from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select, update
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from decimal import Decimal
from typing import Optional
from datetime import datetime, timedelta, timezone
import hashlib
import json

from app.db.session import get_db
from app.api.deps import get_current_active_user, get_current_admin_user
from app.models.user import User
from app.models.order import Order, OrderStatus
from app.models.order_idempotency import OrderIdempotency, OrderIdempotencyState
from app.models.natal_data import NatalData
from app.models.order_natal_item import OrderNatalItem
from app.models.promocode import Promocode, PromocodeRedemption
from app.models.report import ReportStatus
from app.services.payment import YookassaPaymentService
from app.services.refund import RefundService
from app.services.tariff import TariffService
from app.services.analytics import get_user_attribution, record_analytics_event
from app.schemas.order import OrderCreate, OrderListItem, OrderOut, TariffSummary
from app.schemas.refund import AdminRefundResponse
from app.core.rate_limit import limiter
from app.core.config import settings
from app.utils.email_policy import resolve_receipt_and_report_email
from app.services.free_order_policy import user_already_used_free_tariff
import structlog
import asyncio

logger = structlog.get_logger(__name__)
IDEMPOTENCY_PROCESSING_TTL_SECONDS = 120


def _queue_free_report(order_id: int) -> None:
    """Отдельная точка для постановки генерации бесплатного отчёта (удобно мокать в тестах)."""
    from app.tasks.report_generation import generate_report_task

    generate_report_task.delay(order_id)


def _order_to_list_item(order: Order) -> OrderListItem:
    report_ready = bool(
        order.status == OrderStatus.COMPLETED
        and order.report
        and order.report.status == ReportStatus.ACTIVE
    )
    return OrderListItem(
        id=order.id,
        status=order.status.value,
        amount=order.amount,
        natal_data_id=order.natal_data_id,
        created_at=order.created_at,
        updated_at=order.updated_at,
        tariff=TariffSummary(
            code=order.tariff.code,
            name=order.tariff.name,
            billing_type=order.tariff.billing_type,
            subscription_interval=order.tariff.subscription_interval,
        ),
        report_ready=report_ready,
    )


def _build_order_request_fingerprint(
    user_id: int,
    tariff_code: str,
    primary_natal_data_id: int,
    natal_data_ids: list[int],
    report_delivery_email: str | None,
) -> str:
    payload = {
        "user_id": user_id,
        "tariff_code": tariff_code,
        "primary_natal_data_id": primary_natal_data_id,
        "natal_data_ids": natal_data_ids,
        "report_delivery_email": (report_delivery_email or "").lower(),
    }
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def _mark_idempotency_completed(
    db: AsyncSession,
    *,
    user_id: int,
    idempotency_key: str,
    order_id: int,
    yookassa_id: str | None,
    confirmation_url: str | None,
) -> None:
    await db.execute(
        update(OrderIdempotency)
        .where(
            OrderIdempotency.__table__.c.user_id == user_id,
            OrderIdempotency.__table__.c.idempotency_key == idempotency_key,
        )
        .values(
            state=OrderIdempotencyState.COMPLETED,
            order_id=order_id,
            yookassa_id=yookassa_id,
            confirmation_url=confirmation_url,
            processing_started_at=None,
            http_status=200,
            error_detail=None,
        )
    )
    await db.commit()


async def _mark_idempotency_failed(
    db: AsyncSession,
    *,
    user_id: int,
    idempotency_key: str,
    order_id: int | None,
    http_status: int,
    error_detail: str,
) -> None:
    await db.execute(
        update(OrderIdempotency)
        .where(
            OrderIdempotency.__table__.c.user_id == user_id,
            OrderIdempotency.__table__.c.idempotency_key == idempotency_key,
        )
        .values(
            state=OrderIdempotencyState.FAILED,
            order_id=order_id,
            yookassa_id=None,
            confirmation_url=None,
            processing_started_at=None,
            http_status=http_status,
            error_detail=error_detail,
        )
    )
    await db.commit()


router = APIRouter()


@router.get(
    "/",
    response_model=list[OrderListItem],
    summary="Список заказов текущего пользователя",
    description="Заказы по убыванию даты создания; признак готовности отчёта — `report_ready`.",
)
async def list_orders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    stmt = (
        select(Order)
        .where(Order.user_id == current_user.id)
        .options(joinedload(Order.tariff), joinedload(Order.report))
        .order_by(Order.created_at.desc())
    )
    result = await db.execute(stmt)
    orders = result.unique().scalars().all()
    return [_order_to_list_item(o) for o in orders]


@router.get(
    "/{order_id}",
    response_model=OrderListItem,
    summary="Заказ по id",
    description="Только заказы текущего пользователя.",
)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    stmt = (
        select(Order)
        .where(Order.id == order_id, Order.user_id == current_user.id)
        .options(joinedload(Order.tariff), joinedload(Order.report))
    )
    result = await db.execute(stmt)
    order = result.unique().scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return _order_to_list_item(order)


@router.post(
    "/",
    response_model=OrderOut,
    summary="Создать заказ",
    description=(
        "Привязка тарифа к сохранённым натальным данным. Бесплатный тариф сразу переводит "
        "заказ в оплаченный и ставит генерацию отчёта в очередь. Платный — создаёт платёж ЮKassa "
        "и возвращает `confirmation_url`. Требуется согласие с политикой и email для чека/отчёта "
        "(см. `report_delivery_email` при аккаунте без реальной почты)."
    ),
)
@limiter.limit(f"{settings.RATE_LIMIT_ORDERS_PER_MINUTE}/minute")
async def create_order(
    request: Request,
    order_in: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not current_user.consent_given_at:
        raise HTTPException(status_code=400, detail="User consent required")

    # Фиксируем ID пользователя до любых commit, чтобы исключить возможные lazy-load/expired
    # сценарии на ORM-объекте `current_user` в конкурентных запросах.
    user_id = current_user.id

    idempotency_key_raw = request.headers.get("Idempotency-Key")
    idempotency_key = idempotency_key_raw.strip() if idempotency_key_raw else None
    idempotency_key = idempotency_key if idempotency_key else None
    if idempotency_key:
        if len(idempotency_key) > 255:
            raise HTTPException(status_code=422, detail="Idempotency-Key is too long (max 255 chars)")
        if not idempotency_key.isprintable():
            raise HTTPException(status_code=422, detail="Idempotency-Key contains non-printable characters")

    tariff = await TariffService.get_by_code(db, order_in.tariff_code)
    if not tariff:
        raise HTTPException(status_code=404, detail="Tariff not found")

    # Для bundle: primary = first из natal_data_ids (если передан), иначе natal_data_id
    is_bundle = tariff.code == "bundle"
    if is_bundle and order_in.natal_data_ids:
        raw_ids = order_in.natal_data_ids[:3]  # не более 3
        primary_id = raw_ids[0]
    else:
        primary_id = order_in.natal_data_id
        raw_ids = [primary_id]

    natal_stmt = select(NatalData).where(
        NatalData.id == primary_id,
        NatalData.user_id == user_id,
    )
    natal_result = await db.execute(natal_stmt)
    natal_data = natal_result.scalar_one_or_none()
    if not natal_data:
        raise HTTPException(status_code=404, detail="Natal data not found")

    # Валидация дополнительных профилей для bundle
    extra_ids = raw_ids[1:] if is_bundle else []
    extra_natal_data: list[NatalData] = []
    if extra_ids:
        stmt_e = select(NatalData).where(
            NatalData.id.in_(extra_ids),
            NatalData.user_id == user_id,
        )
        res_e = await db.execute(stmt_e)
        by_id = {nd.id: nd for nd in res_e.scalars().all()}
        for eid in extra_ids:
            nd = by_id.get(eid)
            if not nd:
                raise HTTPException(status_code=404, detail=f"Natal data {eid} not found")
            extra_natal_data.append(nd)
    extra_natal_data_ids = [nd.id for nd in extra_natal_data]
    natal_data_id = natal_data.id
    tariff_id = tariff.id
    tariff_name = tariff.name
    tariff_code = tariff.code
    tariff_billing_type = getattr(tariff, "billing_type", None)

    price = tariff.price if isinstance(tariff.price, Decimal) else Decimal(str(tariff.price))
    applied_promo: Promocode | None = None
    promo_discount_percent = 0
    if order_in.promo_code:
        promo_stmt = select(Promocode).where(Promocode.code == order_in.promo_code.strip().upper())
        promo_result = await db.execute(promo_stmt)
        applied_promo = promo_result.scalar_one_or_none()
        if not applied_promo or not applied_promo.is_active:
            raise HTTPException(status_code=404, detail="Promo code not found or inactive")
        if applied_promo.active_until and applied_promo.active_until < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Promo code expired")
        if applied_promo.used_count >= applied_promo.max_uses:
            raise HTTPException(status_code=400, detail="Promo code usage limit reached")
        promo_discount_percent = applied_promo.discount_percent
        price = (price * Decimal(100 - promo_discount_percent) / Decimal(100)).quantize(Decimal("0.01"))
    delivery_email = (
        str(order_in.report_delivery_email).strip()
        if order_in.report_delivery_email
        else None
    )

    receipt_email = resolve_receipt_and_report_email(current_user.email, delivery_email)
    if not receipt_email:
        raise HTTPException(
            status_code=400,
            detail="Укажите report_delivery_email: для аккаунта без реальной почты нужен email для отчёта и чека.",
        )

    if price <= 0 and tariff.code == "free":
        if await user_already_used_free_tariff(db, user_id):
            raise HTTPException(
                status_code=400,
                detail="Бесплатный отчёт уже был заказан. Выберите платный тариф.",
            )

    request_fingerprint = _build_order_request_fingerprint(
        user_id=user_id,
        tariff_code=tariff.code,
        primary_natal_data_id=primary_id,
        natal_data_ids=raw_ids,
        report_delivery_email=delivery_email,
    )

    # Idempotency для create_order:
    # - same key + same payload => idempotent replay
    # - same key + different payload => 409 conflict
    # - stale processing lock => reclaim
    idempotency_row: OrderIdempotency | None = None
    if idempotency_key:
        now_utc = datetime.now(timezone.utc)
        inserted = False
        stmt_insert = insert(OrderIdempotency).values(
            user_id=user_id,
            idempotency_key=idempotency_key,
            state=OrderIdempotencyState.PROCESSING,
            request_fingerprint=request_fingerprint,
            processing_started_at=now_utc,
        )
        try:
            await db.execute(stmt_insert)
            await db.commit()
            inserted = True
        except IntegrityError:
            await db.rollback()

        idem_stmt = select(OrderIdempotency).where(
            OrderIdempotency.__table__.c.user_id == user_id,
            OrderIdempotency.__table__.c.idempotency_key == idempotency_key,
        )
        idempotency_row = None
        for _ in range(50):
            idem_res = await db.execute(idem_stmt)
            idempotency_row = idem_res.scalar_one_or_none()
            if idempotency_row:
                break
            await asyncio.sleep(0.02)

        if not idempotency_row:
            raise HTTPException(
                status_code=409,
                detail="Order creation is in progress for this idempotency key",
            )

        existing_fingerprint = idempotency_row.request_fingerprint
        # Legacy rows may have empty fingerprint; keep compatibility and skip strict payload mismatch in that case.
        if existing_fingerprint in (None, ""):
            logger.warning(
                "Idempotency strict payload check skipped for legacy fingerprint",
                user_id=user_id,
                idempotency_key=idempotency_key,
                state=idempotency_row.state.value,
            )
        elif existing_fingerprint != request_fingerprint:
            raise HTTPException(
                status_code=409,
                detail="Idempotency-Key already used with different request payload",
            )

        if idempotency_row.state == OrderIdempotencyState.COMPLETED:
            if not idempotency_row.order_id:
                raise HTTPException(status_code=500, detail="Idempotency completed without order_id")
            existing_stmt = select(Order).where(
                Order.id == idempotency_row.order_id,
                Order.user_id == user_id,
            )
            existing_res = await db.execute(existing_stmt)
            existing_order = existing_res.scalar_one_or_none()
            if not existing_order:
                raise HTTPException(status_code=404, detail="Order not found for idempotency key")
            return OrderOut(
                id=existing_order.id,
                user_id=existing_order.user_id,
                natal_data_id=existing_order.natal_data_id,
                tariff_id=existing_order.tariff_id,
                status=existing_order.status.value,
                amount=existing_order.amount,
                yookassa_id=idempotency_row.yookassa_id or existing_order.yookassa_id,
                confirmation_url=idempotency_row.confirmation_url,
                created_at=existing_order.created_at,
            )

        if idempotency_row.state == OrderIdempotencyState.FAILED:
            raise HTTPException(
                status_code=idempotency_row.http_status or 502,
                detail=idempotency_row.error_detail or "Previous attempt failed",
            )

        processing_started_at = idempotency_row.processing_started_at
        lock_expired = False
        if processing_started_at:
            if processing_started_at.tzinfo is None:
                processing_started_at = processing_started_at.replace(tzinfo=timezone.utc)
            lock_expired = processing_started_at + timedelta(seconds=IDEMPOTENCY_PROCESSING_TTL_SECONDS) < now_utc
        # processing уже существует. Делаем атомарный claim: только один запрос продолжит создание.
        # если lock протух — разрешаем reclaim.
        if idempotency_row.state == OrderIdempotencyState.PROCESSING:
            if not inserted and not lock_expired:
                raise HTTPException(
                    status_code=409,
                    detail="Order creation in progress for this idempotency key",
                )
            if lock_expired:
                claim_stmt = (
                    update(OrderIdempotency)
                    .where(
                        OrderIdempotency.__table__.c.user_id == user_id,
                        OrderIdempotency.__table__.c.idempotency_key == idempotency_key,
                        OrderIdempotency.__table__.c.state == OrderIdempotencyState.PROCESSING,
                        OrderIdempotency.__table__.c.order_id.is_(None),
                        OrderIdempotency.__table__.c.processing_started_at == processing_started_at,
                    )
                    .values(processing_started_at=now_utc)
                )
                claim_res = await db.execute(claim_stmt)
                await db.commit()
                if claim_res.rowcount != 1:
                    raise HTTPException(
                        status_code=409,
                        detail="Order creation in progress for this idempotency key",
                    )
                logger.info(
                    "Idempotency stale processing lock reclaimed",
                    user_id=user_id,
                    idempotency_key=idempotency_key,
                    previous_processing_started_at=processing_started_at.isoformat(),
                    new_processing_started_at=now_utc.isoformat(),
                )

    if price <= 0:
        order = Order(
            user_id=user_id,
            natal_data_id=natal_data_id,
            tariff_id=tariff_id,
            amount=price,
            status=OrderStatus.PAID,
            report_delivery_email=delivery_email,
            promo_code=applied_promo.code if applied_promo else None,
        )
        db.add(order)
        await db.flush()  # получаем order.id до commit
        for idx, nd_id in enumerate(extra_natal_data_ids, start=2):
            db.add(OrderNatalItem(order_id=order.id, natal_data_id=nd_id, slot_index=idx))
        await db.commit()
        await db.refresh(order)
        if applied_promo:
            applied_promo.used_count += 1
            db.add(
                PromocodeRedemption(
                    promocode_id=applied_promo.id,
                    user_id=user_id,
                    order_id=order.id,
                    discount_percent=promo_discount_percent,
                    discount_amount=(tariff.price - order.amount),
                )
            )
            await db.commit()

        if idempotency_key:
            await _mark_idempotency_completed(
                db,
                user_id=user_id,
                idempotency_key=idempotency_key,
                order_id=order.id,
                yookassa_id=None,
                confirmation_url=None,
            )

        _queue_free_report(order.id)
        utm_source, utm_medium, utm_campaign, source_channel, platform, geo = await get_user_attribution(db, user_id)
        await record_analytics_event(
            db,
            event_name="order_completed",
            user_id=user_id,
            order_id=order.id,
            tariff_code=tariff_code,
            source_channel=source_channel,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            platform=platform,
            geo=geo,
            amount=order.amount,
            dedupe_key=f"order_completed:{order.id}",
        )
        logger.info(
            "Order created free tariff, report queued",
            order_id=order.id,
            user_id=user_id,
        )
        return OrderOut(
            id=order.id,
            user_id=order.user_id,
            natal_data_id=order.natal_data_id,
            tariff_id=order.tariff_id,
            status=order.status.value,
            amount=order.amount,
            yookassa_id=None,
            confirmation_url=None,
            created_at=order.created_at,
        )

    order = Order(
        user_id=user_id,
        natal_data_id=natal_data_id,
        tariff_id=tariff_id,
        amount=price,
        status=OrderStatus.PENDING,
        report_delivery_email=delivery_email,
        promo_code=applied_promo.code if applied_promo else None,
    )
    db.add(order)
    await db.flush()
    for idx, nd_id in enumerate(extra_natal_data_ids, start=2):
        db.add(OrderNatalItem(order_id=order.id, natal_data_id=nd_id, slot_index=idx))
    await db.commit()
    await db.refresh(order)
    if applied_promo:
        applied_promo.used_count += 1
        db.add(
            PromocodeRedemption(
                promocode_id=applied_promo.id,
                user_id=user_id,
                order_id=order.id,
                discount_percent=promo_discount_percent,
                discount_amount=(tariff.price - order.amount),
            )
        )
        await db.commit()
        await db.refresh(order)

    payment_service = YookassaPaymentService()
    description = f"AstroGen Natal Chart - {tariff_name}"
    save_pm = tariff_billing_type == "subscription"
    try:
        payment_kwargs = {
            "order_id": order.id,
            "amount": order.amount,
            "description": description,
            "user_email": receipt_email,
            "metadata": {"order_id": order.id, "tariff": tariff_code},
            "save_payment_method": save_pm,
        }
        # Если клиент повторяет запрос с тем же заголовком — YooKassa тоже должен дедуплицировать платеж.
        if idempotency_key:
            payment_kwargs["idempotency_key"] = idempotency_key

        payment = await payment_service.create_payment(**payment_kwargs)
    except Exception as exc:
        logger.exception(
            "YooKassa create_payment failed",
            order_id=order.id,
            user_id=user_id,
            error=str(exc),
        )
        order.status = OrderStatus.FAILED_TO_INIT_PAYMENT
        await db.commit()
        await db.refresh(order)

        if idempotency_key:
            await _mark_idempotency_failed(
                db,
                user_id=user_id,
                idempotency_key=idempotency_key,
                order_id=order.id,
                http_status=502,
                error_detail="Payment provider unavailable. Order marked as failed.",
            )

        raise HTTPException(
            status_code=502,
            detail="Payment provider unavailable. Order marked as failed; create a new order or contact support.",
        )

    order.yookassa_id = payment["id"]
    await db.commit()
    await db.refresh(order)

    if idempotency_key:
        await _mark_idempotency_completed(
            db,
            user_id=user_id,
            idempotency_key=idempotency_key,
            order_id=order.id,
            yookassa_id=order.yookassa_id,
            confirmation_url=payment.get("confirmation_url"),
        )

    logger.info(
        "Payment initialized for order",
        order_id=order.id,
        user_id=user_id,
        yookassa_id=order.yookassa_id,
    )
    utm_source, utm_medium, utm_campaign, source_channel, platform, geo = await get_user_attribution(db, user_id)
    await record_analytics_event(
        db,
        event_name="payment_started",
        user_id=user_id,
        order_id=order.id,
        tariff_code=tariff_code,
        source_channel=source_channel,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
        platform=platform,
        geo=geo,
        amount=order.amount,
        dedupe_key=f"payment_started:{order.id}",
    )

    return OrderOut(
        id=order.id,
        user_id=order.user_id,
        natal_data_id=order.natal_data_id,
        tariff_id=order.tariff_id,
        status=order.status.value,
        amount=order.amount,
        yookassa_id=order.yookassa_id,
        confirmation_url=payment["confirmation_url"],
        created_at=order.created_at,
    )


@router.post(
    "/{order_id}/retry-payment",
    response_model=OrderOut,
    summary="Повторная инициализация оплаты заказа",
    description=(
        "Возвращает актуальный `confirmation_url` для заказа текущего пользователя. "
        "Доступно только для `pending` и `failed_to_init_payment`."
    ),
)
async def retry_order_payment(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    stmt = (
        select(Order)
        .where(Order.id == order_id, Order.user_id == current_user.id)
        .options(joinedload(Order.tariff))
    )
    result = await db.execute(stmt)
    order = result.unique().scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status not in {OrderStatus.PENDING, OrderStatus.FAILED_TO_INIT_PAYMENT}:
        raise HTTPException(
            status_code=400,
            detail="Retry payment is available only for pending or failed_to_init_payment orders",
        )
    if order.amount <= 0:
        raise HTTPException(status_code=400, detail="Free order does not require payment")
    if not order.tariff:
        raise HTTPException(status_code=404, detail="Tariff not found")
    payment_service = YookassaPaymentService()
    if order.yookassa_id:
        existing_payment = await payment_service.get_payment(order.yookassa_id)
        existing_url = existing_payment.get("confirmation_url") if existing_payment else None
        if existing_url and existing_payment.get("status") in {"pending", "waiting_for_capture"}:
            return OrderOut(
                id=order.id,
                user_id=order.user_id,
                natal_data_id=order.natal_data_id,
                tariff_id=order.tariff_id,
                status=order.status.value,
                amount=order.amount,
                yookassa_id=order.yookassa_id,
                confirmation_url=existing_url,
                created_at=order.created_at,
            )

    receipt_email = resolve_receipt_and_report_email(current_user.email, order.report_delivery_email)
    if not receipt_email:
        raise HTTPException(
            status_code=400,
            detail="Укажите report_delivery_email: для аккаунта без реальной почты нужен email для отчёта и чека.",
        )

    description = f"AstroGen Natal Chart - {order.tariff.name}"
    save_pm = getattr(order.tariff, "billing_type", None) == "subscription"
    try:
        payment = await payment_service.create_payment(
            order_id=order.id,
            amount=order.amount,
            description=description,
            user_email=receipt_email,
            metadata={"order_id": order.id, "tariff": order.tariff.code},
            save_payment_method=save_pm,
            # Детерминированный ключ: меняется раз в час → идемпотентен при двойном клике,
            # но позволяет создать новый платёж если предыдущий истёк.
            idempotency_key=f"retry-{order.id}-{datetime.utcnow().strftime('%Y%m%d%H')}",
        )
    except Exception as exc:
        logger.exception(
            "YooKassa retry payment failed",
            order_id=order.id,
            user_id=current_user.id,
            error=str(exc),
        )
        order.status = OrderStatus.FAILED_TO_INIT_PAYMENT
        await db.commit()
        await db.refresh(order)
        raise HTTPException(
            status_code=502,
            detail="Payment provider unavailable. Retry later or contact support.",
        )

    order.yookassa_id = payment["id"]
    order.status = OrderStatus.PENDING
    await db.commit()
    await db.refresh(order)

    return OrderOut(
        id=order.id,
        user_id=order.user_id,
        natal_data_id=order.natal_data_id,
        tariff_id=order.tariff_id,
        status=order.status.value,
        amount=order.amount,
        yookassa_id=order.yookassa_id,
        confirmation_url=payment["confirmation_url"],
        created_at=order.created_at,
    )


@router.post(
    "/{order_id}/refund",
    response_model=AdminRefundResponse,
    summary="Возврат по заказу (админ)",
    description="Инициирует возврат в ЮKassa для заказов в статусе оплачен/завершён. Только администратор API.",
)
async def refund_order(
    order_id: int,
    amount: Optional[Decimal] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    service = RefundService()
    try:
        result = await service.create_refund(db, order_id, amount)
    except ValueError as e:
        msg = str(e)
        code = status.HTTP_404_NOT_FOUND if "not found" in msg.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=msg) from e
    return AdminRefundResponse(**result)
