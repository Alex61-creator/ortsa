from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select

import app.services.refund as refund_module
from app.models.analytics_event import AnalyticsEvent
from app.models.order import Order, OrderStatus
from app.models.tariff import Tariff
from app.models.user import OAuthProvider, User
from app.services.refund import RefundService


@pytest.mark.asyncio
async def test_refund_completed_emitted_and_deduped(db_session, monkeypatch):
    user = User(
        email="user-refunds@example.com",
        external_id="u_refund_1",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
        utm_source="google",
        utm_medium="cpc",
        utm_campaign="summer",
        source_channel="google_ads",
        signup_platform="web",
        signup_geo="RU",
    )
    db_session.add(user)

    tariff = Tariff(
        code="report",
        name="Отчёт",
        price=Decimal("100.00"),
        price_usd=Decimal("1.05"),
        features={"max_natal_profiles": 1},
        retention_days=30,
        llm_tier="natal_full",
    )
    db_session.add(tariff)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(tariff)

    order = Order(
        user_id=user.id,
        tariff_id=tariff.id,
        status=OrderStatus.PAID,
        yookassa_id="payment_1",
        amount=Decimal("10.00"),
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    refund_service = RefundService()

    fake_refund = MagicMock()
    fake_refund.id = "refund_1"
    fake_refund.status = "succeeded"

    def fake_create(refund_data, idempotency_key):
        return fake_refund

    monkeypatch.setattr(refund_module.Refund, "create", fake_create)

    # create_refund should emit refund_completed.
    created = await refund_service.create_refund(db_session, order.id, amount=Decimal("2.50"))
    assert created["refund_id"] == "refund_1"

    rows = (
        await db_session.execute(
            select(AnalyticsEvent).where(
                AnalyticsEvent.event_name == "refund_completed",
                AnalyticsEvent.dedupe_key == "refund_completed:refund_1",
            )
        )
    ).scalars().all()
    assert len(rows) == 1

    # process_refund_webhook should not duplicate due to dedupe_key.
    await refund_service.process_refund_webhook(
        {
            "event": "refund.succeeded",
            "object": {
                "id": "refund_1",
                "payment_id": "payment_1",
                "status": "succeeded",
                "amount": {"value": "2.50", "currency": "RUB"},
            },
        },
        db_session,
    )

    rows2 = (
        await db_session.execute(
            select(AnalyticsEvent).where(
                AnalyticsEvent.event_name == "refund_completed",
                AnalyticsEvent.dedupe_key == "refund_completed:refund_1",
            )
        )
    ).scalars().all()
    assert len(rows2) == 1

