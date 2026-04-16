"""Admin campaign / UTM performance metrics (analytics_events)."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.analytics_event import AnalyticsEvent
from app.models.order import Order, OrderStatus
from app.models.tariff import Tariff
from app.models.user import OAuthProvider, User


@pytest.mark.asyncio
async def test_campaign_performance_groups_by_campaign(client: AsyncClient, db_session: AsyncSession):
    admin = User(
        email="adm-camp@example.com",
        external_id="adm-camp",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.now(timezone.utc),
        is_admin=True,
    )
    db_session.add(admin)
    u1 = User(
        email="u1-camp@example.com",
        external_id="u1-camp",
        oauth_provider=OAuthProvider.TELEGRAM,
        consent_given_at=datetime.now(timezone.utc),
    )
    u2 = User(
        email="u2-camp@example.com",
        external_id="u2-camp",
        oauth_provider=OAuthProvider.TELEGRAM,
        consent_given_at=datetime.now(timezone.utc),
    )
    db_session.add_all([u1, u2])
    await db_session.flush()

    tariff = Tariff(
        code="report",
        name="Отчёт",
        price=Decimal("100"),
        price_usd=Decimal("1"),
        features={},
        retention_days=30,
        llm_tier="natal_full",
        billing_type="one_time",
    )
    db_session.add(tariff)
    await db_session.flush()
    order1 = Order(
        user_id=u1.id,
        tariff_id=tariff.id,
        amount=Decimal("100"),
        status=OrderStatus.PAID,
    )
    db_session.add(order1)
    await db_session.flush()

    t0 = datetime.now(timezone.utc) - timedelta(days=1)
    evs = [
        AnalyticsEvent(
            event_name="signup_completed",
            user_id=u1.id,
            order_id=None,
            utm_campaign="spring",
            source_channel="telegram",
            event_time=t0,
        ),
        AnalyticsEvent(
            event_name="signup_completed",
            user_id=u2.id,
            order_id=None,
            utm_campaign="spring",
            source_channel="google",
            event_time=t0,
        ),
        AnalyticsEvent(
            event_name="first_purchase_completed",
            user_id=u1.id,
            order_id=order1.id,
            utm_campaign="spring",
            amount=Decimal("100.00"),
            event_time=t0,
        ),
    ]
    for e in evs:
        db_session.add(e)
    await db_session.commit()

    token = create_access_token({"sub": str(admin.id), "tv": admin.token_version})
    r = await client.get(
        "/api/v1/admin/metrics/campaign-performance",
        headers={"Authorization": f"Bearer {token}"},
        params={"group_by": "campaign"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["group_by"] == "campaign"
    assert data["billing_segment"] == "all"
    row = next((x for x in data["rows"] if x["segment_key"] == "spring"), None)
    assert row is not None
    assert row["signups"] == 2
    assert row["first_paid_users"] == 1
    assert float(row["first_paid_revenue_rub"]) == pytest.approx(100.0)
    assert row["cr1"] == pytest.approx(0.5)


@pytest.mark.asyncio
async def test_campaign_performance_one_time_segment(client: AsyncClient, db_session: AsyncSession):
    admin = User(
        email="adm-c2@example.com",
        external_id="adm-c2",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.now(timezone.utc),
        is_admin=True,
    )
    db_session.add(admin)
    user = User(
        email="u-c2@example.com",
        external_id="u-c2",
        oauth_provider=OAuthProvider.TELEGRAM,
        consent_given_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    tariff_sub = Tariff(
        code="sub_monthly",
        name="Pro",
        price=Decimal("500"),
        price_usd=Decimal("5"),
        features={},
        retention_days=30,
        llm_tier="pro",
        billing_type="subscription",
    )
    tariff_ot = Tariff(
        code="report",
        name="Отчёт",
        price=Decimal("100"),
        price_usd=Decimal("1"),
        features={},
        retention_days=30,
        llm_tier="natal_full",
        billing_type="one_time",
    )
    db_session.add_all([tariff_sub, tariff_ot])
    await db_session.flush()
    o_sub = Order(
        user_id=user.id,
        tariff_id=tariff_sub.id,
        amount=Decimal("500"),
        status=OrderStatus.PAID,
    )
    o_ot = Order(
        user_id=user.id,
        tariff_id=tariff_ot.id,
        amount=Decimal("100"),
        status=OrderStatus.PAID,
    )
    db_session.add_all([o_sub, o_ot])
    await db_session.flush()

    t0 = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.add_all(
        [
            AnalyticsEvent(
                event_name="first_purchase_completed",
                user_id=user.id,
                order_id=o_sub.id,
                utm_campaign="mix",
                amount=Decimal("500"),
                event_time=t0,
            ),
            AnalyticsEvent(
                event_name="first_purchase_completed",
                user_id=user.id,
                order_id=o_ot.id,
                utm_campaign="mix",
                amount=Decimal("100"),
                event_time=t0,
            ),
        ]
    )
    await db_session.commit()

    token = create_access_token({"sub": str(admin.id), "tv": admin.token_version})
    r = await client.get(
        "/api/v1/admin/metrics/campaign-performance",
        headers={"Authorization": f"Bearer {token}"},
        params={"group_by": "campaign", "billing_segment": "one_time"},
    )
    assert r.status_code == 200
    data = r.json()
    row = next((x for x in data["rows"] if x["segment_key"] == "mix"), None)
    assert row is not None
    assert row["first_paid_users"] == 1
    assert float(row["first_paid_revenue_rub"]) == pytest.approx(100.0)


@pytest.mark.asyncio
async def test_campaign_performance_one_time_alias_route(client: AsyncClient, db_session: AsyncSession):
    admin = User(
        email="adm-c3@example.com",
        external_id="adm-c3",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.now(timezone.utc),
        is_admin=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    token = create_access_token({"sub": str(admin.id), "tv": admin.token_version})
    r = await client.get(
        "/api/v1/admin/metrics/campaign-performance/one-time",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["billing_segment"] == "one_time"

