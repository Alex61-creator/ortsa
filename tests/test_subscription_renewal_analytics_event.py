"""subscription_renewal_payment при продлении без order (YooKassa webhook)."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.analytics_event import AnalyticsEvent
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.tariff import Tariff
from app.models.user import OAuthProvider, User
from app.services.payment import YookassaPaymentService
from tests.conftest import TestingSessionLocal


@pytest.mark.asyncio
async def test_subscription_only_webhook_emits_subscription_renewal_payment(db_session):
    user = User(
        email="renew-user@example.com",
        external_id="renew_u1",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
        utm_source="src",
        utm_medium="med",
        utm_campaign="camp",
        source_channel="organic",
        signup_platform="web",
        signup_geo="RU",
    )
    db_session.add(user)
    await db_session.flush()
    tariff = Tariff(
        code="sub_renew_tariff",
        name="Pro Sub",
        price=Decimal("490.00"),
        price_usd=Decimal("5.00"),
        features={"max_natal_profiles": 5},
        retention_days=180,
        billing_type="subscription",
        subscription_interval="month",
        llm_tier="pro",
    )
    db_session.add(tariff)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(tariff)

    now = datetime.now(timezone.utc)
    sub = Subscription(
        user_id=user.id,
        tariff_id=tariff.id,
        status=SubscriptionStatus.ACTIVE.value,
        current_period_end=now + timedelta(days=5),
        cancel_at_period_end=False,
    )
    db_session.add(sub)
    await db_session.commit()
    await db_session.refresh(sub)

    service = YookassaPaymentService()
    payment_id = "pay_renewal_test_1"
    payment_obj = {"amount": {"value": "123.45", "currency": "RUB"}}

    async with TestingSessionLocal() as db:
        await service._handle_subscription_only_webhook(
            db,
            "payment.succeeded",
            sub.id,
            payment_obj,
            payment_id,
        )

        row = (
            await db.execute(
                select(AnalyticsEvent).where(
                    AnalyticsEvent.event_name == "subscription_renewal_payment",
                    AnalyticsEvent.user_id == user.id,
                )
            )
        ).scalar_one()
        assert row.amount == Decimal("123.45")
        assert row.order_id is None
        assert row.dedupe_key == f"subscription_renewal_payment:{payment_id}"
        assert row.correlation_id == payment_id
        assert row.tariff_code == tariff.code

        await service._handle_subscription_only_webhook(
            db,
            "payment.succeeded",
            sub.id,
            payment_obj,
            payment_id,
        )
        rows = (
            await db.execute(
                select(AnalyticsEvent).where(
                    AnalyticsEvent.dedupe_key == f"subscription_renewal_payment:{payment_id}"
                )
            )
        ).scalars().all()
        assert len(rows) == 1


@pytest.mark.asyncio
async def test_subscription_only_webhook_skips_analytics_for_non_succeeded(db_session):
    user = User(
        email="renew-skip@example.com",
        external_id="renew_skip",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
    )
    db_session.add(user)
    await db_session.flush()
    tariff = Tariff(
        code="sub_skip_tariff",
        name="Pro Sub",
        price=Decimal("100.00"),
        price_usd=Decimal("1.00"),
        features={"max_natal_profiles": 1},
        retention_days=30,
        billing_type="subscription",
        subscription_interval="month",
        llm_tier="pro",
    )
    db_session.add(tariff)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(tariff)

    now = datetime.now(timezone.utc)
    sub = Subscription(
        user_id=user.id,
        tariff_id=tariff.id,
        status=SubscriptionStatus.ACTIVE.value,
        current_period_end=now + timedelta(days=5),
        cancel_at_period_end=False,
    )
    db_session.add(sub)
    await db_session.commit()
    await db_session.refresh(sub)

    service = YookassaPaymentService()
    async with TestingSessionLocal() as db:
        await service._handle_subscription_only_webhook(
            db,
            "payment.canceled",
            sub.id,
            {"amount": {"value": "10.00", "currency": "RUB"}},
            "pay_canceled_1",
        )

        rows = (
            await db.execute(
                select(AnalyticsEvent).where(AnalyticsEvent.event_name == "subscription_renewal_payment")
            )
        ).scalars().all()
        assert len(rows) == 0
