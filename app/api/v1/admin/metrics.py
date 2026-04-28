from __future__ import annotations

from calendar import monthrange
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.deps import get_current_admin_user
from app.db.session import get_db
from app.models.analytics_event import AnalyticsEvent
from app.models.marketing_spend_manual import MarketingSpendManual
from app.models.order import Order, OrderStatus
from app.models.promocode import Promocode, PromocodeRedemption
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.tariff import Tariff
from app.models.user import User
from app.schemas.admin_extra import (
    CampaignPerformanceOut,
    CampaignPerformanceRow,
    ChannelCacRow,
    CohortRow,
    MarketingSpendCreate,
    MarketingSpendRow,
    MetricsCohortsOut,
    MetricsEconomicsOut,
    MetricsFunnelOut,
    MetricsOverviewOut,
    MetricValueCard,
    OneTimeMonthRow,
    OneTimeMonthlyOut,
    PromoPerformanceOut,
    PromoPerformanceRow,
    ReportOptionsAnalyticsOut,
    SubscriptionExportRow,
    SubscriptionListOut,
    SubscriptionMonthRow,
    SubscriptionsOverviewOut,
)
from app.schemas.admin_extra import FunnelStep
from app.services.admin_logs import append_admin_log
from app.services.analytics import fetch_addon_counts, fetch_first_paid_users_by_period, fetch_paid_orders_revenue, record_analytics_event
from app.services.event_based_metrics import (
    compute_campaign_performance,
    compute_channel_cac_rows,
    compute_funnel_steps,
    compute_growth_metrics,
    compute_retention_cohorts,
)
from app.services.report_option_pricing import aggregate_report_option_analytics

router = APIRouter()

_MONTHS_RU = {
    1: "Янв", 2: "Фев", 3: "Мар", 4: "Апр", 5: "Май", 6: "Июн",
    7: "Июл", 8: "Авг", 9: "Сен", 10: "Окт", 11: "Ноя", 12: "Дек",
}


def _last_n_calendar_months(n: int) -> list[tuple[int, int]]:
    now = datetime.now(timezone.utc)
    y, m = now.year, now.month
    buckets: list[tuple[int, int]] = []
    for _ in range(n):
        buckets.append((y, m))
        m -= 1
        if m < 1:
            m = 12
            y -= 1
    return list(reversed(buckets))


def _month_window_utc(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    return start, end


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


@router.get(
    "/campaign-performance",
    response_model=CampaignPerformanceOut,
    summary="UTM / кампания: конверсии и выручка (события)",
)
async def campaign_performance(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    group_by: Literal["campaign", "source"] = Query(default="campaign"),
    billing_segment: Literal["all", "one_time", "subscription"] = Query(default="all"),
):
    now = datetime.now(timezone.utc)
    if date_from and date_to:
        start_at, end_at = date_from, date_to
        if end_at <= start_at:
            start_at, end_at = end_at - timedelta(days=30), end_at
    else:
        end_at = now
        start_at = end_at - timedelta(days=30)
    seg_filter = None if billing_segment == "all" else billing_segment
    rows_raw, methodology = await compute_campaign_performance(
        db,
        start_at,
        end_at,
        group_by=group_by,
        billing_segment=seg_filter,
    )
    rows = [CampaignPerformanceRow(**r) for r in rows_raw]
    return CampaignPerformanceOut(
        period_start=start_at,
        period_end=end_at,
        group_by=group_by,
        billing_segment=billing_segment,
        methodology=methodology,
        rows=rows,
    )


@router.get(
    "/campaign-performance/one-time",
    response_model=CampaignPerformanceOut,
    summary="Кампании: только разовые заказы (billing_type one_time)",
)
async def campaign_performance_one_time(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    group_by: Literal["campaign", "source"] = Query(default="campaign"),
):
    now = datetime.now(timezone.utc)
    if date_from and date_to:
        start_at, end_at = date_from, date_to
        if end_at <= start_at:
            start_at, end_at = end_at - timedelta(days=30), end_at
    else:
        end_at = now
        start_at = end_at - timedelta(days=30)
    rows_raw, methodology = await compute_campaign_performance(
        db,
        start_at,
        end_at,
        group_by=group_by,
        billing_segment="one_time",
    )
    rows = [CampaignPerformanceRow(**r) for r in rows_raw]
    return CampaignPerformanceOut(
        period_start=start_at,
        period_end=end_at,
        group_by=group_by,
        billing_segment="one_time",
        methodology=methodology,
        rows=rows,
    )


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


@router.get("/one-time-monthly", response_model=OneTimeMonthlyOut, summary="Разовые продажи по месяцам")
async def one_time_monthly(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
    months: int = Query(default=12, ge=1, le=36),
):
    methodology = (
        "Заказы со статусами paid и completed, tariffs.billing_type = one_time; "
        "AOV = revenue / orders_count."
    )
    rows: list[OneTimeMonthRow] = []
    for y, m in _last_n_calendar_months(months):
        ms, me = _month_window_utc(y, m)
        rev, cnt = (
            await db.execute(
                select(
                    func.coalesce(func.sum(Order.amount), Decimal("0")),
                    func.count(Order.id),
                )
                .select_from(Order)
                .join(Tariff, Tariff.id == Order.tariff_id)
                .where(
                    Tariff.billing_type == "one_time",
                    Order.status.in_((OrderStatus.PAID, OrderStatus.COMPLETED)),
                    Order.created_at >= ms,
                    Order.created_at < me,
                )
            )
        ).one()
        revenue = float(rev or 0)
        orders_count = int(cnt or 0)
        aov = revenue / orders_count if orders_count else 0.0
        rows.append(
            OneTimeMonthRow(
                month=f"{_MONTHS_RU[m]} {y}",
                orders_count=orders_count,
                revenue_rub=round(revenue, 2),
                aov_rub=round(aov, 2),
            )
        )
    return OneTimeMonthlyOut(methodology=methodology, rows=rows)


@router.get(
    "/report-options-analytics",
    response_model=ReportOptionsAnalyticsOut,
    summary="Аналитика тумблеров report/bundle",
)
async def report_options_analytics(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    raw = await aggregate_report_option_analytics(db)
    methodology = (
        "Последние заказы с непустым report_option_flags (до 3000 строк). "
        "Оценка выручки опций — compute_toggle_line по app_settings, без скидки промокода на тариф."
    )
    return ReportOptionsAnalyticsOut(
        methodology=methodology,
        key_counts=raw["key_counts"],
        bucket_counts=raw["bucket_counts"],
        estimated_options_revenue_rub=raw["estimated_options_revenue_rub"],
        orders_sampled=raw["orders_sampled"],
    )


@router.get("/promo-performance", response_model=PromoPerformanceOut, summary="Эффективность промокодов")
async def promo_performance(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    methodology = (
        "promocode_redemptions ⋈ orders: число погашений, сумма discount_amount, сумма amount заказов (выручка чека)."
    )
    stmt = (
        select(
            Promocode.code,
            func.count(PromocodeRedemption.id),
            func.coalesce(func.sum(PromocodeRedemption.discount_amount), Decimal("0")),
            func.coalesce(func.sum(Order.amount), Decimal("0")),
        )
        .select_from(PromocodeRedemption)
        .join(Promocode, Promocode.id == PromocodeRedemption.promocode_id)
        .join(Order, Order.id == PromocodeRedemption.order_id)
        .group_by(Promocode.id, Promocode.code)
        .order_by(func.count(PromocodeRedemption.id).desc())
    )
    out_rows: list[PromoPerformanceRow] = []
    for code, red_cnt, disc_sum, ord_sum in (await db.execute(stmt)).all():
        out_rows.append(
            PromoPerformanceRow(
                promocode=str(code),
                redemptions=int(red_cnt or 0),
                discount_total_rub=float(disc_sum or 0),
                order_revenue_rub=float(ord_sum or 0),
            )
        )
    return PromoPerformanceOut(methodology=methodology, rows=out_rows)


@router.get(
    "/subscriptions-overview",
    response_model=SubscriptionsOverviewOut,
    summary="Подписки: активные, новые, выручка заказов и продлений по месяцам",
)
async def subscriptions_overview(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
    months: int = Query(default=12, ge=1, le=36),
):
    now = datetime.now(timezone.utc)
    methodology = (
        "Новые подписки — по subscriptions.created_at. Выручка первых платежей — заказы paid/completed "
        "с tariffs.billing_type = subscription. Продления — событие subscription_renewal_payment (webhook без order)."
    )
    active = int(
        (
            await db.scalar(
                select(func.count(Subscription.id)).where(
                    Subscription.status == SubscriptionStatus.ACTIVE.value,
                    or_(
                        Subscription.current_period_end.is_(None),
                        Subscription.current_period_end > now,
                    ),
                )
            )
        )
        or 0
    )
    monthly_rows: list[SubscriptionMonthRow] = []
    for y, m in _last_n_calendar_months(months):
        ms, me = _month_window_utc(y, m)
        new_subs = int(
            (
                await db.scalar(
                    select(func.count(Subscription.id)).where(
                        Subscription.created_at >= ms,
                        Subscription.created_at < me,
                    )
                )
            )
            or 0
        )
        sub_orders = (
            await db.execute(
                select(
                    func.count(Order.id),
                    func.coalesce(func.sum(Order.amount), Decimal("0")),
                )
                .select_from(Order)
                .join(Tariff, Tariff.id == Order.tariff_id)
                .where(
                    Tariff.billing_type == "subscription",
                    Order.status.in_((OrderStatus.PAID, OrderStatus.COMPLETED)),
                    Order.created_at >= ms,
                    Order.created_at < me,
                )
            )
        ).one()
        first_pay_cnt = int(sub_orders[0] or 0)
        sub_rev = float(sub_orders[1] or 0)
        ren = (
            await db.scalar(
                select(func.coalesce(func.sum(AnalyticsEvent.amount), 0)).where(
                    AnalyticsEvent.event_name == "subscription_renewal_payment",
                    AnalyticsEvent.event_time >= ms,
                    AnalyticsEvent.event_time < me,
                )
            )
        ) or 0
        monthly_rows.append(
            SubscriptionMonthRow(
                month=f"{_MONTHS_RU[m]} {y}",
                new_subscriptions=new_subs,
                first_payment_orders=first_pay_cnt,
                subscription_order_revenue_rub=round(sub_rev, 2),
                renewal_revenue_rub=round(float(ren), 2),
            )
        )
    return SubscriptionsOverviewOut(
        methodology=methodology,
        active_subscriptions_now=active,
        monthly_rows=monthly_rows,
    )


@router.get("/subscriptions-list", response_model=SubscriptionListOut, summary="Список подписок (админ)")
async def subscriptions_list(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
    limit: int = Query(default=500, ge=1, le=5000),
):
    stmt = (
        select(Subscription)
        .options(joinedload(Subscription.tariff))
        .order_by(Subscription.created_at.desc())
        .limit(limit)
    )
    subs = (await db.execute(stmt)).unique().scalars().all()
    rows = [
        SubscriptionExportRow(
            id=s.id,
            user_id=s.user_id,
            tariff_code=s.tariff.code if s.tariff else "",
            status=s.status,
            current_period_start=s.current_period_start,
            current_period_end=s.current_period_end,
            created_at=s.created_at,
        )
        for s in subs
    ]
    return SubscriptionListOut(rows=rows)


# ── LLM аналитика ─────────────────────────────────────────────────────────────

@router.get(
    "/llm-usage",
    response_model=None,
    summary="LLM: использование по провайдерам",
)
async def llm_usage(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    from app.models.llm_usage_log import LlmUsageLog
    from app.schemas.admin_extra import LlmProviderUsageRow, LlmUsageOut

    now = datetime.now(timezone.utc)
    period_start = date_from or now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    period_end = date_to or now

    stmt = (
        select(
            LlmUsageLog.provider,
            func.count(LlmUsageLog.id).label("calls_count"),
            func.sum(LlmUsageLog.cost_rub).label("total_cost_rub"),
            func.sum(LlmUsageLog.cached_tokens).label("cached_tokens"),
        )
        .where(LlmUsageLog.created_at >= period_start, LlmUsageLog.created_at <= period_end)
        .group_by(LlmUsageLog.provider)
    )
    results = (await db.execute(stmt)).all()

    total_calls = sum(r.calls_count for r in results)
    total_cost = float(sum(r.total_cost_rub or 0 for r in results))

    rows = [
        LlmProviderUsageRow(
            provider=r.provider,
            calls_count=r.calls_count,
            cost_rub=float(r.total_cost_rub or 0),
            cached_tokens=r.cached_tokens or 0,
            pct_of_total=round(r.calls_count / total_calls * 100, 1) if total_calls else 0.0,
        )
        for r in sorted(results, key=lambda x: x.calls_count, reverse=True)
    ]

    most_used = rows[0].provider if rows else None
    return LlmUsageOut(
        period_start=period_start,
        period_end=period_end,
        rows=rows,
        most_used_provider=most_used,
        total_calls=total_calls,
        total_cost_rub=total_cost,
    )


@router.get(
    "/llm-margin",
    response_model=None,
    summary="LLM: маржинальность по провайдерам",
)
async def llm_margin(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    from app.models.llm_usage_log import LlmUsageLog
    from app.models.report import Report
    from app.schemas.admin_extra import LlmMarginRow, LlmMarginOut

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    async def _margin_rows(date_from: datetime | None) -> list[LlmMarginRow]:
        cost_stmt = (
            select(
                LlmUsageLog.provider,
                func.sum(LlmUsageLog.cost_rub).label("ai_cost_rub"),
            )
            .group_by(LlmUsageLog.provider)
        )
        if date_from:
            cost_stmt = cost_stmt.where(LlmUsageLog.created_at >= date_from)
        cost_rows = {r.provider: float(r.ai_cost_rub or 0) for r in (await db.execute(cost_stmt)).all()}

        # Revenue: из заказов с llm_provider через отчёты
        rev_stmt = (
            select(
                Report.llm_provider,
                func.sum(Order.amount).label("revenue_rub"),
            )
            .join(Order, Order.id == Report.order_id)
            .where(Report.llm_provider.is_not(None))
            .group_by(Report.llm_provider)
        )
        if date_from:
            rev_stmt = rev_stmt.where(Report.generated_at >= date_from)
        rev_rows = {r.llm_provider: float(r.revenue_rub or 0) for r in (await db.execute(rev_stmt)).all()}

        providers = set(list(cost_rows.keys()) + list(rev_rows.keys()))
        result = []
        for p in sorted(providers):
            rev = rev_rows.get(p, 0.0)
            cost = cost_rows.get(p, 0.0)
            margin = rev - cost
            result.append(LlmMarginRow(
                provider=p,
                revenue_rub=rev,
                ai_cost_rub=cost,
                margin_rub=margin,
                margin_pct=round(margin / rev * 100, 1) if rev else 0.0,
            ))
        return result

    current_month = await _margin_rows(month_start)
    total = await _margin_rows(None)
    return LlmMarginOut(current_month=current_month, total=total)
