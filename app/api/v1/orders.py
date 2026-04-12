from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from decimal import Decimal
from typing import Optional

from app.db.session import get_db
from app.api.deps import get_current_active_user, get_current_admin_user
from app.models.user import User
from app.models.order import Order, OrderStatus
from app.models.natal_data import NatalData
from app.models.report import ReportStatus
from app.services.payment import YookassaPaymentService
from app.services.refund import RefundService
from app.services.tariff import TariffService
from app.schemas.order import OrderCreate, OrderListItem, OrderOut, TariffSummary
from app.core.rate_limit import limiter
from app.core.config import settings
from app.utils.email_policy import resolve_receipt_and_report_email
from app.services.free_order_policy import user_already_used_free_tariff
import structlog

logger = structlog.get_logger(__name__)


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
        tariff=TariffSummary(code=order.tariff.code, name=order.tariff.name),
        report_ready=report_ready,
    )


router = APIRouter()


@router.get("/", response_model=list[OrderListItem])
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


@router.get("/{order_id}", response_model=OrderListItem)
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


@router.post("/", response_model=OrderOut)
@limiter.limit(f"{settings.RATE_LIMIT_ORDERS_PER_MINUTE}/minute")
async def create_order(
    request: Request,
    order_in: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not current_user.consent_given_at:
        raise HTTPException(status_code=400, detail="User consent required")

    tariff = await TariffService.get_by_code(db, order_in.tariff_code)
    if not tariff:
        raise HTTPException(status_code=404, detail="Tariff not found")

    natal_stmt = select(NatalData).where(
        NatalData.id == order_in.natal_data_id,
        NatalData.user_id == current_user.id,
    )
    natal_result = await db.execute(natal_stmt)
    natal_data = natal_result.scalar_one_or_none()
    if not natal_data:
        raise HTTPException(status_code=404, detail="Natal data not found")

    price = tariff.price if isinstance(tariff.price, Decimal) else Decimal(str(tariff.price))
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
        if await user_already_used_free_tariff(db, current_user.id):
            raise HTTPException(
                status_code=400,
                detail="Бесплатный отчёт уже был заказан. Выберите платный тариф.",
            )

    if price <= 0:
        order = Order(
            user_id=current_user.id,
            natal_data_id=natal_data.id,
            tariff_id=tariff.id,
            amount=price,
            status=OrderStatus.PAID,
            report_delivery_email=delivery_email,
        )
        db.add(order)
        await db.commit()
        await db.refresh(order)
        _queue_free_report(order.id)
        logger.info(
            "Order created free tariff, report queued",
            order_id=order.id,
            user_id=current_user.id,
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
        user_id=current_user.id,
        natal_data_id=natal_data.id,
        tariff_id=tariff.id,
        amount=price,
        status=OrderStatus.PENDING,
        report_delivery_email=delivery_email,
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    payment_service = YookassaPaymentService()
    description = f"AstroGen Natal Chart - {tariff.name}"
    save_pm = getattr(tariff, "billing_type", None) == "subscription"
    try:
        payment = await payment_service.create_payment(
            order_id=order.id,
            amount=order.amount,
            description=description,
            user_email=receipt_email,
            metadata={"order_id": order.id, "tariff": tariff.code},
            save_payment_method=save_pm,
        )
    except Exception as exc:
        logger.exception(
            "YooKassa create_payment failed",
            order_id=order.id,
            user_id=current_user.id,
            error=str(exc),
        )
        order.status = OrderStatus.FAILED_TO_INIT_PAYMENT
        await db.commit()
        await db.refresh(order)
        raise HTTPException(
            status_code=502,
            detail="Payment provider unavailable. Order marked as failed; create a new order or contact support.",
        )

    order.yookassa_id = payment["id"]
    await db.commit()
    await db.refresh(order)

    logger.info(
        "Payment initialized for order",
        order_id=order.id,
        user_id=current_user.id,
        yookassa_id=order.yookassa_id,
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


@router.post("/{order_id}/refund")
async def refund_order(
    order_id: int,
    amount: Optional[Decimal] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    service = RefundService()
    result = await service.create_refund(db, order_id, amount)
    return result
