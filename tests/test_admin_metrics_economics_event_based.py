from datetime import datetime, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.analytics_event import AnalyticsEvent
from app.models.order import Order, OrderStatus
from app.models.tariff import Tariff
from app.models.user import OAuthProvider, User


async def _create_admin_headers(db_session, *, email: str = "adm-economics@example.com") -> dict[str, str]:
    admin = User(
        email=email,
        external_id=email,
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
        is_admin=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    token = create_access_token({"sub": str(admin.id), "tv": admin.token_version})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_metrics_economics_event_based_filter_by_source_channel(
    client: AsyncClient,
    db_session,
):
    headers = await _create_admin_headers(db_session)

    start_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end_at = datetime(2026, 2, 1, tzinfo=timezone.utc)

    tg_user1 = User(
        email="u1-econ@example.com",
        external_id="u1-econ",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
    )
    tg_user2 = User(
        email="u2-econ@example.com",
        external_id="u2-econ",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
    )
    email_user = User(
        email="u3-econ@example.com",
        external_id="u3-econ",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
    )
    db_session.add_all([tg_user1, tg_user2, email_user])
    await db_session.commit()
    await db_session.refresh(tg_user1)
    await db_session.refresh(tg_user2)
    await db_session.refresh(email_user)

    bundle = Tariff(
        code="bundle",
        name="Bundle",
        price=Decimal("100.00"),
        price_usd=Decimal("1.00"),
        features={"max_natal_profiles": 2},
        retention_days=30,
        llm_tier="natal_full",
    )
    synastry_addon = Tariff(
        code="synastry_addon",
        name="Synastry Addon",
        price=Decimal("20.00"),
        price_usd=Decimal("0.20"),
        features={"max_natal_profiles": 1},
        retention_days=30,
        llm_tier="natal_full",
    )
    db_session.add_all([bundle, synastry_addon])
    await db_session.commit()
    await db_session.flush()

    order_tg_1 = Order(
        user_id=tg_user1.id,
        tariff_id=bundle.id,
        amount=Decimal("100.00"),
        status=OrderStatus.COMPLETED,
    )
    order_tg_2 = Order(
        user_id=tg_user2.id,
        tariff_id=bundle.id,
        amount=Decimal("200.00"),
        status=OrderStatus.COMPLETED,
    )
    order_email = Order(
        user_id=email_user.id,
        tariff_id=bundle.id,
        amount=Decimal("150.00"),
        status=OrderStatus.COMPLETED,
    )
    addon_order_tg = Order(
        user_id=tg_user1.id,
        tariff_id=synastry_addon.id,
        amount=Decimal("20.00"),
        status=OrderStatus.COMPLETED,
    )
    addon_order_email = Order(
        user_id=email_user.id,
        tariff_id=synastry_addon.id,
        amount=Decimal("20.00"),
        status=OrderStatus.COMPLETED,
    )

    db_session.add_all([order_tg_1, order_tg_2, order_email, addon_order_tg, addon_order_email])
    await db_session.commit()
    await db_session.refresh(order_tg_1)
    await db_session.refresh(order_tg_2)
    await db_session.refresh(order_email)
    await db_session.refresh(addon_order_tg)
    await db_session.refresh(addon_order_email)

    # Seed analytics events used by compute_growth_metrics + compute_channel_cac_rows.
    events = [
        # Signups (filtered by source_channel).
        AnalyticsEvent(
            event_name="signup_completed",
            user_id=tg_user1.id,
            event_time=datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc),
            dedupe_key="su:tg:u1",
            source_channel="tg_ads",
            cost_components=None,
            event_metadata=None,
        ),
        AnalyticsEvent(
            event_name="signup_completed",
            user_id=tg_user2.id,
            event_time=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
            dedupe_key="su:tg:u2",
            source_channel="tg_ads",
            cost_components=None,
            event_metadata=None,
        ),
        AnalyticsEvent(
            event_name="signup_completed",
            user_id=email_user.id,
            event_time=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
            dedupe_key="su:email:u3",
            source_channel="email_ads",
            cost_components=None,
            event_metadata=None,
        ),
        # First purchase (for tariff_code segmentation + channel CAC).
        AnalyticsEvent(
            event_name="first_purchase_completed",
            user_id=tg_user1.id,
            event_time=datetime(2026, 1, 11, 12, 0, tzinfo=timezone.utc),
            dedupe_key="fp:tg:u1",
            tariff_code="bundle",
            source_channel="tg_ads",
            amount=Decimal("100.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
        ),
        AnalyticsEvent(
            event_name="first_purchase_completed",
            user_id=tg_user2.id,
            event_time=datetime(2026, 1, 12, 12, 0, tzinfo=timezone.utc),
            dedupe_key="fp:tg:u2",
            tariff_code="bundle",
            source_channel="tg_ads",
            amount=Decimal("200.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
        ),
        AnalyticsEvent(
            event_name="first_purchase_completed",
            user_id=email_user.id,
            event_time=datetime(2026, 1, 16, 12, 0, tzinfo=timezone.utc),
            dedupe_key="fp:email:u3",
            tariff_code="bundle",
            source_channel="email_ads",
            amount=Decimal("150.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
        ),
        # Orders in the overview/economics window (revenue/eligible orders).
        AnalyticsEvent(
            event_name="order_completed",
            user_id=tg_user1.id,
            order_id=order_tg_1.id,
            event_time=datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc),
            dedupe_key="oc:tg:o1",
            tariff_code="bundle",
            source_channel="tg_ads",
            amount=Decimal("100.00"),
            currency="RUB",
            cost_components={
                "variable_cost_amount": 5.0,
                "payment_fee_amount": 5.0,
                "ai_cost_amount": 5.0,
                "infra_cost_amount": 5.0,
            },
            event_metadata=None,
        ),
        AnalyticsEvent(
            event_name="order_completed",
            user_id=tg_user2.id,
            order_id=order_tg_2.id,
            event_time=datetime(2026, 1, 21, 12, 0, tzinfo=timezone.utc),
            dedupe_key="oc:tg:o2",
            tariff_code="bundle",
            source_channel="tg_ads",
            amount=Decimal("200.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
        ),
        AnalyticsEvent(
            event_name="order_completed",
            user_id=email_user.id,
            order_id=order_email.id,
            event_time=datetime(2026, 1, 22, 12, 0, tzinfo=timezone.utc),
            dedupe_key="oc:email:o3",
            tariff_code="bundle",
            source_channel="email_ads",
            amount=Decimal("150.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
        ),
        # Refunds (contribution margin).
        AnalyticsEvent(
            event_name="refund_completed",
            user_id=tg_user1.id,
            order_id=order_tg_1.id,
            event_time=datetime(2026, 1, 28, 12, 0, tzinfo=timezone.utc),
            dedupe_key="refund:tg:u1",
            tariff_code="bundle",
            source_channel="tg_ads",
            amount=Decimal("50.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
        ),
        AnalyticsEvent(
            event_name="refund_completed",
            user_id=email_user.id,
            order_id=order_email.id,
            event_time=datetime(2026, 1, 29, 12, 0, tzinfo=timezone.utc),
            dedupe_key="refund:email:u3",
            tariff_code="bundle",
            source_channel="email_ads",
            amount=Decimal("30.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
        ),
        # Channel acquisition spend.
        AnalyticsEvent(
            event_name="acquisition_cost_recorded",
            user_id=None,
            order_id=None,
            event_time=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
            dedupe_key="spend:tg",
            tariff_code=None,
            source_channel="tg_ads",
            amount=Decimal("300.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
        ),
        AnalyticsEvent(
            event_name="acquisition_cost_recorded",
            user_id=None,
            order_id=None,
            event_time=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
            dedupe_key="spend:email",
            tariff_code=None,
            source_channel="email_ads",
            amount=Decimal("200.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
        ),
        # Addons (attach-rate numerator).
        AnalyticsEvent(
            event_name="addon_attached",
            user_id=tg_user1.id,
            order_id=addon_order_tg.id,
            event_time=datetime(2026, 1, 26, 12, 0, tzinfo=timezone.utc),
            dedupe_key="addon:tg",
            tariff_code="synastry_addon",
            source_channel="tg_ads",
            amount=Decimal("20.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
        ),
        AnalyticsEvent(
            event_name="addon_attached",
            user_id=email_user.id,
            order_id=addon_order_email.id,
            event_time=datetime(2026, 1, 27, 12, 0, tzinfo=timezone.utc),
            dedupe_key="addon:email",
            tariff_code="synastry_addon",
            source_channel="email_ads",
            amount=Decimal("20.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
        ),
    ]

    db_session.add_all(events)
    await db_session.commit()

    async def call_economics(source: str):
        resp = await client.get(
            "/api/v1/admin/metrics/economics",
            headers=headers,
            params={
                "period": "custom",
                "date_from": start_at.isoformat(),
                "date_to": end_at.isoformat(),
                "tariff_code": "bundle",
                "source_channel": source,
            },
        )
        assert resp.status_code == 200
        return resp.json()

    tg_payload = await call_economics("tg_ads")
    assert tg_payload["blended_cac"] == 150.0
    assert tg_payload["attach_rate"] == 0.5
    assert tg_payload["channel_cac"][0]["channel"] == "tg_ads"
    assert tg_payload["channel_cac"][0]["cac"] == 150.0

    email_payload = await call_economics("email_ads")
    assert email_payload["blended_cac"] == 200.0
    assert email_payload["attach_rate"] == 1.0
    assert email_payload["channel_cac"][0]["channel"] == "email_ads"
    assert email_payload["channel_cac"][0]["cac"] == 200.0

