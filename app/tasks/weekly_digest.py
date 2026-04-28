"""Еженедельный дайджест транзитов для подписчиков Pro.

Каждый понедельник в 9:00 UTC отправляет HTML-письмо с транзитами
на предстоящие 7 дней всем активным pro-подписчикам.

Идемпотентность: таблица weekly_digest_logs (UNIQUE sub_id + week_start).
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone

import structlog
from celery import shared_task
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.constants.tariffs import LlmTier
from app.core.cache import cache
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.natal_data import NatalData
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.tariff import Tariff
from app.models.weekly_digest_log import WeeklyDigestLog
from app.services.astrology import AstrologyService
from app.services.email import EmailService
from app.services.llm import LLMService
from app.services.transit import TransitService
from app.utils.calendar_context import events_to_weekly_context
from app.utils.email_policy import is_placeholder_account_email

logger = structlog.get_logger(__name__)

PRO_TIER_VALUE = LlmTier.PRO.value


@shared_task(bind=True, autoretry_for=(Exception,), max_retries=2, default_retry_delay=300)
def run_weekly_transit_digest(self):
    """Celery beat: каждый понедельник в 9:00 UTC."""
    return asyncio.run(_run_weekly_digest_async())


# ── Core ─────────────────────────────────────────────────────────────────────

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


def _transits_to_context(events: list, locale: str = "ru") -> str:
    if not events:
        return "Нет значимых транзитов." if locale == "ru" else "No significant transits."
    lines = []
    for ev in sorted(events, key=lambda e: e.orb)[:10]:
        label = ev.label_ru if locale == "ru" else ev.label_en
        lines.append(f"{ev.date.strftime('%d.%m')} — {label} ({ev.orb:.1f}°)")
    return "\n".join(lines)


async def _run_weekly_digest_async() -> None:
    today = datetime.now(timezone.utc).date()
    # Гарантируем, что week_start = понедельник
    week_start = today - timedelta(days=today.weekday())

    async with AsyncSessionLocal() as db:
        stmt = (
            select(Subscription)
            .join(Tariff, Subscription.tariff_id == Tariff.id)
            .where(
                Subscription.status == SubscriptionStatus.ACTIVE.value,
                Tariff.llm_tier == PRO_TIER_VALUE,
            )
            .options(joinedload(Subscription.user), joinedload(Subscription.tariff))
        )
        result = await db.execute(stmt)
        subs = result.unique().scalars().all()

    astro = AstrologyService()
    transit_svc = TransitService()
    llm = LLMService()
    email_svc = EmailService()
    sent = 0

    for sub in subs:
        if not sub.user:
            continue
        email = (sub.user.email or "").strip()
        if not email or is_placeholder_account_email(email):
            continue

        # Идемпотентность
        async with AsyncSessionLocal() as db:
            exists = await db.execute(
                select(WeeklyDigestLog.id).where(
                    WeeklyDigestLog.subscription_id == sub.id,
                    WeeklyDigestLog.week_start == week_start,
                )
            )
            if exists.scalar_one_or_none() is not None:
                continue

            natal_result = await db.execute(
                select(NatalData)
                .where(NatalData.user_id == sub.user_id)
                .order_by(NatalData.created_at.asc())
                .limit(1)
            )
            natal = natal_result.scalar_one_or_none()

        if not natal:
            continue

        locale = natal.report_locale if natal.report_locale in ("ru", "en") else "ru"
        natal_dict = _build_natal_dict(natal)

        try:
            events = await transit_svc.get_week_highlights(natal_dict, week_start)
            transit_context = _transits_to_context(events, locale)
            week_ctx = events_to_weekly_context(events, week_start, locale)

            digest_text = await llm.generate_weekly_digest(
                transit_context, locale=locale,
                cache_key_extra=f"{sub.id}:{week_start}",
            )

            week_label_ru = f"{week_start.strftime('%d.%m')} – {(week_start + timedelta(days=6)).strftime('%d.%m.%Y')}"
            subject = (
                f"Астрология на неделю: {week_label_ru}"
                if locale == "ru"
                else f"Your weekly astro digest: {week_start.strftime('%b %d')} – {(week_start + timedelta(days=6)).strftime('%b %d, %Y')}"
            )

            await email_svc.send_email(
                recipients=[email],
                subject=subject,
                body="",
                template_name="weekly_transit.html",
                template_body={
                    "user_name": natal.full_name,
                    "week_label": week_label_ru,
                    "digest_text": digest_text,
                    "week_ctx": week_ctx,
                    "cabinet_link": f"{settings.public_app_base_url}/dashboard",
                    "locale": locale,
                },
            )

        except Exception as exc:
            logger.exception(
                "weekly_digest failed",
                subscription_id=sub.id,
                error=str(exc),
            )
            continue

        async with AsyncSessionLocal() as db:
            db.add(WeeklyDigestLog(subscription_id=sub.id, week_start=week_start))
            await db.commit()

        sent += 1
        logger.info("weekly_digest sent", subscription_id=sub.id, week_start=str(week_start))

    logger.info("weekly_digest_complete", week_start=str(week_start), sent=sent)
