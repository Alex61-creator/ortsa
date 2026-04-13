from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user
from app.db.session import get_db
from app.models.user import User
from app.services.order_ops_metrics import compute_order_ops_metrics_dict

router = APIRouter()


class OrderMetricsBlock(BaseModel):
    failed_orders_total: int
    processing_stuck_over_2h: int
    checked_at: datetime


class AdminDashboardSummary(BaseModel):
    order_metrics: OrderMetricsBlock
    analytics_stub: bool = True
    future_docs: str = Field(
        default="docs/ADMIN_PANEL_FUTURE.md",
        description="Промокоды, воронка UTM, feature flags — в документе для последующей реализации",
    )


@router.get("/summary", response_model=AdminDashboardSummary, summary="Сводка дашборда админки")
async def admin_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    raw = await compute_order_ops_metrics_dict(db)
    return AdminDashboardSummary(
        order_metrics=OrderMetricsBlock(**raw),
        analytics_stub=True,
    )
