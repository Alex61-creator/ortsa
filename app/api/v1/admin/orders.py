import csv
import io
import json
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.deps import get_current_admin_user, get_current_admin_user_can_refund, get_current_admin_user_can_retry_report
from app.db.session import get_db
from app.models.admin_action_log import AdminActionLog
from app.models.analytics_event import AnalyticsEvent
from app.models.order import Order, OrderStatus
from app.models.report import Report, ReportStatus
from app.models.user import User
from app.schemas.admin_order import AdminOrderListItem
from app.schemas.admin_extra import AdminOrderTimelineItem
from app.schemas.order import TariffSummary
from app.schemas.refund import AdminRefundResponse
from app.services.admin_order_prepare import prepare_order_for_admin_report_retry
from app.services.admin_report_retry import consume_admin_report_retry_slot
from app.services.admin_logs import append_admin_log
from app.services.refund import RefundService
from app.services.report_option_pricing import estimate_report_options_line_amount, load_report_option_price_map_and_multi
from app.tasks.report_generation import generate_report_task

router = APIRouter()


def _to_admin_item(
    order: Order,
    *,
    price_by_key: dict[str, Decimal] | None = None,
    multi_discount_percent: Decimal | None = None,
) -> AdminOrderListItem:
    report_ready = bool(
        order.status == OrderStatus.COMPLETED
        and order.report
        and order.report.status == ReportStatus.ACTIVE
    )
    line_amt = None
    if price_by_key is not None and multi_discount_percent is not None:
        line_amt = estimate_report_options_line_amount(
            order.report_option_flags,
            price_by_key=price_by_key,
            multi_discount_percent=multi_discount_percent,
        )
    return AdminOrderListItem(
        id=order.id,
        user_id=order.user_id,
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
        promo_code=order.promo_code,
        report_option_flags=order.report_option_flags,
        report_options_line_amount=line_amt,
    )


@router.get("/", response_model=list[AdminOrderListItem], summary="Заказы (админ)")
async def list_orders_admin(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    user_id: Optional[int] = Query(None),
    q: Optional[str] = Query(None, description="Поиск по id заказа"),
):
    conds = []
    if status_filter:
        try:
            st = OrderStatus(status_filter)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
        conds.append(Order.status == st)
    if user_id is not None:
        conds.append(Order.user_id == user_id)
    if q and q.strip().isdigit():
        conds.append(Order.id == int(q.strip()))

    stmt = (
        select(Order)
        .options(joinedload(Order.tariff), joinedload(Order.report))
        .order_by(Order.created_at.desc())
    )
    if conds:
        stmt = stmt.where(and_(*conds))

    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    result = await db.execute(stmt)
    orders = result.unique().scalars().all()
    price_by_key, multi_discount_percent = await load_report_option_price_map_and_multi(db)
    return [_to_admin_item(o, price_by_key=price_by_key, multi_discount_percent=multi_discount_percent) for o in orders]


@router.get("/{order_id}", response_model=AdminOrderListItem, summary="Заказ по id (админ)")
async def get_order_admin(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    stmt = (
        select(Order)
        .where(Order.id == order_id)
        .options(joinedload(Order.tariff), joinedload(Order.report))
    )
    result = await db.execute(stmt)
    order = result.unique().scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    price_by_key, multi_discount_percent = await load_report_option_price_map_and_multi(db)
    return _to_admin_item(order, price_by_key=price_by_key, multi_discount_percent=multi_discount_percent)


@router.post(
    "/{order_id}/refund",
    response_model=AdminRefundResponse,
    summary="Возврат по заказу (админ)",
)
async def refund_order_admin(
    order_id: int,
    amount: Optional[Decimal] = None,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_admin_user_can_refund),
):
    service = RefundService()
    try:
        result = await service.create_refund(db, order_id, amount)
    except ValueError as e:
        msg = str(e)
        code = status.HTTP_404_NOT_FOUND if "not found" in msg.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=msg) from e
    await append_admin_log(
        db,
        actor.email or f"user:{actor.id}",
        "refund_order_admin",
        f"order:{order_id}",
        details={
            "refund_id": result["refund_id"],
            "status": result["status"],
            "amount": str(result["amount"]),
        },
    )
    return AdminRefundResponse(**result)


@router.post(
    "/{order_id}/retry-report",
    summary="Перезапустить генерацию отчёта (админ, лимит 5/сутки на заказ)",
)
async def retry_report_admin(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_admin_user_can_retry_report),
):
    stmt = select(Order).where(Order.id == order_id).options(joinedload(Order.tariff), joinedload(Order.report))
    result = await db.execute(stmt)
    order = result.unique().scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    await consume_admin_report_retry_slot(order_id)
    await prepare_order_for_admin_report_retry(db, order)
    await db.refresh(order)
    generate_report_task.delay(order_id)
    await append_admin_log(
        db,
        actor.email or f"user:{actor.id}",
        "retry_report_admin",
        f"order:{order_id}",
        details={"queued": True},
    )
    return {"order_id": order_id, "status": order.status.value, "queued": True}


@router.get(
    "/{order_id}/timeline",
    response_model=list[AdminOrderTimelineItem],
    summary="Таймлайн заказа (админ)",
)
async def order_timeline_admin(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    order_exists = await db.scalar(select(Order.id).where(Order.id == order_id))
    if not order_exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    analytics_event_names = [
        "payment_started",
        "payment_succeeded",
        "first_purchase_completed",
        "order_completed",
        "addon_attached",
        "refund_completed",
        "email_sent",
        "cohort_month_started",
        "subscription_renewal_payment",
    ]

    analytics_stmt = (
        select(AnalyticsEvent)
        .where(AnalyticsEvent.order_id == order_id)
        .where(
            or_(
                AnalyticsEvent.event_name.in_(analytics_event_names),
                AnalyticsEvent.event_name.like("report_generation_%"),
            )
        )
    )
    analytics_events = (await db.execute(analytics_stmt)).scalars().all()

    logs_stmt = (
        select(AdminActionLog)
        .where(AdminActionLog.entity.ilike(f"%order:{order_id}%"))
        .order_by(AdminActionLog.created_at.asc())
    )
    admin_logs = (await db.execute(logs_stmt)).scalars().all()

    items: list[AdminOrderTimelineItem] = []

    for ev in analytics_events:
        amount = float(ev.amount) if ev.amount is not None else None
        items.append(
            AdminOrderTimelineItem(
                type="analytics",
                time=ev.event_time,
                event_name=ev.event_name,
                details={
                    "amount": amount,
                    "currency": ev.currency,
                    "tariff_code": ev.tariff_code,
                    "source_channel": ev.source_channel,
                    "utm_source": ev.utm_source,
                    "utm_medium": ev.utm_medium,
                    "utm_campaign": ev.utm_campaign,
                    "correlation_id": ev.correlation_id,
                    "cost_components": ev.cost_components,
                    "event_metadata": ev.event_metadata,
                    "notes": ev.notes,
                    "dedupe_key": ev.dedupe_key,
                },
            )
        )

    for lg in admin_logs:
        items.append(
            AdminOrderTimelineItem(
                type="admin_log",
                time=lg.created_at,
                action=lg.action,
                entity=lg.entity,
                details=lg.details,
            )
        )

    items.sort(key=lambda x: x.time)
    return items


@router.get(
    "/{order_id}/timeline.csv",
    summary="Таймлайн заказа — CSV-выгрузка",
    response_class=StreamingResponse,
)
async def order_timeline_csv(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
    excel_bom: int = Query(default=0, ge=0, le=1),
):
    order_exists = await db.scalar(select(Order.id).where(Order.id == order_id))
    if not order_exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    analytics_event_names = [
        "payment_started",
        "payment_succeeded",
        "first_purchase_completed",
        "order_completed",
        "addon_attached",
        "refund_completed",
        "email_sent",
        "cohort_month_started",
        "subscription_renewal_payment",
    ]
    analytics_stmt = (
        select(AnalyticsEvent)
        .where(AnalyticsEvent.order_id == order_id)
        .where(
            or_(
                AnalyticsEvent.event_name.in_(analytics_event_names),
                AnalyticsEvent.event_name.like("report_generation_%"),
            )
        )
    )
    analytics_events = (await db.execute(analytics_stmt)).scalars().all()

    logs_stmt = (
        select(AdminActionLog)
        .where(AdminActionLog.entity.ilike(f"%order:{order_id}%"))
        .order_by(AdminActionLog.created_at.asc())
    )
    admin_logs = (await db.execute(logs_stmt)).scalars().all()

    header = ["time_utc", "type", "name", "entity", "details", "dedupe_key"]
    rows: list[list[str]] = [header]

    for ev in analytics_events:
        details_dict = {
            "amount": float(ev.amount) if ev.amount is not None else None,
            "currency": ev.currency,
            "tariff_code": ev.tariff_code,
            "source_channel": ev.source_channel,
            "utm_source": ev.utm_source,
            "utm_campaign": ev.utm_campaign,
            "cost_components": ev.cost_components,
            "event_metadata": ev.event_metadata,
        }
        rows.append([
            ev.event_time.isoformat() if ev.event_time else "",
            "analytics",
            ev.event_name or "",
            "",
            json.dumps(details_dict, ensure_ascii=False, default=str),
            ev.dedupe_key or "",
        ])

    for lg in admin_logs:
        rows.append([
            lg.created_at.isoformat() if lg.created_at else "",
            "admin_log",
            lg.action or "",
            lg.entity or "",
            json.dumps(lg.details, ensure_ascii=False, default=str) if lg.details else "",
            "",
        ])

    rows.sort(key=lambda r: r[0])

    buf = io.StringIO()
    writer = csv.writer(buf)
    for row in rows:
        writer.writerow(row)
    data = buf.getvalue()
    if excel_bom:
        data = "\ufeff" + data

    async def _stream():
        yield data.encode("utf-8")

    return StreamingResponse(
        _stream(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="order_{order_id}_timeline.csv"'},
    )
