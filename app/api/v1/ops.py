"""
Служебные метрики для мониторинга (алерты по заказам). Доступ только администраторам API.
"""
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user
from app.db.session import get_db
from app.models.user import User
from app.services.order_ops_metrics import compute_order_ops_metrics_dict

router = APIRouter()


class OrderOpsMetrics(BaseModel):
    failed_orders_total: int
    processing_stuck_over_2h: int
    paid_completed_latency_p50_seconds: float | None = None
    paid_completed_latency_p95_seconds: float | None = None
    checked_at: datetime


@router.get(
    "/metrics/orders",
    response_model=OrderOpsMetrics,
    summary="Метрики заказов для мониторинга",
    description="Счётчики FAILED и «зависших» PROCESSING (>2 ч). Только администратор API.",
)
async def order_ops_metrics(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """Счётчики для дашбордов/алертов: FAILED и «зависшие» PROCESSING."""
    data = await compute_order_ops_metrics_dict(db)
    return OrderOpsMetrics(**data)
