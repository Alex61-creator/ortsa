from datetime import datetime, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.analytics_event import AnalyticsEvent
from app.models.user import OAuthProvider, User


async def _create_admin_headers(db_session, *, email: str = "adm-overview@example.com") -> dict[str, str]:
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
async def test_admin_metrics_overview_event_based_retention_m1_is_ratio(
    client: AsyncClient,
    db_session,
):
    headers = await _create_admin_headers(db_session)

    start_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end_at = datetime(2026, 2, 1, tzinfo=timezone.utc)

    u1 = User(
        email="u1-overview@example.com",
        external_id="u1-overview",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
    )
    u2 = User(
        email="u2-overview@example.com",
        external_id="u2-overview",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
    )
    db_session.add_all([u1, u2])
    await db_session.commit()
    await db_session.refresh(u1)
    await db_session.refresh(u2)

    events = [
        # Signups within the overview window.
        AnalyticsEvent(
            event_name="signup_completed",
            user_id=u1.id,
            event_time=datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc),
            dedupe_key="su:u1:jan",
            source_channel="tg_ads",
            cost_components=None,
            event_metadata=None,
        ),
        AnalyticsEvent(
            event_name="signup_completed",
            user_id=u2.id,
            event_time=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
            dedupe_key="su:u2:jan",
            source_channel="tg_ads",
            cost_components=None,
            event_metadata=None,
        ),
        # First paid (used for tariff segmentation).
        AnalyticsEvent(
            event_name="first_purchase_completed",
            user_id=u1.id,
            event_time=datetime(2026, 1, 11, 12, 0, tzinfo=timezone.utc),
            dedupe_key="fp:u1",
            tariff_code="bundle",
            source_channel="tg_ads",
            amount=Decimal("100.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
        ),
        AnalyticsEvent(
            event_name="first_purchase_completed",
            user_id=u2.id,
            event_time=datetime(2026, 1, 12, 12, 0, tzinfo=timezone.utc),
            dedupe_key="fp:u2",
            tariff_code="bundle",
            source_channel="tg_ads",
            amount=Decimal("200.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
        ),
        # Cohort anchors in January.
        AnalyticsEvent(
            event_name="cohort_month_started",
            user_id=u1.id,
            event_time=datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc),
            dedupe_key="cohort:u1:jan",
            source_channel="tg_ads",
            tariff_code=None,
            amount=None,
            currency=None,
            cost_components=None,
            event_metadata=None,
        ),
        AnalyticsEvent(
            event_name="cohort_month_started",
            user_id=u2.id,
            event_time=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
            dedupe_key="cohort:u2:jan",
            source_channel="tg_ads",
            tariff_code=None,
            amount=None,
            currency=None,
            cost_components=None,
            event_metadata=None,
        ),
        # Orders within overview window (January): revenue, variable costs, paid orders, eligible base orders.
        AnalyticsEvent(
            event_name="order_completed",
            user_id=u1.id,
            order_id=1001,
            event_time=datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc),
            dedupe_key="oc:u1:jan",
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
            user_id=u2.id,
            order_id=1002,
            event_time=datetime(2026, 1, 21, 12, 0, tzinfo=timezone.utc),
            dedupe_key="oc:u2:jan",
            tariff_code="bundle",
            source_channel="tg_ads",
            amount=Decimal("200.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
        ),
        # Retention offsets for M1/M3/M6: only u1 becomes active.
        AnalyticsEvent(
            event_name="order_completed",
            user_id=u1.id,
            order_id=2001,
            event_time=datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc),
            dedupe_key="oc:u1:m1",
            tariff_code="bundle",
            source_channel="tg_ads",
            amount=Decimal("100.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
        ),
        AnalyticsEvent(
            event_name="order_completed",
            user_id=u1.id,
            order_id=2002,
            event_time=datetime(2026, 4, 20, 12, 0, tzinfo=timezone.utc),
            dedupe_key="oc:u1:m3",
            tariff_code="bundle",
            source_channel="tg_ads",
            amount=Decimal("100.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
        ),
        AnalyticsEvent(
            event_name="order_completed",
            user_id=u1.id,
            order_id=2003,
            event_time=datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc),
            dedupe_key="oc:u1:m6",
            tariff_code="bundle",
            source_channel="tg_ads",
            amount=Decimal("100.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
        ),
        # Acquisition spend (used for blended CAC).
        AnalyticsEvent(
            event_name="acquisition_cost_recorded",
            user_id=None,
            order_id=None,
            event_time=datetime(2026, 1, 25, 12, 0, tzinfo=timezone.utc),
            dedupe_key="spend:jan",
            source_channel="tg_ads",
            tariff_code=None,
            amount=Decimal("300.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
        ),
        # Refund (used for contribution margin).
        AnalyticsEvent(
            event_name="refund_completed",
            user_id=u1.id,
            order_id=None,
            event_time=datetime(2026, 1, 28, 12, 0, tzinfo=timezone.utc),
            dedupe_key="refund:u1:jan",
            tariff_code="bundle",
            source_channel="tg_ads",
            amount=Decimal("50.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
        ),
        # Addon attached for attach-rate (synastry_addon).
        AnalyticsEvent(
            event_name="addon_attached",
            user_id=u1.id,
            order_id=3001,
            event_time=datetime(2026, 1, 26, 12, 0, tzinfo=timezone.utc),
            dedupe_key="addon:u1:jan",
            tariff_code="synastry_addon",
            source_channel="tg_ads",
            amount=Decimal("20.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
        ),
    ]

    db_session.add_all(events)
    await db_session.commit()

    resp = await client.get(
        "/api/v1/admin/metrics/overview",
        headers=headers,
        params={
            "period": "custom",
            "date_from": start_at.isoformat(),
            "date_to": end_at.isoformat(),
            "tariff_code": "bundle",
            "source_channel": "tg_ads",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    cards = {c["key"]: c for c in payload["cards"]}

    # retention is returned as ratio (0..1), so UI multiplies by 100.
    assert cards["retention_m1"]["unit"] == "ratio"
    assert cards["retention_m1"]["value"] == 0.5

    # sanity check: CR1 = first_paid_users / signups = 2/2 = 1.0
    assert cards["cr1"]["value"] == 1.0

