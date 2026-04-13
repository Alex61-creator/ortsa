from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.deps import get_current_admin_user
from app.db.session import get_db
from app.models.order import Order, OrderStatus
from app.models.report import Report, ReportStatus
from app.models.user import User
from app.schemas.admin_order import AdminOrderListItem
from app.schemas.order import TariffSummary
from app.schemas.refund import AdminRefundResponse
from app.services.admin_order_prepare import prepare_order_for_admin_report_retry
from app.services.admin_report_retry import consume_admin_report_retry_slot
from app.services.refund import RefundService
from app.tasks.report_generation import generate_report_task

router = APIRouter()


def _to_admin_item(order: Order) -> AdminOrderListItem:
    report_ready = bool(
        order.status == OrderStatus.COMPLETED
        and order.report
        and order.report.status == ReportStatus.ACTIVE
    )
    return AdminOrderListItem(
        id=order.id,
        user_id=order.user_id,
        status=order.status.value,
        amount=order.amount,
        natal_data_id=order.natal_data_id,
        created_at=order.created_at,
        updated_at=order.updated_at,
        tariff=TariffSummary(code=order.tariff.code, name=order.tariff.name),
        report_ready=report_ready,
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
    return [_to_admin_item(o) for o in orders]


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
    return _to_admin_item(order)


@router.post(
    "/{order_id}/refund",
    response_model=AdminRefundResponse,
    summary="Возврат по заказу (админ)",
)
async def refund_order_admin(
    order_id: int,
    amount: Optional[Decimal] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    service = RefundService()
    try:
        result = await service.create_refund(db, order_id, amount)
    except ValueError as e:
        msg = str(e)
        code = status.HTTP_404_NOT_FOUND if "not found" in msg.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=msg) from e
    return AdminRefundResponse(**result)


@router.post(
    "/{order_id}/retry-report",
    summary="Перезапустить генерацию отчёта (админ, лимит 5/сутки на заказ)",
)
async def retry_report_admin(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
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
    return {"order_id": order_id, "status": order.status.value, "queued": True}
