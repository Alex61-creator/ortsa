"""
Ежемесячный дайджест Astro Pro: транзиты и прогноз (тот же llm_tier=pro), без заказа.
"""
import asyncio
from datetime import datetime, timezone

import structlog
from celery import shared_task
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.constants.tariffs import LlmTier
from app.core.cache import cache
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.monthly_digest import MonthlyDigestLog
from app.models.natal_data import NatalData
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.tariff import Tariff
from app.services.astrology import AstrologyService
from app.services.email import EmailService
from app.services.llm import LLMService
from app.utils.email_policy import is_placeholder_account_email
from app.utils.tariff_features import max_natal_profiles_from_tariff

logger = structlog.get_logger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), max_retries=2, default_retry_delay=120)
def run_monthly_pro_digests(self):
    return asyncio.run(_run_monthly_pro_digests_async())


async def _run_monthly_pro_digests_async() -> None:
    period = datetime.now(timezone.utc).strftime("%Y-%m")
    async with AsyncSessionLocal() as db:
        stmt = (
            select(Subscription)
            .join(Tariff, Subscription.tariff_id == Tariff.id)
            .where(
                Subscription.status == SubscriptionStatus.ACTIVE.value,
                Tariff.llm_tier == LlmTier.PRO.value,
            )
            .options(joinedload(Subscription.user), joinedload(Subscription.tariff))
        )
        result = await db.execute(stmt)
        subs = result.unique().scalars().all()

        email_svc = EmailService()
        astro = AstrologyService()
        llm = LLMService()

        for sub in subs:
            if not sub.user:
                continue
            email = (sub.user.email or "").strip()
            if not email or is_placeholder_account_email(email):
                logger.warning("Monthly digest skipped: no real email", subscription_id=sub.id)
                continue

            exists = await db.execute(
                select(MonthlyDigestLog.id).where(
                    MonthlyDigestLog.subscription_id == sub.id,
                    MonthlyDigestLog.period_yyyymm == period,
                )
            )
            if exists.scalar_one_or_none() is not None:
                continue

            natal_stmt = (
                select(NatalData)
                .where(NatalData.user_id == sub.user_id)
                .order_by(NatalData.created_at.asc())
                .limit(max_natal_profiles_from_tariff(sub.tariff) if sub.tariff else 1)
            )
            natal_result = await db.execute(natal_stmt)
            natal_rows = natal_result.scalars().all()
            if not natal_rows:
                logger.info("Monthly digest skipped: no natal data", subscription_id=sub.id)
                log_row = MonthlyDigestLog(subscription_id=sub.id, period_yyyymm=period)
                db.add(log_row)
                await db.commit()
                continue

            # Одно письмо: первый профиль (основной) — чтобы уложиться в бюджет LLM.
            natal_data = natal_rows[0]
            report_locale = (
                natal_data.report_locale if natal_data.report_locale in ("ru", "en") else "ru"
            )

            cache_key = astro.make_cache_key(
                name=natal_data.full_name,
                birth_date=natal_data.birth_date,
                birth_time=natal_data.birth_time,
                lat=natal_data.lat,
                lon=natal_data.lon,
                tz_str=natal_data.timezone,
                house_system=natal_data.house_system,
            )
            chart_data = await cache.get(cache_key)
            if not chart_data:
                chart_result = await astro.calculate_chart(
                    name=natal_data.full_name,
                    birth_date=natal_data.birth_date,
                    birth_time=natal_data.birth_time,
                    lat=natal_data.lat,
                    lon=natal_data.lon,
                    tz_str=natal_data.timezone,
                    house_system=natal_data.house_system,
                )
                chart_data = chart_result["instance"]
                await cache.set(cache_key, chart_data, ttl=30 * 24 * 3600)

            interpretation = await llm.generate_interpretation(
                chart_data, sub.tariff, locale=report_locale
            )

            subj = (
                f"Astro Pro — прогноз на {period}"
                if report_locale == "ru"
                else f"Astro Pro — forecast for {period}"
            )
            period_start_display = None
            if sub.current_period_start:
                period_start_display = sub.current_period_start.strftime("%d.%m.%Y")
            try:
                await email_svc.send_email(
                    recipients=[email],
                    subject=subj,
                    body="",
                    template_name="monthly_digest.html",
                    template_body={
                        "user_name": natal_data.full_name,
                        "period": period,
                        "period_start_display": period_start_display,
                        "interpretation": interpretation.raw_content,
                        "cabinet_link": f"{settings.public_app_base_url}/dashboard",
                    },
                )
            except Exception as exc:
                logger.exception(
                    "Monthly digest email failed",
                    subscription_id=sub.id,
                    error=str(exc),
                )
                continue

            db.add(MonthlyDigestLog(subscription_id=sub.id, period_yyyymm=period))
            await db.commit()
            logger.info("Monthly digest sent", subscription_id=sub.id, period=period)
