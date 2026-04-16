from datetime import datetime, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.analytics_event import AnalyticsEvent
from app.models.order import Order, OrderStatus
from app.models.tariff import Tariff
from app.models.user import OAuthProvider, User


async def _admin_headers(db_session: AsyncSession) -> dict[str, str]:
    admin = User(
        email="adm-funnel-event@example.com",
        external_id="adm-funnel-event",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
        is_admin=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    token = create_access_token({"sub": str(admin.id), "tv": admin.token_version})
    return {"Authorization": f"Bearer {token}"}


def _dt_utc(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@pytest.mark.asyncio
async def test_metrics_funnel_event_based_filtered(
    client: AsyncClient,
    db_session: AsyncSession,
):
    headers = await _admin_headers(db_session)

    # Period: Jan 2026
    start_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end_at = datetime(2026, 2, 1, tzinfo=timezone.utc)

    # Seed tariffs
    bundle = Tariff(
        code="bundle",
        name="Bundle",
        price=Decimal("100.00"),
        price_usd=Decimal("1.00"),
        features={"max_natal_profiles": 1},
        retention_days=30,
        llm_tier="natal_full",
    )
    report = Tariff(
        code="report",
        name="Report",
        price=Decimal("300.00"),
        price_usd=Decimal("3.00"),
        features={"max_natal_profiles": 1},
        retention_days=30,
        llm_tier="natal_full",
    )
    synastry = Tariff(
        code="synastry_addon",
        name="Synastry Addon",
        price=Decimal("20.00"),
        price_usd=Decimal("0.20"),
        features={"max_natal_profiles": 1},
        retention_days=30,
        llm_tier="natal_full",
    )
    db_session.add_all([bundle, report, synastry])

    # Users (two tg_ads, one email_ads)
    user1 = User(
        email="u1-funnel@example.com",
        external_id="u1-funnel",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
        source_channel="tg_ads",
        signup_platform="web",
        signup_geo="RU",
    )
    user2 = User(
        email="u2-funnel@example.com",
        external_id="u2-funnel",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
        source_channel="tg_ads",
        signup_platform="web",
        signup_geo="RU",
    )
    user3 = User(
        email="u3-funnel@example.com",
        external_id="u3-funnel",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
        source_channel="email_ads",
        signup_platform="web",
        signup_geo="RU",
    )
    db_session.add_all([user1, user2, user3])
    await db_session.commit()
    await db_session.flush()

    # Orders for FK integrity
    order1 = Order(user_id=user1.id, tariff_id=bundle.id, amount=Decimal("100.00"), status=OrderStatus.COMPLETED)
    order2 = Order(user_id=user2.id, tariff_id=bundle.id, amount=Decimal("200.00"), status=OrderStatus.COMPLETED)
    order3 = Order(user_id=user3.id, tariff_id=report.id, amount=Decimal("300.00"), status=OrderStatus.COMPLETED)
    addon_order = Order(user_id=user1.id, tariff_id=synastry.id, amount=Decimal("20.00"), status=OrderStatus.COMPLETED)
    db_session.add_all([order1, order2, order3, addon_order])
    await db_session.commit()
    await db_session.flush()

    events: list[AnalyticsEvent] = [
        # signup + first purchase + cohort anchor
        AnalyticsEvent(
            event_name="signup_completed",
            user_id=user1.id,
            order_id=None,
            tariff_code=None,
            source_channel="tg_ads",
            amount=None,
            currency=None,
            cost_components=None,
            event_metadata=None,
            correlation_id=None,
            dedupe_key="signup:u1",
            event_time=_dt_utc("2026-01-05T12:00:00Z"),
        ),
        AnalyticsEvent(
            event_name="signup_completed",
            user_id=user2.id,
            order_id=None,
            tariff_code=None,
            source_channel="tg_ads",
            amount=None,
            currency=None,
            cost_components=None,
            event_metadata=None,
            correlation_id=None,
            dedupe_key="signup:u2",
            event_time=_dt_utc("2026-01-10T12:00:00Z"),
        ),
        AnalyticsEvent(
            event_name="signup_completed",
            user_id=user3.id,
            order_id=None,
            tariff_code=None,
            source_channel="email_ads",
            amount=None,
            currency=None,
            cost_components=None,
            event_metadata=None,
            correlation_id=None,
            dedupe_key="signup:u3",
            event_time=_dt_utc("2026-01-07T12:00:00Z"),
        ),
        AnalyticsEvent(
            event_name="first_purchase_completed",
            user_id=user1.id,
            order_id=order1.id,
            tariff_code="bundle",
            source_channel="tg_ads",
            amount=Decimal("100.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
            correlation_id=None,
            dedupe_key="fp:u1",
            event_time=_dt_utc("2026-01-06T12:00:00Z"),
        ),
        AnalyticsEvent(
            event_name="first_purchase_completed",
            user_id=user2.id,
            order_id=order2.id,
            tariff_code="bundle",
            source_channel="tg_ads",
            amount=Decimal("200.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
            correlation_id=None,
            dedupe_key="fp:u2",
            event_time=_dt_utc("2026-01-11T12:00:00Z"),
        ),
        AnalyticsEvent(
            event_name="first_purchase_completed",
            user_id=user3.id,
            order_id=order3.id,
            tariff_code="report",
            source_channel="email_ads",
            amount=Decimal("300.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
            correlation_id=None,
            dedupe_key="fp:u3",
            event_time=_dt_utc("2026-01-08T12:00:00Z"),
        ),
        # Completed orders
        AnalyticsEvent(
            event_name="order_completed",
            user_id=user1.id,
            order_id=order1.id,
            tariff_code="bundle",
            source_channel="tg_ads",
            amount=Decimal("100.00"),
            currency="RUB",
            cost_components={
                "variable_cost_amount": 1.0,
                "payment_fee_amount": 2.0,
                "ai_cost_amount": 3.0,
                "infra_cost_amount": 4.0,
            },
            event_metadata=None,
            correlation_id=None,
            dedupe_key="oc:order1",
            event_time=_dt_utc("2026-01-20T12:00:00Z"),
        ),
        AnalyticsEvent(
            event_name="order_completed",
            user_id=user2.id,
            order_id=order2.id,
            tariff_code="bundle",
            source_channel="tg_ads",
            amount=Decimal("200.00"),
            currency="RUB",
            cost_components={
                "variable_cost_amount": 2.0,
                "payment_fee_amount": 3.0,
                "ai_cost_amount": 1.0,
                "infra_cost_amount": 4.0,
            },
            event_metadata=None,
            correlation_id=None,
            dedupe_key="oc:order2",
            event_time=_dt_utc("2026-01-25T12:00:00Z"),
        ),
        AnalyticsEvent(
            event_name="order_completed",
            user_id=user3.id,
            order_id=order3.id,
            tariff_code="report",
            source_channel="email_ads",
            amount=Decimal("300.00"),
            currency="RUB",
            cost_components={
                "variable_cost_amount": 1.0,
                "payment_fee_amount": 1.0,
                "ai_cost_amount": 1.0,
                "infra_cost_amount": 1.0,
            },
            event_metadata=None,
            correlation_id=None,
            dedupe_key="oc:order3",
            event_time=_dt_utc("2026-01-12T12:00:00Z"),
        ),
        # Addon attached
        AnalyticsEvent(
            event_name="addon_attached",
            user_id=user1.id,
            order_id=addon_order.id,
            tariff_code="synastry_addon",
            source_channel="tg_ads",
            amount=Decimal("20.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
            correlation_id=None,
            dedupe_key="aa:addon",
            event_time=_dt_utc("2026-01-21T12:00:00Z"),
        ),
    ]

    db_session.add_all(events)
    await db_session.commit()

    resp = await client.get(
        "/api/v1/admin/metrics/funnel",
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
    data = resp.json()
    steps = {s["key"]: s for s in data["steps"]}
    assert steps["signup"]["count"] == 2
    assert steps["first_purchase"]["count"] == 2
    assert steps["completed"]["count"] == 2
    assert steps["addon"]["count"] == 1
    assert steps["addon"]["conversion_pct"] == 50.0

    # Same period without filters: should include user3 as well.
    resp2 = await client.get(
        "/api/v1/admin/metrics/funnel",
        headers=headers,
        params={
            "period": "custom",
            "date_from": start_at.isoformat(),
            "date_to": end_at.isoformat(),
        },
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    steps2 = {s["key"]: s for s in data2["steps"]}
    assert steps2["signup"]["count"] == 3
    assert steps2["first_purchase"]["count"] == 3
    assert steps2["completed"]["count"] == 3
    assert steps2["addon"]["count"] == 1
    assert steps2["addon"]["conversion_pct"] == 33.3

