"""
Продление подписок Astro Pro: списание по сохранённому payment_method_id (ЮKassa).
"""
import asyncio
from datetime import datetime, timedelta, timezone

import structlog
from celery import shared_task
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.subscription import Subscription, SubscriptionStatus
from app.services.email import EmailService
from app.services.payment import YookassaPaymentService
from app.utils.email_policy import is_placeholder_account_email

logger = structlog.get_logger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), max_retries=2, default_retry_delay=120)
def renew_due_subscriptions(self):
    return asyncio.run(_renew_due_subscriptions_async())


async def _renew_due_subscriptions_async() -> None:
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=1)
    async with AsyncSessionLocal() as db:
        stmt = (
            select(Subscription)
            .where(
                Subscription.status == SubscriptionStatus.ACTIVE.value,
                Subscription.cancel_at_period_end.is_(False),
                Subscription.yookassa_payment_method_id.isnot(None),
                Subscription.current_period_end.isnot(None),
                Subscription.current_period_end <= horizon,
            )
            .options(joinedload(Subscription.tariff), joinedload(Subscription.user))
        )
        result = await db.execute(stmt)
        subs = result.unique().scalars().all()

        svc = YookassaPaymentService()
        for sub in subs:
            if not sub.tariff or sub.tariff.billing_type != "subscription":
                continue
            email = sub.user.email if sub.user else None
            if not email or is_placeholder_account_email(email):
                logger.warning(
                    "Subscription renewal skipped: no real email",
                    subscription_id=sub.id,
                )
                continue
            try:
                await svc.charge_subscription_renewal(
                    subscription_id=sub.id,
                    payment_method_id=sub.yookassa_payment_method_id,
                    amount=sub.tariff.price,
                    description=f"AstroGen Pro renewal — {sub.tariff.name}",
                    user_email=email,
                )
            except Exception as exc:
                logger.exception(
                    "Subscription renewal payment failed",
                    subscription_id=sub.id,
                    error=str(exc),
                )
                sub.status = SubscriptionStatus.PAST_DUE.value
                await db.commit()
                try:
                    email_svc = EmailService()
                    await email_svc.send_email(
                        recipients=[email],
                        subject="Astro Pro — не удалось продлить подписку",
                        body="",
                        template_name="subscription_past_due.html",
                        template_body={
                            "cabinet_link": f"{settings.public_app_base_url}/cabinet",
                        },
                    )
                except Exception:
                    logger.exception(
                        "Past due notification email failed",
                        subscription_id=sub.id,
                    )
