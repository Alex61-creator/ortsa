from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.analytics_event import AnalyticsEvent
from app.models.user import OAuthProvider, User


async def _admin_headers(db_session, *, email: str = "adm-funnel-summary@example.com") -> dict[str, str]:
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
async def test_admin_funnel_summary_event_based_current_month(
    client: AsyncClient,
    db_session,
):
    headers = await _admin_headers(db_session)

    now = datetime.now(timezone.utc)
    start_at = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    if now.month == 12:
        end_at = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end_at = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)

    u1 = User(
        email="u1-funnel-summary@example.com",
        external_id="u1-funnel-summary",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
    )
    u2 = User(
        email="u2-funnel-summary@example.com",
        external_id="u2-funnel-summary",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
    )
    db_session.add_all([u1, u2])
    await db_session.commit()
    await db_session.refresh(u1)
    await db_session.refresh(u2)

    signup1 = start_at + timedelta(days=1)
    signup2 = start_at + timedelta(days=2)

    events = [
        AnalyticsEvent(
            event_name="signup_completed",
            user_id=u1.id,
            event_time=signup1,
            dedupe_key="fs:signup:u1",
            amount=None,
            currency=None,
            cost_components=None,
            event_metadata=None,
        ),
        AnalyticsEvent(
            event_name="signup_completed",
            user_id=u2.id,
            event_time=signup2,
            dedupe_key="fs:signup:u2",
            amount=None,
            currency=None,
            cost_components=None,
            event_metadata=None,
        ),
        AnalyticsEvent(
            event_name="first_purchase_completed",
            user_id=u1.id,
            event_time=signup1 + timedelta(days=5),
            dedupe_key="fs:fpc:u1",
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
            event_time=signup2 + timedelta(days=5),
            dedupe_key="fs:fpc:u2",
            tariff_code="bundle",
            source_channel="tg_ads",
            amount=Decimal("200.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
        ),
        AnalyticsEvent(
            event_name="payment_succeeded",
            user_id=u1.id,
            event_time=signup1 + timedelta(days=7),
            dedupe_key="fs:pay:u1",
            tariff_code="bundle",
            source_channel="tg_ads",
            amount=Decimal("100.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
        ),
        AnalyticsEvent(
            event_name="payment_succeeded",
            user_id=u2.id,
            event_time=signup2 + timedelta(days=7),
            dedupe_key="fs:pay:u2",
            tariff_code="bundle",
            source_channel="tg_ads",
            amount=Decimal("200.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
        ),
        AnalyticsEvent(
            event_name="order_completed",
            user_id=u1.id,
            event_time=signup1 + timedelta(days=9),
            dedupe_key="fs:oc:u1",
            tariff_code="bundle",
            source_channel="tg_ads",
            amount=Decimal("100.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
        ),
        AnalyticsEvent(
            event_name="order_completed",
            user_id=u2.id,
            event_time=signup2 + timedelta(days=9),
            dedupe_key="fs:oc:u2",
            tariff_code="bundle",
            source_channel="tg_ads",
            amount=Decimal("200.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
        ),
    ]

    db_session.add_all(events)
    await db_session.commit()

    resp = await client.get("/api/v1/admin/funnel/summary", headers=headers, params={"period": "current_month"})
    assert resp.status_code == 200
    payload = resp.json()
    assert "steps" in payload

    steps = {s["key"]: s for s in payload["steps"]}
    assert steps["landing"]["count"] == 2
    assert steps["form"]["count"] == 2
    assert steps["tariff"]["count"] == 2
    assert steps["auth"]["count"] == 2
    assert steps["payment"]["count"] == 2
    assert steps["completed"]["count"] == 2

    # All conversions should be 100% with fully matching events.
    assert steps["payment"]["conversion_pct"] == 100.0
    assert steps["completed"]["conversion_pct"] == 100.0

