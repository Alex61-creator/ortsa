from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user
from app.db.session import get_db
from app.models.analytics_event import AnalyticsEvent
from app.models.user import User
from app.schemas.admin_extra import FunnelStep, FunnelSummary

router = APIRouter()


def _period_bounds(period: str) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    if period == "wow":
        return now - timedelta(days=7), now
    if period == "qoq":
        return now - timedelta(days=90), now
    start_at = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    if now.month == 12:
        end_at = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end_at = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
    return start_at, end_at


@router.get("/summary", response_model=FunnelSummary, summary="Воронка: сводка [deprecated — использовать /api/v1/admin/metrics/funnel]", deprecated=True)
async def funnel_summary(
    period: str = Query("current_month"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    start_at, end_at = _period_bounds(period)

    landing = int(
        (await db.scalar(
            select(func.count(func.distinct(AnalyticsEvent.user_id))).where(
                AnalyticsEvent.event_name == "signup_completed",
                AnalyticsEvent.event_time >= start_at,
                AnalyticsEvent.event_time < end_at,
                AnalyticsEvent.user_id.is_not(None),
            )
        ))
        or 0
    )
    form = int(
        (await db.scalar(
            select(func.count(func.distinct(AnalyticsEvent.user_id))).where(
                AnalyticsEvent.event_name == "first_purchase_completed",
                AnalyticsEvent.event_time >= start_at,
                AnalyticsEvent.event_time < end_at,
                AnalyticsEvent.user_id.is_not(None),
            )
        ))
        or 0
    )
    # Multiple UI funnel steps map to the same canonical runtime events.
    tariff = form
    auth = form
    payment = int(
        (await db.scalar(
            select(func.count(func.distinct(AnalyticsEvent.user_id))).where(
                AnalyticsEvent.event_name == "payment_succeeded",
                AnalyticsEvent.event_time >= start_at,
                AnalyticsEvent.event_time < end_at,
                AnalyticsEvent.user_id.is_not(None),
            )
        ))
        or 0
    )
    completed = int(
        (await db.scalar(
            select(func.count(func.distinct(AnalyticsEvent.user_id))).where(
                AnalyticsEvent.event_name == "order_completed",
                AnalyticsEvent.event_time >= start_at,
                AnalyticsEvent.event_time < end_at,
                AnalyticsEvent.user_id.is_not(None),
            )
        ))
        or 0
    )

    def pct(value: int) -> float:
        return round((value / landing) * 100, 1) if landing else 0.0

    steps = [
        FunnelStep(key="landing", title="Лендинг", count=landing, conversion_pct=100.0 if landing else 0.0),
        FunnelStep(key="form", title="Форма", count=form, conversion_pct=pct(form)),
        FunnelStep(key="tariff", title="Тариф", count=tariff, conversion_pct=pct(tariff)),
        FunnelStep(key="auth", title="Авторизация", count=auth, conversion_pct=pct(auth)),
        FunnelStep(key="payment", title="Оплата", count=payment, conversion_pct=pct(payment)),
        FunnelStep(key="completed", title="Отчет доставлен", count=completed, conversion_pct=pct(completed)),
    ]
    drop_offs = [
        {"from_key": "landing", "to_key": "form", "lost": max(landing - form, 0)},
        {"from_key": "form", "to_key": "tariff", "lost": max(form - tariff, 0)},
        {"from_key": "auth", "to_key": "payment", "lost": max(auth - payment, 0)},
    ]
    recommendations = [
        "Оптимизировать первый экран тарифов и уменьшить когнитивную нагрузку.",
        "Проверить скорость шага авторизации и повторные клики на оплату.",
        "Для failed/processing заказов включить автоматический follow-up в support.",
    ]
    return FunnelSummary(period=period, steps=steps, drop_offs=drop_offs, recommendations=recommendations)
