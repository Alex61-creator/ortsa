from datetime import datetime, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.analytics_event import AnalyticsEvent
from app.models.user import OAuthProvider, User


async def _create_admin_headers(db_session, *, email: str = "adm-metrics-cohorts@example.com") -> dict[str, str]:
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
async def test_metrics_cohorts_event_based_m1_m3_m6_current_period(
    client: AsyncClient,
    db_session,
):
    headers = await _create_admin_headers(db_session)

    # Keep deterministic boundaries: same as compute_retention_cohorts service test.
    start_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end_at = datetime(2026, 2, 1, tzinfo=timezone.utc)

    u1 = User(
        email="u1-cohort@example.com",
        external_id="u1-cohort",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
    )
    u2 = User(
        email="u2-cohort@example.com",
        external_id="u2-cohort",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
    )
    db_session.add_all([u1, u2])
    await db_session.commit()
    await db_session.refresh(u1)
    await db_session.refresh(u2)

    cohort_month_started_u1 = datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)
    cohort_month_started_u2 = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)

    # cohort_size = 2 (two users in 2026-01 cohort).
    # m1/m3/m6 should each be 50.0 because only u1 has an order_completed in each target month-offset.
    events = [
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
        AnalyticsEvent(
            event_name="cohort_month_started",
            user_id=u1.id,
            event_time=cohort_month_started_u1,
            dedupe_key="c:u1:2026-01",
            tariff_code=None,
            source_channel="tg_ads",
            amount=None,
            currency=None,
            cost_components=None,
            event_metadata=None,
        ),
        AnalyticsEvent(
            event_name="cohort_month_started",
            user_id=u2.id,
            event_time=cohort_month_started_u2,
            dedupe_key="c:u2:2026-01",
            tariff_code=None,
            source_channel="tg_ads",
            amount=None,
            currency=None,
            cost_components=None,
            event_metadata=None,
        ),
        AnalyticsEvent(
            event_name="order_completed",
            user_id=u1.id,
            order_id=None,
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
            order_id=None,
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
            order_id=None,
            event_time=datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc),
            dedupe_key="oc:u1:m6",
            tariff_code="bundle",
            source_channel="tg_ads",
            amount=Decimal("100.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
        ),
    ]
    db_session.add_all(events)
    await db_session.commit()

    resp = await client.get(
        "/api/v1/admin/metrics/cohorts",
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
    assert "rows" in payload

    rows = payload["rows"]
    assert len(rows) == 1
    row = rows[0]
    assert row["cohort"] == "2026-01"
    assert row["size"] == 2
    assert row["m1"] == 50.0
    assert row["m3"] == 50.0
    assert row["m6"] == 50.0

