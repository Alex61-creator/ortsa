from __future__ import annotations

from calendar import monthrange
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user
from app.db.session import get_db
from app.models.marketing_spend_manual import MarketingSpendManual
from app.models.order import Order, OrderStatus
from app.models.tariff import Tariff
from app.models.user import User
from app.schemas.admin_extra import (
    ChannelCacRow,
    CohortRow,
    MarketingSpendCreate,
    MarketingSpendRow,
    MetricsCohortsOut,
    MetricsEconomicsOut,
    MetricsFunnelOut,
    MetricsOverviewOut,
    MetricValueCard,
)
from app.schemas.admin_extra import FunnelStep
from app.services.admin_logs import append_admin_log
from app.services.analytics import fetch_addon_counts, fetch_first_paid_users_by_period, fetch_paid_orders_revenue, record_analytics_event
from app.services.event_based_metrics import compute_funnel_steps, compute_growth_metrics, compute_retention_cohorts
from app.services.event_based_metrics import compute_channel_cac_rows

router = APIRouter()


def _period_bounds(period: str, date_from: datetime | None, date_to: datetime | None) -> tuple[datetime, datetime, datetime, datetime]:
    now = datetime.now(timezone.utc)
    if date_from and date_to:
        start_at = date_from
        end_at = date_to
    elif period == "wow":
        end_at = now
        start_at = now - timedelta(days=7)
    elif period == "qoq":
        end_at = now
        start_at = now - timedelta(days=90)
    else:
        start_at = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        last_day = monthrange(now.year, now.month)[1]
        end_at = datetime(now.year, now.month, last_day, 23, 59, 59, tzinfo=timezone.utc) + timedelta(seconds=1)

    length = end_at - start_at
    prev_end = start_at
    prev_start = start_at - length
    return start_at, end_at, prev_start, prev_end


async def _compute_growth_metrics(
    db: AsyncSession,
    start_at: datetime,
    end_at: datetime,
) -> dict:
    signups = int((await db.scalar(select(func.count(User.id)).where(User.created_at >= start_at, User.created_at < end_at))) or 0)
    first_paid_users = await fetch_first_paid_users_by_period(db, start_at, end_at)
    revenue, paid_orders = await fetch_paid_orders_revenue(db, start_at, end_at)
    addon_orders, eligible_orders = await fetch_addon_counts(db, start_at, end_at)
    refunded = Decimal((await db.scalar(select(func.coalesce(func.sum(Order.refunded_amount), Decimal("0.00"))).where(Order.created_at >= start_at, Order.created_at < end_at))) or Decimal("0.00"))
    variable_costs = Decimal((await db.scalar(select(func.coalesce(func.sum(Order.variable_cost_amount + Order.payment_fee_amount + Order.ai_cost_amount + Order.infra_cost_amount), Decimal("0.00"))).where(Order.created_at >= start_at, Order.created_at < end_at))) or Decimal("0.00"))
    spend = Decimal((await db.scalar(select(func.coalesce(func.sum(MarketingSpendManual.spend_amount), Decimal("0.00"))).where(MarketingSpendManual.period_start < end_at, MarketingSpendManual.period_end >= start_at))) or Decimal("0.00"))

    cr1 = (first_paid_users / signups) if signups else 0.0
    aov = float(revenue / paid_orders) if paid_orders else 0.0
    attach_rate = (addon_orders / eligible_orders) if eligible_orders else 0.0
    blended_cac = float(spend / first_paid_users) if first_paid_users else 0.0
    gross_profit = revenue - refunded - variable_costs
    ltv = float(gross_profit / first_paid_users) if first_paid_users else 0.0
    ltv_cac = (ltv / blended_cac) if blended_cac else 0.0
    contribution_margin = float(gross_profit / revenue) if revenue else 0.0

    return {
        "signups": signups,
        "first_paid_users": first_paid_users,
        "revenue": float(revenue),
        "paid_orders": paid_orders,
        "addon_orders": addon_orders,
        "eligible_orders": eligible_orders,
        "spend": float(spend),
        "refunded": float(refunded),
        "variable_costs": float(variable_costs),
        "cr1": cr1,
        "aov": aov,
        "attach_rate": attach_rate,
        "blended_cac": blended_cac,
        "ltv": ltv,
        "ltv_cac": ltv_cac,
        "contribution_margin": contribution_margin,
    }


async def _channel_cac_rows(db: AsyncSession, start_at: datetime, end_at: datetime) -> list[ChannelCacRow]:
    spend_rows = (
        await db.execute(
            select(MarketingSpendManual.channel, func.coalesce(func.sum(MarketingSpendManual.spend_amount), Decimal("0.00")))
            .where(MarketingSpendManual.period_start < end_at, MarketingSpendManual.period_end >= start_at)
            .group_by(MarketingSpendManual.channel)
        )
    ).all()
    rows: list[ChannelCacRow] = []
    for channel, spend in spend_rows:
        first_paid = await fetch_first_paid_users_by_period(db, start_at, end_at, channel=channel)
        spend_amount = float(spend or 0)
        rows.append(
            ChannelCacRow(
                channel=channel,
                spend=spend_amount,
                first_paid_users=first_paid,
                cac=(spend_amount / first_paid) if first_paid else 0.0,
            )
        )
    return rows


@router.get("/spend", response_model=list[MarketingSpendRow], summary="Маркетинговые расходы")
async def list_manual_spend(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
    channel: str | None = Query(default=None),
):
    stmt = select(MarketingSpendManual).order_by(MarketingSpendManual.period_start.desc())
    if channel:
        stmt = stmt.where(MarketingSpendManual.channel == channel)
    rows = (await db.execute(stmt)).scalars().all()
    return [MarketingSpendRow.model_validate(row) for row in rows]


@router.post("/spend", response_model=MarketingSpendRow, summary="Добавить маркетинговый расход")
async def create_manual_spend(
    payload: MarketingSpendCreate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_admin_user),
):
    row = MarketingSpendManual(
        period_start=payload.period_start,
        period_end=payload.period_end,
        channel=payload.channel,
        campaign_name=payload.campaign_name,
        spend_amount=payload.spend_amount,
        currency=payload.currency,
        notes=payload.notes,
        created_by=actor.email or f"user:{actor.id}",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    await append_admin_log(db, actor.email or f"user:{actor.id}", "acquisition_cost_recorded", f"spend:{row.channel}", details={"amount": str(row.spend_amount)})

    await record_analytics_event(
        db,
        event_name="acquisition_cost_recorded",
        user_id=None,
        order_id=None,
        tariff_code=None,
        source_channel=payload.channel,
        utm_source=None,
        utm_medium=None,
        utm_campaign=None,
        platform=None,
        geo=None,
        amount=payload.spend_amount,
        currency=payload.currency,
        cost_components=None,
        correlation_id=None,
        dedupe_key=f"acquisition_cost_recorded:{row.id}",
        event_time=payload.period_start,
        event_metadata={
            "campaign_name": payload.campaign_name,
            "notes": payload.notes,
            "period_start": payload.period_start.isoformat(),
            "period_end": payload.period_end.isoformat(),
        },
    )
    return MarketingSpendRow.model_validate(row)


@router.get("/overview", response_model=MetricsOverviewOut, summary="Growth metrics overview")
async def metrics_overview(
    period: str = Query(default="current_month"),
    compare: str = Query(default="mom"),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    tariff_code: str | None = Query(default=None),
    source_channel: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    start_at, end_at, prev_start, prev_end = _period_bounds(period, date_from, date_to)
    current = await compute_growth_metrics(db, start_at, end_at, tariff_code=tariff_code, source_channel=source_channel)
    previous = await compute_growth_metrics(db, prev_start, prev_end, tariff_code=tariff_code, source_channel=source_channel)

    cohort_key_current = start_at.strftime("%Y-%m")
    cohort_key_previous = prev_start.strftime("%Y-%m")
    current_cohorts = await compute_retention_cohorts(db, start_at, end_at, tariff_code=tariff_code, source_channel=source_channel)
    previous_cohorts = await compute_retention_cohorts(db, prev_start, prev_end, tariff_code=tariff_code, source_channel=source_channel)
    retention_m1_current_ratio = next((row.m1 for row in current_cohorts if row.cohort == cohort_key_current), 0.0) / 100.0
    retention_m1_previous_ratio = next((row.m1 for row in previous_cohorts if row.cohort == cohort_key_previous), 0.0) / 100.0

    def card(key: str, label: str, value: float, previous_value: float, unit: str | None = None, threshold: float | None = None) -> MetricValueCard:
        delta_pct = ((value - previous_value) / previous_value * 100) if previous_value else None
        status = None
        hint = None
        if threshold is not None and value < threshold:
            status = "warning"
        if key == "cr1" and value < 0.08:
            hint = "Проверить оффер и шаг оплаты."
        elif key == "attach_rate" and value < 0.1:
            hint = "Проверить placement add-on."
        elif key == "ltv_cac" and value < 2:
            hint = "Проверить CAC по каналам и margin."
        return MetricValueCard(key=key, label=label, value=value, previous_value=previous_value, delta_pct=delta_pct, unit=unit, status=status, hint=hint)

    cards = [
        card("cr1", "CR1", current["cr1"], previous["cr1"], unit="ratio"),
        card("aov", "AOV", current["aov"], previous["aov"], unit="RUB"),
        card("attach_rate", "Attach-rate", current["attach_rate"], previous["attach_rate"], unit="ratio"),
        card("retention_m1", "Retention M1", retention_m1_current_ratio, retention_m1_previous_ratio, unit="ratio"),
        card("ltv_cac", "LTV/CAC", current["ltv_cac"], previous["ltv_cac"], unit="ratio"),
        card("contribution_margin", "Contribution Margin", current["contribution_margin"], previous["contribution_margin"], unit="ratio"),
    ]
    alerts: list[str] = []
    if current["cr1"] < 0.08:
        alerts.append("CR1 ниже целевого порога.")
    if current["attach_rate"] < 0.10:
        alerts.append("Attach-rate add-on ухудшился.")
    if current["ltv_cac"] < 2:
        alerts.append("LTV/CAC ниже безопасного уровня.")
    if current["contribution_margin"] < 0.35:
        alerts.append("Contribution margin ниже порога.")
    return MetricsOverviewOut(period_start=start_at, period_end=end_at, cards=cards, alerts=alerts)


@router.get("/funnel", response_model=MetricsFunnelOut, summary="Growth funnel")
async def metrics_funnel(
    period: str = Query(default="current_month"),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    tariff_code: str | None = Query(default=None),
    source_channel: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    start_at, end_at, _, _ = _period_bounds(period, date_from, date_to)
    steps = await compute_funnel_steps(
        db,
        start_at,
        end_at,
        tariff_code=tariff_code,
        source_channel=source_channel,
    )
    return MetricsFunnelOut(period_start=start_at, period_end=end_at, steps=steps)


@router.get("/cohorts", response_model=MetricsCohortsOut, summary="Growth cohorts")
async def metrics_cohorts(
    period: str = Query(default="current_month"),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    tariff_code: str | None = Query(default=None),
    source_channel: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    start_at, end_at, _, _ = _period_bounds(period, date_from, date_to)
    rows = await compute_retention_cohorts(
        db,
        start_at,
        end_at,
        tariff_code=tariff_code,
        source_channel=source_channel,
    )
    return MetricsCohortsOut(period_start=start_at, period_end=end_at, rows=rows)


@router.get("/economics", response_model=MetricsEconomicsOut, summary="Growth economics")
async def metrics_economics(
    period: str = Query(default="current_month"),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    tariff_code: str | None = Query(default=None),
    source_channel: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    start_at, end_at, _, _ = _period_bounds(period, date_from, date_to)
    current = await compute_growth_metrics(
        db,
        start_at,
        end_at,
        tariff_code=tariff_code,
        source_channel=source_channel,
    )

    channel_rows = await compute_channel_cac_rows(
        db,
        start_at,
        end_at,
        tariff_code=tariff_code,
    )
    if source_channel is not None:
        channel_rows = [r for r in channel_rows if r.channel == source_channel]

    hints: list[str] = []
    if current["cr1"] < 0.08:
        hints.append("Пересмотреть оффер и шаг авторизации/оплаты.")
    if current["attach_rate"] < 0.10:
        hints.append("Изменить placement add-on в продуктовой воронке.")
    if current["blended_cac"] > 0 and current["ltv_cac"] < 2:
        hints.append("Проверить CAC по каналам и отключить убыточные кампании.")
    if current["contribution_margin"] < 0.35:
        hints.append("Проверить рост variable costs, AI/infra и fees.")
    return MetricsEconomicsOut(
        period_start=start_at,
        period_end=end_at,
        blended_cac=current["blended_cac"],
        ltv_cac=current["ltv_cac"],
        contribution_margin=current["contribution_margin"],
        aov=current["aov"],
        attach_rate=current["attach_rate"],
        channel_cac=channel_rows,
        action_hints=hints,
    )
