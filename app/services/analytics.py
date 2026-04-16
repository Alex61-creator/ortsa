from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics_event import AnalyticsEvent
from app.models.order import Order, OrderStatus
from app.models.tariff import Tariff
from app.models.user import User


def derive_source_channel(utm_source: str | None, fallback: str | None = None) -> str:
    value = (utm_source or fallback or "").strip().lower()
    return value or "direct"


async def record_analytics_event(
    db: AsyncSession,
    *,
    event_name: str,
    user_id: int | None = None,
    order_id: int | None = None,
    tariff_code: str | None = None,
    source_channel: str | None = None,
    utm_source: str | None = None,
    utm_medium: str | None = None,
    utm_campaign: str | None = None,
    geo: str | None = None,
    platform: str | None = None,
    amount: Decimal | float | None = None,
    currency: str | None = "RUB",
    cost_components: dict | None = None,
    event_metadata: dict | None = None,
    correlation_id: str | None = None,
    dedupe_key: str | None = None,
    notes: str | None = None,
    event_time: datetime | None = None,
) -> AnalyticsEvent:
    if dedupe_key:
        existing = await db.execute(select(AnalyticsEvent).where(AnalyticsEvent.dedupe_key == dedupe_key))
        row = existing.scalar_one_or_none()
        if row:
            return row

    row = AnalyticsEvent(
        event_name=event_name,
        user_id=user_id,
        order_id=order_id,
        tariff_code=tariff_code,
        source_channel=source_channel,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
        geo=geo,
        platform=platform,
        amount=amount,
        currency=currency,
        cost_components=cost_components,
        event_metadata=event_metadata,
        correlation_id=correlation_id,
        dedupe_key=dedupe_key,
        notes=notes,
        event_time=event_time or datetime.now(timezone.utc),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def is_first_paid_order(db: AsyncSession, user_id: int, order_id: int) -> bool:
    result = await db.execute(
        select(func.count(Order.id)).where(
            Order.user_id == user_id,
            Order.id != order_id,
            Order.status.in_([OrderStatus.PAID, OrderStatus.COMPLETED, OrderStatus.REFUNDED]),
        )
    )
    return int(result.scalar() or 0) == 0


async def get_user_attribution(db: AsyncSession, user_id: int) -> tuple[str | None, str | None, str | None, str | None, str | None, str | None]:
    row = await db.execute(
        select(
            User.utm_source,
            User.utm_medium,
            User.utm_campaign,
            User.source_channel,
            User.signup_platform,
            User.signup_geo,
        ).where(User.id == user_id)
    )
    return row.one_or_none() or (None, None, None, None, None, None)


async def fetch_first_paid_users_by_period(
    db: AsyncSession,
    start_at: datetime,
    end_at: datetime,
    *,
    channel: str | None = None,
) -> int:
    base = (
        select(func.count(func.distinct(Order.user_id)))
        .select_from(Order)
        .join(User, User.id == Order.user_id)
        .where(Order.status.in_([OrderStatus.PAID, OrderStatus.COMPLETED, OrderStatus.REFUNDED]))
        .where(Order.created_at >= start_at, Order.created_at < end_at)
    )
    if channel:
        base = base.where(User.source_channel == channel)
    return int((await db.scalar(base)) or 0)


async def fetch_paid_orders_revenue(
    db: AsyncSession,
    start_at: datetime,
    end_at: datetime,
    *,
    channel: str | None = None,
) -> tuple[Decimal, int]:
    stmt = (
        select(func.coalesce(func.sum(Order.amount), Decimal("0.00")), func.count(Order.id))
        .select_from(Order)
        .join(User, User.id == Order.user_id)
        .where(Order.status.in_([OrderStatus.PAID, OrderStatus.COMPLETED, OrderStatus.REFUNDED]))
        .where(Order.created_at >= start_at, Order.created_at < end_at)
    )
    if channel:
        stmt = stmt.where(User.source_channel == channel)
    revenue, count = (await db.execute(stmt)).one()
    return Decimal(revenue or Decimal("0.00")), int(count or 0)


async def fetch_addon_counts(db: AsyncSession, start_at: datetime, end_at: datetime) -> tuple[int, int]:
    eligible_stmt = (
        select(func.count(Order.id))
        .select_from(Order)
        .join(Tariff, Tariff.id == Order.tariff_id)
        .where(Order.status.in_([OrderStatus.PAID, OrderStatus.COMPLETED, OrderStatus.REFUNDED]))
        .where(Order.created_at >= start_at, Order.created_at < end_at)
        .where(Tariff.code.in_(["bundle", "report", "sub_monthly", "sub_annual"]))
    )
    addon_stmt = (
        select(func.count(Order.id))
        .select_from(Order)
        .join(Tariff, Tariff.id == Order.tariff_id)
        .where(Order.status.in_([OrderStatus.PAID, OrderStatus.COMPLETED, OrderStatus.REFUNDED]))
        .where(Order.created_at >= start_at, Order.created_at < end_at)
        .where(Tariff.code == "synastry_addon")
    )
    eligible = int((await db.scalar(eligible_stmt)) or 0)
    addon = int((await db.scalar(addon_stmt)) or 0)
    return addon, eligible
