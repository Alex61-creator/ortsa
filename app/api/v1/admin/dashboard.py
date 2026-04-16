from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user
from app.db.session import get_db
from app.models.order import Order, OrderStatus
from app.models.tariff import Tariff
from app.models.user import User
from app.services.order_ops_metrics import compute_order_ops_metrics_dict

router = APIRouter()

MONTHS_RU = {
    1: "Янв", 2: "Фев", 3: "Мар", 4: "Апр", 5: "Май", 6: "Июн",
    7: "Июл", 8: "Авг", 9: "Сен", 10: "Окт", 11: "Ноя", 12: "Дек",
}

REVENUE_ORDER_STATUSES = (OrderStatus.PAID, OrderStatus.COMPLETED)


class OrderMetricsBlock(BaseModel):
    failed_orders_total: int
    processing_stuck_over_2h: int
    checked_at: datetime


class MrrPoint(BaseModel):
    month: str
    mrr: float


class MonthAmount(BaseModel):
    month: str
    amount_rub: float


class TariffKpiRow(BaseModel):
    tariff_code: str
    tariff_name: str
    revenue_rub: float
    ai_cost_rub: float


class AdminDashboardSummary(BaseModel):
    order_metrics: OrderMetricsBlock
    analytics_stub: bool = False
    future_docs: str = Field(
        default="docs/ADMIN_PANEL_FUTURE.md",
        description="Доп. идеи для админки — см. документ",
    )
    business_metrics: dict
    llm_metrics: dict
    mrr_history: list[MrrPoint] = Field(default_factory=list)
    ai_cost_history: list[MonthAmount] = Field(default_factory=list)
    tariff_kpis: list[TariffKpiRow] = Field(default_factory=list)


def _month_bounds(now: datetime, months_ago: int) -> tuple[datetime, datetime]:
    year = now.year
    month = now.month - months_ago
    while month <= 0:
        month += 12
        year -= 1
    month_start = datetime(year, month, 1, tzinfo=timezone.utc)
    next_month = month + 1
    next_year = year
    if next_month > 12:
        next_month = 1
        next_year += 1
    month_end = datetime(next_year, next_month, 1, tzinfo=timezone.utc)
    return month_start, month_end


@router.get("/summary", response_model=AdminDashboardSummary, summary="Сводка дашборда админки")
async def admin_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    raw = await compute_order_ops_metrics_dict(db)
    users_total = int((await db.scalar(select(func.count(User.id)))) or 0)
    now = datetime.now(timezone.utc)
    start_30d = now - timedelta(days=30)
    start_90d = now - timedelta(days=90)

    revenue_lifetime = (
        await db.scalar(
            select(func.coalesce(func.sum(Order.amount), Decimal("0.00"))).where(
                Order.status.in_(REVENUE_ORDER_STATUSES)
            )
        )
    ) or Decimal("0.00")

    revenue_30d = (
        await db.scalar(
            select(func.coalesce(func.sum(Order.amount), Decimal("0.00")))
            .where(Order.status.in_(REVENUE_ORDER_STATUSES))
            .where(Order.created_at >= start_30d)
        )
    ) or Decimal("0.00")

    revenue_90d = (
        await db.scalar(
            select(func.coalesce(func.sum(Order.amount), Decimal("0.00")))
            .where(Order.status.in_(REVENUE_ORDER_STATUSES))
            .where(Order.created_at >= start_90d)
        )
    ) or Decimal("0.00")

    refunded_lifetime = (
        await db.scalar(select(func.coalesce(func.sum(Order.refunded_amount), Decimal("0.00"))))
    ) or Decimal("0.00")

    refunded_30d = (
        await db.scalar(
            select(func.coalesce(func.sum(Order.refunded_amount), Decimal("0.00"))).where(
                Order.created_at >= start_30d
            )
        )
    ) or Decimal("0.00")

    completed_cnt = int(
        (await db.scalar(select(func.count(Order.id)).where(Order.status == OrderStatus.COMPLETED))) or 0
    )

    ai_cost_total = (
        await db.scalar(select(func.coalesce(func.sum(Order.ai_cost_amount), Decimal("0.00"))))
    ) or Decimal("0.00")
    infra_total = (
        await db.scalar(select(func.coalesce(func.sum(Order.infra_cost_amount), Decimal("0.00"))))
    ) or Decimal("0.00")
    fee_total = (
        await db.scalar(select(func.coalesce(func.sum(Order.payment_fee_amount), Decimal("0.00"))))
    ) or Decimal("0.00")
    variable_total = (
        await db.scalar(select(func.coalesce(func.sum(Order.variable_cost_amount), Decimal("0.00"))))
    ) or Decimal("0.00")

    cost_stack = ai_cost_total + infra_total + fee_total + variable_total
    net_after_costs = revenue_lifetime - cost_stack
    contribution_margin = (
        float(net_after_costs / revenue_lifetime) if revenue_lifetime > 0 else 0.0
    )
    roi_vs_ai = (
        float((revenue_lifetime - cost_stack) / ai_cost_total * 100) if ai_cost_total > 0 else 0.0
    )

    avg_ai_per_completed = (
        float(ai_cost_total / Decimal(completed_cnt)) if completed_cnt else 0.0
    )

    arpu = float(revenue_lifetime / Decimal(users_total)) if users_total else 0.0

    mrr_history: list[MrrPoint] = []
    ai_cost_history: list[MonthAmount] = []
    for i in range(5, -1, -1):
        month_start, month_end = _month_bounds(now, i)
        month_label_key = month_start.month

        month_rev = float(
            (
                await db.scalar(
                    select(func.coalesce(func.sum(Order.amount), Decimal("0")))
                    .where(Order.status.in_(REVENUE_ORDER_STATUSES))
                    .where(Order.created_at >= month_start)
                    .where(Order.created_at < month_end)
                )
            )
            or 0
        )
        mrr_history.append(MrrPoint(month=MONTHS_RU[month_label_key], mrr=round(month_rev, 2)))

        month_ai = float(
            (
                await db.scalar(
                    select(func.coalesce(func.sum(Order.ai_cost_amount), Decimal("0")))
                    .where(Order.created_at >= month_start)
                    .where(Order.created_at < month_end)
                )
            )
            or 0
        )
        ai_cost_history.append(MonthAmount(month=MONTHS_RU[month_label_key], amount_rub=round(month_ai, 2)))

    tariff_rows = (
        await db.execute(
            select(
                Tariff.code,
                Tariff.name,
                func.coalesce(func.sum(Order.amount), Decimal("0")),
                func.coalesce(func.sum(Order.ai_cost_amount), Decimal("0")),
            )
            .select_from(Order)
            .join(Tariff, Order.tariff_id == Tariff.id)
            .where(
                Order.status.in_(
                    (OrderStatus.PAID, OrderStatus.COMPLETED, OrderStatus.REFUNDED)
                )
            )
            .group_by(Tariff.id, Tariff.code, Tariff.name)
            .order_by(func.sum(Order.amount).desc())
        )
    ).all()

    tariff_kpis = [
        TariffKpiRow(
            tariff_code=str(code),
            tariff_name=str(name),
            revenue_rub=float(rev or 0),
            ai_cost_rub=float(ai or 0),
        )
        for code, name, rev, ai in tariff_rows
    ]

    return AdminDashboardSummary(
        order_metrics=OrderMetricsBlock(**raw),
        analytics_stub=False,
        business_metrics={
            "users_total": users_total,
            "mrr": round(float(revenue_lifetime), 2),
            "new_mrr": round(float(revenue_30d), 2),
            "revenue_90d_rub": round(float(revenue_90d), 2),
            "churn_mrr": round(float(refunded_30d), 2),
            "refunds_lifetime_rub": round(float(refunded_lifetime), 2),
            "ltv": round(arpu, 2),
        },
        llm_metrics={
            "llm_cost": round(float(ai_cost_total), 2),
            "infra_cost_rub": round(float(infra_total), 2),
            "payment_fee_rub": round(float(fee_total), 2),
            "variable_cost_rub": round(float(variable_total), 2),
            "roi_pct": round(roi_vs_ai, 2),
            "contribution_margin_pct": round(contribution_margin * 100, 2),
            "avg_report_cost": round(avg_ai_per_completed, 2),
        },
        mrr_history=mrr_history,
        ai_cost_history=ai_cost_history,
        tariff_kpis=tariff_kpis,
    )
