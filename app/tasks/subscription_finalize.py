"""
Завершение подписки после окончания оплаченного периода, если пользователь отменил с конца периода.
"""
import asyncio
from datetime import datetime, timezone

import structlog
from celery import shared_task
from sqlalchemy import select, update

from app.db.session import AsyncSessionLocal
from app.models.subscription import Subscription, SubscriptionStatus

logger = structlog.get_logger(__name__)


@shared_task
def finalize_subscriptions_at_period_end():
    return asyncio.run(_finalize_subscriptions_at_period_end_async())


async def _finalize_subscriptions_at_period_end_async() -> dict:
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        stmt = (
            select(Subscription.id)
            .where(
                Subscription.status == SubscriptionStatus.ACTIVE.value,
                Subscription.cancel_at_period_end.is_(True),
                Subscription.current_period_end.isnot(None),
                Subscription.current_period_end < now,
            )
        )
        result = await db.execute(stmt)
        ids = [row[0] for row in result.all()]
        if not ids:
            await db.commit()
            return {"finalized": 0}

        upd = (
            update(Subscription)
            .where(Subscription.id.in_(ids))
            .values(
                status=SubscriptionStatus.CANCELED.value,
                yookassa_payment_method_id=None,
                updated_at=now,
            )
        )
        await db.execute(upd)
        await db.commit()
        logger.info("Subscriptions finalized at period end", count=len(ids), ids=ids)
        return {"finalized": len(ids)}
