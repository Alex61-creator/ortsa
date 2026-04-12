"""
Служебные метрики для мониторинга (алерты по заказам). Доступ только администраторам API.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user
from app.db.session import get_db
from app.models.order import Order, OrderStatus
from app.models.user import User

router = APIRouter()


class OrderOpsMetrics(BaseModel):
    failed_orders_total: int
    processing_stuck_over_2h: int
    checked_at: datetime


@router.get("/metrics/orders", response_model=OrderOpsMetrics)
async def order_ops_metrics(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """Счётчики для дашбордов/алертов: FAILED и «зависшие» PROCESSING."""
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(hours=2)

    failed_q = await db.execute(
        select(func.count()).select_from(Order).where(Order.status == OrderStatus.FAILED)
    )
    failed_orders_total = int(failed_q.scalar_one() or 0)

    stuck_q = await db.execute(
        select(func.count())
        .select_from(Order)
        .where(
            Order.status == OrderStatus.PROCESSING,
            Order.updated_at < threshold,
        )
    )
    processing_stuck_over_2h = int(stuck_q.scalar_one() or 0)

    return OrderOpsMetrics(
        failed_orders_total=failed_orders_total,
        processing_stuck_over_2h=processing_stuck_over_2h,
        checked_at=now,
    )
