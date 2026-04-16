from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics_event import AnalyticsEvent
from app.models.order import Order
from app.models.tariff import Tariff
from app.schemas.admin_extra import ChannelCacRow, CohortRow, FunnelStep

ELIGIBLE_BASE_TARIFFS: set[str] = {"bundle", "report", "sub_monthly", "sub_annual"}


def _month_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def _month_index(dt: datetime) -> int:
    return dt.year * 12 + dt.month


async def _distinct_user_ids(db: AsyncSession, stmt) -> set[int]:
    rows = await db.execute(stmt)
    return {int(u) for u in rows.scalars().all() if u is not None}


async def compute_funnel_steps(
    db: AsyncSession,
    start_at: datetime,
    end_at: datetime,
    *,
    tariff_code: str | None = None,
    source_channel: str | None = None,
) -> list[FunnelStep]:
    # Signup_completed events can have tariff_code = NULL, so if tariff_code filter is set,
    # derive signup segmentation from the user's first_purchase_completed tariff_code.
    first_purchase_subq = None
    if tariff_code is not None:
        first_purchase_subq = (
            select(
                AnalyticsEvent.user_id.label("user_id"),
                AnalyticsEvent.tariff_code.label("tariff_code"),
            )
            .where(AnalyticsEvent.event_name == "first_purchase_completed")
            .subquery()
        )

    signup_stmt = select(func.count(func.distinct(AnalyticsEvent.user_id))).where(
        AnalyticsEvent.event_name == "signup_completed",
        AnalyticsEvent.event_time >= start_at,
        AnalyticsEvent.event_time < end_at,
    )
    if source_channel is not None:
        signup_stmt = signup_stmt.where(AnalyticsEvent.source_channel == source_channel)
    if first_purchase_subq is not None:
        signup_stmt = (
            signup_stmt.select_from(AnalyticsEvent)
            .join(first_purchase_subq, AnalyticsEvent.user_id == first_purchase_subq.c.user_id)
            .where(first_purchase_subq.c.tariff_code == tariff_code)
        )

    paid_stmt = select(func.count(func.distinct(AnalyticsEvent.user_id))).where(
        AnalyticsEvent.event_name == "first_purchase_completed",
        AnalyticsEvent.event_time >= start_at,
        AnalyticsEvent.event_time < end_at,
    )
    if tariff_code is not None:
        paid_stmt = paid_stmt.where(AnalyticsEvent.tariff_code == tariff_code)
    if source_channel is not None:
        paid_stmt = paid_stmt.where(AnalyticsEvent.source_channel == source_channel)

    completed_stmt = select(func.count(func.distinct(AnalyticsEvent.order_id))).where(
        AnalyticsEvent.event_name == "order_completed",
        AnalyticsEvent.event_time >= start_at,
        AnalyticsEvent.event_time < end_at,
    )
    if tariff_code is not None:
        completed_stmt = completed_stmt.where(AnalyticsEvent.tariff_code == tariff_code)
    if source_channel is not None:
        completed_stmt = completed_stmt.where(AnalyticsEvent.source_channel == source_channel)

    addon_stmt = select(func.count(func.distinct(AnalyticsEvent.order_id))).where(
        AnalyticsEvent.event_name == "addon_attached",
        AnalyticsEvent.event_time >= start_at,
        AnalyticsEvent.event_time < end_at,
    )
    if source_channel is not None:
        addon_stmt = addon_stmt.where(AnalyticsEvent.source_channel == source_channel)
    # Add-ons are emitted under `tariff_code="synastry_addon"`, but when
    # UI filters by a base `tariff_code`, we must still count add-ons
    # for users belonging to that base segment.
    addon_stmt = addon_stmt.where(AnalyticsEvent.tariff_code == "synastry_addon")
    if tariff_code is not None:
        segment_users_subq = (
            select(func.distinct(AnalyticsEvent.user_id))
            .where(
                AnalyticsEvent.event_name == "first_purchase_completed",
                AnalyticsEvent.event_time >= start_at,
                AnalyticsEvent.event_time < end_at,
            )
        )
        segment_users_subq = segment_users_subq.where(AnalyticsEvent.tariff_code == tariff_code)
        if source_channel is not None:
            segment_users_subq = segment_users_subq.where(AnalyticsEvent.source_channel == source_channel)
        addon_stmt = addon_stmt.where(AnalyticsEvent.user_id.in_(segment_users_subq))

    eligible_stmt = select(func.count(func.distinct(AnalyticsEvent.order_id))).where(
        AnalyticsEvent.event_name == "order_completed",
        AnalyticsEvent.event_time >= start_at,
        AnalyticsEvent.event_time < end_at,
        AnalyticsEvent.tariff_code.in_(list(ELIGIBLE_BASE_TARIFFS)),
    )
    if source_channel is not None:
        eligible_stmt = eligible_stmt.where(AnalyticsEvent.source_channel == source_channel)
    if tariff_code is not None:
        # If tariff_code filter is set, intersect it with eligible base tariffs.
        eligible_stmt = eligible_stmt.where(AnalyticsEvent.tariff_code == tariff_code)

    signups = int((await db.scalar(signup_stmt)) or 0)
    first_paid_users = int((await db.scalar(paid_stmt)) or 0)
    completed_orders = int((await db.scalar(completed_stmt)) or 0)
    addon_orders = int((await db.scalar(addon_stmt)) or 0)
    eligible_orders = int((await db.scalar(eligible_stmt)) or 0)

    def pct(num: int, den: int) -> float:
        return round((num / den) * 100, 1) if den else 0.0

    return [
        FunnelStep(key="signup", title="Signup", count=signups, conversion_pct=100.0 if signups else 0.0),
        FunnelStep(
            key="first_purchase",
            title="First Purchase",
            count=first_paid_users,
            conversion_pct=pct(first_paid_users, signups),
        ),
        FunnelStep(
            key="completed",
            title="Completed Orders",
            count=completed_orders,
            conversion_pct=pct(completed_orders, signups),
        ),
        FunnelStep(
            key="addon",
            title="Addon Attached",
            count=addon_orders,
            conversion_pct=pct(addon_orders, eligible_orders),
        ),
    ]


async def compute_growth_metrics(
    db: AsyncSession,
    start_at: datetime,
    end_at: datetime,
    *,
    tariff_code: str | None = None,
    source_channel: str | None = None,
) -> dict:
    # Signups + first paid users.
    first_purchase_subq = None
    if tariff_code is not None:
        first_purchase_subq = (
            select(
                AnalyticsEvent.user_id.label("user_id"),
                AnalyticsEvent.tariff_code.label("tariff_code"),
            )
            .where(AnalyticsEvent.event_name == "first_purchase_completed")
            .subquery()
        )

    signups_stmt = select(func.count(func.distinct(AnalyticsEvent.user_id))).where(
        AnalyticsEvent.event_name == "signup_completed",
        AnalyticsEvent.event_time >= start_at,
        AnalyticsEvent.event_time < end_at,
    )
    if source_channel is not None:
        signups_stmt = signups_stmt.where(AnalyticsEvent.source_channel == source_channel)
    if first_purchase_subq is not None:
        signups_stmt = (
            signups_stmt.select_from(AnalyticsEvent)
            .join(first_purchase_subq, AnalyticsEvent.user_id == first_purchase_subq.c.user_id)
            .where(first_purchase_subq.c.tariff_code == tariff_code)
        )

    first_paid_stmt = select(func.count(func.distinct(AnalyticsEvent.user_id))).where(
        AnalyticsEvent.event_name == "first_purchase_completed",
        AnalyticsEvent.event_time >= start_at,
        AnalyticsEvent.event_time < end_at,
    )
    if tariff_code is not None:
        first_paid_stmt = first_paid_stmt.where(AnalyticsEvent.tariff_code == tariff_code)
    if source_channel is not None:
        first_paid_stmt = first_paid_stmt.where(AnalyticsEvent.source_channel == source_channel)

    signups = int((await db.scalar(signups_stmt)) or 0)
    first_paid_users = int((await db.scalar(first_paid_stmt)) or 0)

    # Orders: revenue + costs + paid_orders.
    orders_stmt = select(AnalyticsEvent.order_id, AnalyticsEvent.amount, AnalyticsEvent.cost_components).where(
        AnalyticsEvent.event_name == "order_completed",
        AnalyticsEvent.event_time >= start_at,
        AnalyticsEvent.event_time < end_at,
        AnalyticsEvent.order_id.is_not(None),
    )
    if tariff_code is not None:
        orders_stmt = orders_stmt.where(AnalyticsEvent.tariff_code == tariff_code)
    if source_channel is not None:
        orders_stmt = orders_stmt.where(AnalyticsEvent.source_channel == source_channel)

    orders_rows = (await db.execute(orders_stmt)).all()
    paid_orders = len({int(o[0]) for o in orders_rows if o[0] is not None})
    revenue = sum((o[1] or Decimal("0.00")) for o in orders_rows) if orders_rows else Decimal("0.00")

    variable_costs = Decimal("0.00")
    for _, __, cost_components in orders_rows:
        if not cost_components:
            continue
        variable_costs += Decimal(str(cost_components.get("variable_cost_amount") or 0))
        variable_costs += Decimal(str(cost_components.get("payment_fee_amount") or 0))
        variable_costs += Decimal(str(cost_components.get("ai_cost_amount") or 0))
        variable_costs += Decimal(str(cost_components.get("infra_cost_amount") or 0))

    # Refunds.
    refunds_stmt = select(func.coalesce(func.sum(AnalyticsEvent.amount), Decimal("0.00"))).where(
        AnalyticsEvent.event_name == "refund_completed",
        AnalyticsEvent.event_time >= start_at,
        AnalyticsEvent.event_time < end_at,
    )
    if tariff_code is not None:
        refunds_stmt = refunds_stmt.where(AnalyticsEvent.tariff_code == tariff_code)
    if source_channel is not None:
        refunds_stmt = refunds_stmt.where(AnalyticsEvent.source_channel == source_channel)
    refunded = await db.scalar(refunds_stmt) or Decimal("0.00")

    # Spend: acquisition_cost_recorded.
    spend_stmt = select(func.coalesce(func.sum(AnalyticsEvent.amount), Decimal("0.00"))).where(
        AnalyticsEvent.event_name == "acquisition_cost_recorded",
        AnalyticsEvent.event_time >= start_at,
        AnalyticsEvent.event_time < end_at,
    )
    if source_channel is not None:
        spend_stmt = spend_stmt.where(AnalyticsEvent.source_channel == source_channel)
    spend = await db.scalar(spend_stmt) or Decimal("0.00")

    # Attach-rate: addon_attached vs eligible base orders.
    addon_orders_stmt = select(func.count(func.distinct(AnalyticsEvent.order_id))).where(
        AnalyticsEvent.event_name == "addon_attached",
        AnalyticsEvent.event_time >= start_at,
        AnalyticsEvent.event_time < end_at,
        AnalyticsEvent.order_id.is_not(None),
    )
    eligible_orders_stmt = select(func.count(func.distinct(AnalyticsEvent.order_id))).where(
        AnalyticsEvent.event_name == "order_completed",
        AnalyticsEvent.event_time >= start_at,
        AnalyticsEvent.event_time < end_at,
        AnalyticsEvent.order_id.is_not(None),
        AnalyticsEvent.tariff_code.in_(list(ELIGIBLE_BASE_TARIFFS)),
    )
    if source_channel is not None:
        addon_orders_stmt = addon_orders_stmt.where(AnalyticsEvent.source_channel == source_channel)
        eligible_orders_stmt = eligible_orders_stmt.where(AnalyticsEvent.source_channel == source_channel)
    if tariff_code is not None:
        eligible_orders_stmt = eligible_orders_stmt.where(AnalyticsEvent.tariff_code == tariff_code)
    # Add-ons are emitted under synastry_addon.
    addon_orders_stmt = addon_orders_stmt.where(AnalyticsEvent.tariff_code == "synastry_addon")
    if tariff_code is not None:
        segment_users_subq = (
            select(func.distinct(AnalyticsEvent.user_id))
            .where(
                AnalyticsEvent.event_name == "first_purchase_completed",
                AnalyticsEvent.event_time >= start_at,
                AnalyticsEvent.event_time < end_at,
            )
            .where(AnalyticsEvent.tariff_code == tariff_code)
        )
        if source_channel is not None:
            segment_users_subq = segment_users_subq.where(AnalyticsEvent.source_channel == source_channel)
        addon_orders_stmt = addon_orders_stmt.where(AnalyticsEvent.user_id.in_(segment_users_subq))

    addon_orders = int((await db.scalar(addon_orders_stmt)) or 0)
    eligible_orders = int((await db.scalar(eligible_orders_stmt)) or 0)

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
        "gross_profit": float(gross_profit),
    }


async def compute_channel_cac_rows(
    db: AsyncSession,
    start_at: datetime,
    end_at: datetime,
    *,
    tariff_code: str | None = None,
) -> list[ChannelCacRow]:
    # Group spend by source_channel.
    stmt = select(AnalyticsEvent.source_channel, func.coalesce(func.sum(AnalyticsEvent.amount), Decimal("0.00"))).where(
        AnalyticsEvent.event_name == "acquisition_cost_recorded",
        AnalyticsEvent.event_time >= start_at,
        AnalyticsEvent.event_time < end_at,
        AnalyticsEvent.source_channel.is_not(None),
    ).group_by(AnalyticsEvent.source_channel)

    rows = (await db.execute(stmt)).all()
    channel_rows: list[ChannelCacRow] = []
    for channel, spend in rows:
        first_paid_stmt = select(func.count(func.distinct(AnalyticsEvent.user_id))).where(
            AnalyticsEvent.event_name == "first_purchase_completed",
            AnalyticsEvent.event_time >= start_at,
            AnalyticsEvent.event_time < end_at,
            AnalyticsEvent.source_channel == channel,
            AnalyticsEvent.user_id.is_not(None),
        )
        if tariff_code is not None:
            first_paid_stmt = first_paid_stmt.where(AnalyticsEvent.tariff_code == tariff_code)

        first_paid = int((await db.scalar(first_paid_stmt)) or 0)
        spend_amount = float(spend or 0)
        channel_rows.append(
            ChannelCacRow(
                channel=channel,
                spend=spend_amount,
                first_paid_users=first_paid,
                cac=(spend_amount / first_paid) if first_paid else 0.0,
            )
        )
    return channel_rows


async def compute_retention_cohorts(
    db: AsyncSession,
    start_at: datetime,
    end_at: datetime,
    *,
    tariff_code: str | None = None,
    source_channel: str | None = None,
) -> list[CohortRow]:
    cohort_anchor_start = start_at - timedelta(days=180)

    first_purchase_subq = None
    if tariff_code is not None:
        first_purchase_subq = (
            select(
                AnalyticsEvent.user_id.label("user_id"),
                AnalyticsEvent.tariff_code.label("tariff_code"),
            )
            .where(AnalyticsEvent.event_name == "first_purchase_completed")
            .subquery()
        )

    cohort_stmt = select(AnalyticsEvent.user_id, AnalyticsEvent.event_time).where(
        AnalyticsEvent.event_name == "cohort_month_started",
        AnalyticsEvent.event_time >= cohort_anchor_start,
        AnalyticsEvent.event_time < end_at,
        AnalyticsEvent.user_id.is_not(None),
    )
    if source_channel is not None:
        cohort_stmt = cohort_stmt.where(AnalyticsEvent.source_channel == source_channel)
    if first_purchase_subq is not None:
        cohort_stmt = (
            cohort_stmt.select_from(AnalyticsEvent)
            .join(first_purchase_subq, AnalyticsEvent.user_id == first_purchase_subq.c.user_id)
            .where(first_purchase_subq.c.tariff_code == tariff_code)
        )

    cohort_rows = (await db.execute(cohort_stmt)).all()

    # cohort_key -> {user_id: cohort_event_time}
    cohorts: dict[str, dict[int, datetime]] = {}
    for user_id, event_time in cohort_rows:
        if user_id is None or event_time is None:
            continue
        key = _month_key(event_time)
        cohorts.setdefault(key, {})[int(user_id)] = event_time

    if not cohorts:
        return []

    cohort_keys_sorted = sorted(cohorts.keys())
    # Match existing UX: show last 6 cohorts.
    cohort_keys_sorted = cohort_keys_sorted[-6:]
    relevant_user_ids = {uid for k in cohort_keys_sorted for uid in cohorts[k].keys()}

    # Fetch order_completed events for retention offsets up to M6.
    orders_stmt = select(
        AnalyticsEvent.user_id,
        AnalyticsEvent.event_time,
        AnalyticsEvent.tariff_code,
        AnalyticsEvent.source_channel,
    ).where(
        AnalyticsEvent.event_name == "order_completed",
        AnalyticsEvent.user_id.is_not(None),
        AnalyticsEvent.user_id.in_(list(relevant_user_ids)),
        AnalyticsEvent.event_time >= cohort_anchor_start,
        AnalyticsEvent.event_time < end_at + timedelta(days=220),
    )
    if source_channel is not None:
        orders_stmt = orders_stmt.where(AnalyticsEvent.source_channel == source_channel)
    if tariff_code is not None:
        orders_stmt = orders_stmt.where(AnalyticsEvent.tariff_code == tariff_code)

    order_rows = (await db.execute(orders_stmt)).all()

    orders_by_user: dict[int, list[AnalyticsEvent]] = {}
    for user_id, event_time, oc_tariff, oc_source in order_rows:
        orders_by_user.setdefault(int(user_id), []).append(
            AnalyticsEvent(
                event_name="order_completed",
                user_id=int(user_id),
                order_id=None,
                tariff_code=oc_tariff,
                source_channel=oc_source,
                utm_source=None,
                utm_medium=None,
                utm_campaign=None,
                geo=None,
                platform=None,
                amount=None,
                cost_components=None,
                event_metadata=None,
                correlation_id=None,
                dedupe_key=None,
                event_time=event_time,
            )
        )

    def active_ratio_percent(cohort_key: str, offset_months: int) -> float:
        cohort_users = cohorts[cohort_key]
        if not cohort_users:
            return 0.0
        cohort_month_index = _month_index(min(cohort_users.values()))
        active_users: set[int] = set()
        for uid in cohort_users.keys():
            for ev in orders_by_user.get(uid, []):
                if _month_index(ev.event_time) - cohort_month_index == offset_months:
                    active_users.add(uid)
                    break
        return round((len(active_users) / len(cohort_users)) * 100, 1) if cohort_users else 0.0

    rows_out: list[CohortRow] = []
    for cohort_key in cohort_keys_sorted:
        users_map = cohorts[cohort_key]
        size = len(users_map)
        rows_out.append(
            CohortRow(
                cohort=cohort_key,
                size=size,
                m1=active_ratio_percent(cohort_key, 1),
                m3=active_ratio_percent(cohort_key, 3),
                m6=active_ratio_percent(cohort_key, 6),
            )
        )
    return rows_out


def _attribution_segment_column(group_by: str):
    if group_by == "source":
        return func.lower(func.trim(func.coalesce(AnalyticsEvent.source_channel, literal("direct"))))
    camp = func.trim(func.coalesce(AnalyticsEvent.utm_campaign, literal("")))
    inner = func.nullif(camp, "")
    return func.lower(func.coalesce(inner, literal("(no campaign)")))


async def compute_campaign_performance(
    db: AsyncSession,
    start_at: datetime,
    end_at: datetime,
    *,
    group_by: str = "campaign",
    billing_segment: str | None = None,
) -> tuple[list[dict], str]:
    """
    Агрегаты по analytics_events: signup_completed, first_purchase_completed (выручка = sum amount),
    order_completed (число уникальных order_id).
    billing_segment one_time|subscription — только события с order_id и тарифом заказа.
    """
    seg = _attribution_segment_column(group_by)
    methodology = (
        "События в analytics_events за период; сегмент last-touch: "
        + ("utm_campaign (пусто → «(no campaign)»)" if group_by == "campaign" else "source_channel")
        + ". CR1 = first_paid_users / signups по сегменту."
    )
    if billing_segment == "one_time":
        methodology += (
            " first_purchase_completed и order_completed учитываются только для заказов "
            "с tariffs.billing_type = one_time. signups — все signup_completed (без фильтра по тарифу)."
        )
    elif billing_segment == "subscription":
        methodology += (
            " first_purchase_completed и order_completed — только subscription-тарифы заказа. "
            "signups — все signup_completed."
        )

    merged: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {"signups": 0, "first_paid_users": 0, "first_paid_revenue_rub": 0.0, "orders_completed": 0}
    )

    signup_stmt = (
        select(seg.label("sk"), func.count(func.distinct(AnalyticsEvent.user_id)))
        .where(
            AnalyticsEvent.event_name == "signup_completed",
            AnalyticsEvent.event_time >= start_at,
            AnalyticsEvent.event_time < end_at,
            AnalyticsEvent.user_id.is_not(None),
        )
        .group_by(seg)
    )
    for sk, cnt in (await db.execute(signup_stmt)).all():
        merged[str(sk)]["signups"] = int(cnt or 0)

    fp_stmt = (
        select(
            seg.label("sk"),
            func.count(func.distinct(AnalyticsEvent.user_id)).label("users"),
            func.coalesce(func.sum(AnalyticsEvent.amount), 0).label("rev"),
        )
        .where(
            AnalyticsEvent.event_name == "first_purchase_completed",
            AnalyticsEvent.event_time >= start_at,
            AnalyticsEvent.event_time < end_at,
            AnalyticsEvent.user_id.is_not(None),
        )
    )
    if billing_segment in ("one_time", "subscription"):
        fp_stmt = (
            fp_stmt.join(Order, Order.id == AnalyticsEvent.order_id)
            .join(Tariff, Tariff.id == Order.tariff_id)
            .where(Tariff.billing_type == billing_segment)
        )
    fp_stmt = fp_stmt.group_by(seg)
    for sk, users, rev in (await db.execute(fp_stmt)).all():
        key = str(sk)
        merged[key]["first_paid_users"] = int(users or 0)
        merged[key]["first_paid_revenue_rub"] = float(rev or 0)

    oc_stmt = (
        select(seg.label("sk"), func.count(func.distinct(AnalyticsEvent.order_id)).label("oc"))
        .where(
            AnalyticsEvent.event_name == "order_completed",
            AnalyticsEvent.event_time >= start_at,
            AnalyticsEvent.event_time < end_at,
            AnalyticsEvent.order_id.is_not(None),
        )
    )
    if billing_segment in ("one_time", "subscription"):
        oc_stmt = (
            oc_stmt.join(Order, Order.id == AnalyticsEvent.order_id)
            .join(Tariff, Tariff.id == Order.tariff_id)
            .where(Tariff.billing_type == billing_segment)
        )
    oc_stmt = oc_stmt.group_by(seg)
    for sk, oc in (await db.execute(oc_stmt)).all():
        merged[str(sk)]["orders_completed"] = int(oc or 0)

    rows: list[dict] = []
    for sk, m in sorted(merged.items(), key=lambda kv: kv[1]["first_paid_revenue_rub"], reverse=True):
        su = int(m["signups"])
        fp = int(m["first_paid_users"])
        cr1 = (fp / su) if su else 0.0
        rows.append(
            {
                "segment_key": sk,
                "signups": su,
                "first_paid_users": fp,
                "first_paid_revenue_rub": float(m["first_paid_revenue_rub"]),
                "orders_completed": int(m["orders_completed"]),
                "cr1": round(cr1, 4),
            }
        )
    return rows, methodology

