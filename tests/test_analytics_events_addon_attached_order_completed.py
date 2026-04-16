from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.analytics_event import AnalyticsEvent
from app.models.order import Order, OrderStatus
from app.models.tariff import Tariff
from app.models.user import OAuthProvider, User
from app.services.payment import YookassaPaymentService
from tests.conftest import TestingSessionLocal


@pytest.mark.asyncio
async def test_addon_attached_and_order_completed_emitted_for_synastry_addon(
    db_session,
):
    user = User(
        email="user-addons@example.com",
        external_id="u_addon_1",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
        utm_source="google",
        utm_medium="cpc",
        utm_campaign="spring",
        source_channel="google_ads",
        signup_platform="web",
        signup_geo="RU",
    )
    db_session.add(user)

    tariff = Tariff(
        code="synastry_addon",
        name="Synastry Addon",
        price=Decimal("2.00"),
        price_usd=Decimal("1.00"),
        features={"max_natal_profiles": 1},
        retention_days=30,
        billing_type="one_time",
        llm_tier="natal_full",
        priority=0,
    )
    db_session.add(tariff)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(tariff)

    order = Order(
        user_id=user.id,
        tariff_id=tariff.id,
        status=OrderStatus.PENDING,
        yookassa_id=None,
        amount=Decimal("2.00"),
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    payment_id = "pay_1"
    payment_event = {
        "event": "payment.succeeded",
        "object": {
            "id": payment_id,
            "status": "succeeded",
            "paid": True,
            "amount": {"value": "2.00", "currency": "RUB"},
            "metadata": {"order_id": str(order.id)},
            "created_at": "2018-07-10T14:27:54.691Z",
            "description": "test",
            "payment_method": {"type": "bank_card", "id": "pm_x"},
            "refundable": False,
            "test": True,
        },
    }

    service = YookassaPaymentService()
    async with TestingSessionLocal() as db:
        await service.process_webhook_event(payment_event, db)

        # addon_attached
        addon_rows = (
            await db.execute(
                select(AnalyticsEvent).where(
                    AnalyticsEvent.event_name == "addon_attached", AnalyticsEvent.order_id == order.id
                )
            )
        ).scalars().all()
        assert len(addon_rows) == 1
        assert addon_rows[0].dedupe_key == f"addon_attached:{order.id}"
        assert addon_rows[0].correlation_id == payment_id

        # order_completed
        completed_rows = (
            await db.execute(
                select(AnalyticsEvent).where(
                    AnalyticsEvent.event_name == "order_completed", AnalyticsEvent.order_id == order.id
                )
            )
        ).scalars().all()
        assert len(completed_rows) == 1
        assert completed_rows[0].dedupe_key == f"order_completed:{order.id}"

