from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user
from app.db.session import get_db
from app.models.order import Order, OrderStatus
from app.models.user import User
from app.services.order_ops_metrics import compute_order_ops_metrics_dict

router = APIRouter()

MONTHS_RU = {
    1: "Янв", 2: "Фев", 3: "Мар", 4: "Апр", 5: "Май", 6: "Июн",
    7: "Июл", 8: "Авг", 9: "Сен", 10: "Окт", 11: "Ноя", 12: "Дек",
}


class OrderMetricsBlock(BaseModel):
    failed_orders_total: int
    processing_stuck_over_2h: int
    checked_at: datetime


class MrrPoint(BaseModel):
    month: str
    mrr: float


class AdminDashboardSummary(BaseModel):
    order_metrics: OrderMetricsBlock
    analytics_stub: bool = False
    future_docs: str = Field(
        default="docs/ADMIN_PANEL_FUTURE.md",
        description="Промокоды, воронка UTM, feature flags — в документе для последующей реализации",
    )
    business_metrics: dict
    llm_metrics: dict
    mrr_history: list[MrrPoint] = Field(default_factory=list)


@router.get("/summary", response_model=AdminDashboardSummary, summary="Сводка дашборда админки")
async def admin_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    raw = await compute_order_ops_metrics_dict(db)
    users_total = int((await db.scalar(select(func.count(User.id)))) or 0)
    paid_sum = (
        await db.scalar(
            select(func.coalesce(func.sum(Order.amount), Decimal("0.00"))).where(
                Order.status == OrderStatus.PAID
            )
        )
    ) or Decimal("0.00")
    refunded_sum = (
        await db.scalar(
            select(func.coalesce(func.sum(Order.refunded_amount), Decimal("0.00")))
        )
    ) or Decimal("0.00")
    completed_cnt = int(
        (
            await db.scalar(
                select(func.count(Order.id)).where(Order.status == OrderStatus.COMPLETED)
            )
        )
        or 0
    )
    paid_cnt = int(
        (
            await db.scalar(
                select(func.count(Order.id)).where(Order.status == OrderStatus.PAID)
            )
        )
        or 0
    )

    mrr = float(paid_sum)
    new_mrr = round(mrr * 0.25, 2)
    churn_mrr = float(refunded_sum)
    ltv = round(mrr / users_total, 2) if users_total else 0.0
    llm_cost = round(mrr * 0.18, 2)
    roi_pct = round(((mrr - llm_cost) / llm_cost) * 100, 2) if llm_cost else 0.0
    avg_report_cost = round(llm_cost / max(completed_cnt, 1), 2)
    tokens_total = max((paid_cnt + completed_cnt) * 8300, 1000)

    # MRR history — last 6 calendar months
    now = datetime.utcnow()
    mrr_history: list[MrrPoint] = []
    for i in range(5, -1, -1):
        year = now.year
        month = now.month - i
        while month <= 0:
            month += 12
            year -= 1
        month_start = datetime(year, month, 1, 0, 0, 0)
        next_month = month + 1
        next_year = year
        if next_month > 12:
            next_month = 1
            next_year += 1
        month_end = datetime(next_year, next_month, 1, 0, 0, 0)

        month_sum = float(
            (
                await db.scalar(
                    select(func.coalesce(func.sum(Order.amount), Decimal("0")))
                    .where(Order.status.in_([OrderStatus.PAID, OrderStatus.COMPLETED]))
                    .where(Order.created_at >= month_start)
                    .where(Order.created_at < month_end)
                )
            )
            or 0
        )
        mrr_history.append(MrrPoint(month=MONTHS_RU[month], mrr=round(month_sum, 2)))

    return AdminDashboardSummary(
        order_metrics=OrderMetricsBlock(**raw),
        analytics_stub=True,
        business_metrics={
            "users_total": users_total,
            "mrr": round(mrr, 2),
            "new_mrr": new_mrr,
            "churn_mrr": round(churn_mrr, 2),
            "ltv": ltv,
        },
        llm_metrics={
            "llm_cost": llm_cost,
            "roi_pct": roi_pct,
            "avg_report_cost": avg_report_cost,
            "tokens_total": tokens_total,
        },
        mrr_history=mrr_history,
    )
