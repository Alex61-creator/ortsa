"""Ежемесячный персональный прогноз для подписчиков (sub_monthly / sub_annual).

Логика отправки:
- Celery beat запускает dispatch-задачу ежедневно в 9:00 UTC.
- Для каждой активной pro-подписки проверяем: today.day == current_period_start.day
  (т.е. «годовщина» подписки в этом месяце).
- Для месяцев короче (28–30 дней) — last-day fallback.
- Идемпотентность: таблица monthly_forecast_logs (UNIQUE sub_id + period_yyyymm).
"""
from __future__ import annotations

import asyncio
import json
from datetime import date, datetime, timezone
from typing import Any

import structlog
from celery import shared_task
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.constants.tariffs import LlmTier
from app.core.cache import cache
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.monthly_forecast_log import MonthlyForecastLog
from app.models.natal_data import NatalData
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.tariff import Tariff
from app.services.astrology import AstrologyService
from app.services.email import EmailService
from app.services.ics_calendar import generate_ics
from app.services.llm import LLMService
from app.services.pdf import PDFGenerator
from app.services.transit import TransitService
from app.utils.email_policy import is_placeholder_account_email

logger = structlog.get_logger(__name__)

PRO_TIER_VALUE = LlmTier.PRO.value


@shared_task(bind=True, autoretry_for=(Exception,), max_retries=2, default_retry_delay=300)
def dispatch_monthly_forecasts(self):
    """Ежедневная dispatch-задача: определяет, кому сегодня отправить прогноз."""
    return asyncio.run(_dispatch_async())


@shared_task(bind=True, autoretry_for=(Exception,), max_retries=2, default_retry_delay=300)
def send_monthly_forecast_task(self, subscription_id: int):
    """Задача генерации и отправки прогноза для конкретной подписки."""
    return asyncio.run(_send_forecast_async(subscription_id))


# ── Helpers ─────────────────────────────────────────────────────────────────

def _should_send_today(sub: Subscription, today: date) -> bool:
    """
    Проверяет, нужно ли отправить прогноз сегодня.

    Отправляем, если today.day == sub.current_period_start.day,
    с fallback для коротких месяцев (28/30-дневных).
    """
    if not sub.current_period_start:
        return False
    import calendar
    target_day = sub.current_period_start.day
    _, last_day = calendar.monthrange(today.year, today.month)
    # Если день подписки > последнего дня текущего месяца — отправляем в последний день
    effective_day = min(target_day, last_day)
    return today.day == effective_day


async def _dispatch_async() -> None:
    today = datetime.now(timezone.utc).date()
    period = today.strftime("%Y-%m")

    async with AsyncSessionLocal() as db:
        stmt = (
            select(Subscription)
            .join(Tariff, Subscription.tariff_id == Tariff.id)
            .where(
                Subscription.status == SubscriptionStatus.ACTIVE.value,
                Tariff.llm_tier == PRO_TIER_VALUE,
            )
            .options(joinedload(Subscription.tariff))
        )
        result = await db.execute(stmt)
        subs = result.unique().scalars().all()

    dispatched = 0
    for sub in subs:
        if not _should_send_today(sub, today):
            continue
        # Проверяем идемпотентность до диспетча (быстрая проверка)
        async with AsyncSessionLocal() as db:
            exists = await db.execute(
                select(MonthlyForecastLog.id).where(
                    MonthlyForecastLog.subscription_id == sub.id,
                    MonthlyForecastLog.period_yyyymm == period,
                )
            )
            if exists.scalar_one_or_none() is not None:
                continue

        send_monthly_forecast_task.delay(sub.id)
        dispatched += 1

    logger.info("monthly_forecast_dispatched", today=str(today), count=dispatched)


def _build_natal_dict(natal: NatalData) -> dict:
    return {
        "name": natal.full_name,
        "birth_date": natal.birth_date,
        "birth_time": natal.birth_time,
        "lat": natal.lat,
        "lon": natal.lon,
        "tz_str": natal.timezone,
        "house_system": natal.house_system,
    }


def _transits_to_context(events: list[Any], locale: str = "ru") -> str:
    """Форматирует список TransitEvent в текст для LLM."""
    if not events:
        return "Нет значимых транзитов." if locale == "ru" else "No significant transits."
    lines = []
    for ev in events[:40]:  # Лимит контекста
        label = ev.label_ru if locale == "ru" else ev.label_en
        lines.append(f"{ev.date.strftime('%d.%m')} — {label} (орбис {ev.orb:.1f}°)")
    return "\n".join(lines)


async def _send_forecast_async(subscription_id: int) -> None:
    today = datetime.now(timezone.utc).date()
    period = today.strftime("%Y-%m")
    # Прогноз — на следующий месяц (отправляем заранее)
    import calendar
    year, month = today.year, today.month
    if month == 12:
        forecast_year, forecast_month = year + 1, 1
    else:
        forecast_year, forecast_month = year, month + 1

    async with AsyncSessionLocal() as db:
        sub = await db.get(Subscription, subscription_id, options=[
            joinedload(Subscription.user),
            joinedload(Subscription.tariff),
        ])
        if not sub or not sub.user:
            return

        email = (sub.user.email or "").strip()
        if not email or is_placeholder_account_email(email):
            logger.warning("monthly_forecast skipped: no email", subscription_id=subscription_id)
            return

        # Идемпотентность
        exists = await db.execute(
            select(MonthlyForecastLog.id).where(
                MonthlyForecastLog.subscription_id == subscription_id,
                MonthlyForecastLog.period_yyyymm == period,
            )
        )
        if exists.scalar_one_or_none() is not None:
            logger.info("monthly_forecast already sent", subscription_id=subscription_id)
            return

        # Получаем основной natal_data профиль
        natal_result = await db.execute(
            select(NatalData)
            .where(NatalData.user_id == sub.user_id)
            .order_by(NatalData.created_at.asc())
            .limit(1)
        )
        natal = natal_result.scalar_one_or_none()
        if not natal:
            logger.warning("monthly_forecast skipped: no natal data", subscription_id=subscription_id)
            return

        locale = natal.report_locale if natal.report_locale in ("ru", "en") else "ru"

    # Расчёт карты (из кэша или пересчёт)
    astro = AstrologyService()
    natal_dict = _build_natal_dict(natal)
    cache_key_chart = astro.make_cache_key(
        name=natal.full_name,
        birth_date=natal.birth_date,
        birth_time=natal.birth_time,
        lat=natal.lat,
        lon=natal.lon,
        tz_str=natal.timezone,
        house_system=natal.house_system,
    )
    chart_data = await cache.get(cache_key_chart)
    if not chart_data:
        chart_result = await astro.calculate_chart(
            name=natal.full_name,
            birth_date=natal.birth_date,
            birth_time=natal.birth_time,
            lat=natal.lat,
            lon=natal.lon,
            tz_str=natal.timezone,
            house_system=natal.house_system,
        )
        chart_data = chart_result["instance"]
        await cache.set(cache_key_chart, chart_data, ttl=30 * 24 * 3600)

    # Расчёт транзитов
    transit_svc = TransitService()
    events = await transit_svc.calculate_month_transits(natal_dict, forecast_year, forecast_month)
    transit_context = _transits_to_context(events, locale)

    # LLM-прогноз
    llm = LLMService()
    forecast = await llm.generate_monthly_forecast(
        chart_data, transit_context, locale=locale,
        cache_key_extra=f"{subscription_id}:{period}",
    )

    # ICS-файл
    ics_bytes = generate_ics(events, locale=locale,
                              calendar_name=f"Астрология {forecast_year}-{forecast_month:02d}")

    # PDF-прогноз
    from app.utils.calendar_context import build_calendar_context
    calendar_ctx = build_calendar_context(events, forecast_year, forecast_month, locale)

    pdf_gen = PDFGenerator()
    pdf_filename = f"forecast_{subscription_id}_{period}.pdf"
    try:
        pdf_path = await pdf_gen.generate(
            template_name="monthly_forecast.html",
            context={
                "user_name": natal.full_name,
                "period": f"{forecast_year}-{forecast_month:02d}",
                "forecast": forecast,
                "calendar": calendar_ctx,
                "locale": locale,
            },
            output_filename=pdf_filename,
        )
    except Exception as exc:
        logger.exception("monthly_forecast PDF failed", subscription_id=subscription_id, error=str(exc))
        pdf_path = None

    # Email
    email_svc = EmailService()
    month_name = calendar_ctx.month_name if calendar_ctx else f"{forecast_year}-{forecast_month:02d}"
    subject = (
        f"Ваш персональный прогноз на {month_name} готов"
        if locale == "ru"
        else f"Your personal forecast for {month_name} is ready"
    )
    try:
        attachments = [("forecast.ics", ics_bytes, "text/calendar")]
        await email_svc.send_email(
            recipients=[email],
            subject=subject,
            body="",
            template_name="monthly_forecast_ready.html",
            template_body={
                "user_name": natal.full_name,
                "month_name": month_name,
                "forecast_text": forecast.raw_content,
                "cabinet_link": f"{settings.public_app_base_url}/dashboard",
                "locale": locale,
            },
            attachments=attachments if hasattr(email_svc, '_supports_attachments') else None,
        )
    except Exception as exc:
        logger.exception("monthly_forecast email failed", subscription_id=subscription_id, error=str(exc))
        return

    # Запись в лог
    async with AsyncSessionLocal() as db:
        log = MonthlyForecastLog(
            subscription_id=subscription_id,
            period_yyyymm=period,
            pdf_path=str(pdf_path) if pdf_path else None,
        )
        db.add(log)
        await db.commit()

    logger.info("monthly_forecast sent", subscription_id=subscription_id, period=period)
