"""Ежегодный отчёт по прогрессиям для подписчиков Pro.

Отправляется один раз в год на дату годовщины подписки (день создания).
Celery beat запускает dispatch-задачу ежедневно в 10:00 UTC.

Идемпотентность: таблица annual_progression_logs (UNIQUE sub_id + year).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import structlog
from celery import shared_task
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.constants.tariffs import LlmTier
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.annual_progression_log import AnnualProgressionLog
from app.models.natal_data import NatalData
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.tariff import Tariff
from app.services.astrology import AstrologyService
from app.services.email import EmailService
from app.services.llm import LLMService
from app.services.pdf import PDFGenerator
from app.services.progression import ProgressionService
from app.utils.email_policy import is_placeholder_account_email

logger = structlog.get_logger(__name__)

PRO_TIER_VALUE = LlmTier.PRO.value


@shared_task(bind=True, autoretry_for=(Exception,), max_retries=2, default_retry_delay=300)
def dispatch_annual_progressions(self):
    """Ежедневная dispatch-задача в 10:00 UTC."""
    return asyncio.run(_dispatch_async())


@shared_task(bind=True, autoretry_for=(Exception,), max_retries=2, default_retry_delay=300)
def send_annual_progressions_task(self, subscription_id: int):
    """Задача генерации и отправки отчёта по прогрессиям."""
    return asyncio.run(_send_progressions_async(subscription_id))


# ── Helpers ──────────────────────────────────────────────────────────────────

def _is_anniversary_today(sub: Subscription, today_dt: datetime) -> bool:
    """Проверяет, является ли сегодня годовщиной подписки."""
    if not sub.created_at:
        return False
    import calendar
    created = sub.created_at
    target_day = created.day
    _, last_day = calendar.monthrange(today_dt.year, today_dt.month)
    effective_day = min(target_day, last_day)
    return today_dt.day == effective_day and today_dt.month == created.month


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


async def _dispatch_async() -> None:
    today = datetime.now(timezone.utc)
    current_year = today.year

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
        if not _is_anniversary_today(sub, today):
            continue

        async with AsyncSessionLocal() as db:
            exists = await db.execute(
                select(AnnualProgressionLog.id).where(
                    AnnualProgressionLog.subscription_id == sub.id,
                    AnnualProgressionLog.year == current_year,
                )
            )
            if exists.scalar_one_or_none() is not None:
                continue

        send_annual_progressions_task.delay(sub.id)
        dispatched += 1

    logger.info("annual_progressions_dispatched", today=str(today.date()), count=dispatched)


async def _send_progressions_async(subscription_id: int) -> None:
    today = datetime.now(timezone.utc)
    current_year = today.year

    async with AsyncSessionLocal() as db:
        sub = await db.get(Subscription, subscription_id, options=[
            joinedload(Subscription.user),
            joinedload(Subscription.tariff),
        ])
        if not sub or not sub.user:
            return

        email = (sub.user.email or "").strip()
        if not email or is_placeholder_account_email(email):
            logger.warning("annual_progressions skipped: no email", subscription_id=subscription_id)
            return

        # Идемпотентность
        exists = await db.execute(
            select(AnnualProgressionLog.id).where(
                AnnualProgressionLog.subscription_id == subscription_id,
                AnnualProgressionLog.year == current_year,
            )
        )
        if exists.scalar_one_or_none() is not None:
            logger.info("annual_progressions already sent", subscription_id=subscription_id)
            return

        natal_result = await db.execute(
            select(NatalData)
            .where(NatalData.user_id == sub.user_id)
            .order_by(NatalData.created_at.asc())
            .limit(1)
        )
        natal = natal_result.scalar_one_or_none()
        if not natal:
            logger.warning("annual_progressions skipped: no natal data", subscription_id=subscription_id)
            return

        locale = natal.report_locale if natal.report_locale in ("ru", "en") else "ru"

    natal_dict = _build_natal_dict(natal)

    # Расчёт карты
    astro = AstrologyService()
    from app.core.cache import cache
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

    # Расчёт прогрессий
    prog_svc = ProgressionService()
    prog_result = await prog_svc.calculate(natal_dict, target_year=current_year)
    quarterly = await prog_svc.calculate_quarterly(natal_dict, prog_result.target_year)
    prog_context = prog_result.to_llm_context()
    prog_context["quarters"] = {k: v.to_llm_context() for k, v in quarterly.items()}

    # LLM-отчёт
    llm = LLMService()
    report = await llm.generate_annual_progressions(
        chart_data, prog_context, locale=locale,
        cache_key_extra=f"{subscription_id}:{current_year}",
    )

    # PDF
    pdf_gen = PDFGenerator()
    pdf_filename = f"progressions_{subscription_id}_{current_year}.pdf"
    try:
        pdf_path = await pdf_gen.generate(
            template_name="annual_progressions.html",
            context={
                "user_name": natal.full_name,
                "year": current_year,
                "prog_result": prog_result,
                "quarterly": quarterly,
                "report": report,
                "locale": locale,
            },
            output_filename=pdf_filename,
        )
    except Exception as exc:
        logger.exception("annual_progressions PDF failed", subscription_id=subscription_id, error=str(exc))
        pdf_path = None

    # Email
    email_svc = EmailService()
    subject = (
        f"Ваш ежегодный отчёт по прогрессиям {current_year} готов"
        if locale == "ru"
        else f"Your annual progressions report for {current_year} is ready"
    )
    try:
        await email_svc.send_email(
            recipients=[email],
            subject=subject,
            body="",
            template_name="annual_progressions_ready.html",
            template_body={
                "user_name": natal.full_name,
                "year": current_year,
                "report_text": report.raw_content,
                "progressed_moon": prog_result.progressed_moon_sign,
                "top_aspects": [a.label_ru for a in prog_result.aspects_to_natal[:5]],
                "cabinet_link": f"{settings.public_app_base_url}/dashboard",
                "locale": locale,
            },
        )
    except Exception as exc:
        logger.exception("annual_progressions email failed", subscription_id=subscription_id, error=str(exc))
        return

    # Лог
    async with AsyncSessionLocal() as db:
        db.add(AnnualProgressionLog(
            subscription_id=subscription_id,
            year=current_year,
            pdf_path=str(pdf_path) if pdf_path else None,
        ))
        await db.commit()

    logger.info("annual_progressions sent", subscription_id=subscription_id, year=current_year)
