from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription, SubscriptionStatus
from app.models.tariff import Tariff
from app.models.user import OAuthProvider, User


@pytest.fixture
async def user_with_tariff(db_session: AsyncSession):
    user = User(
        email="subuser@example.com",
        external_id="sub-ext",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
    )
    db_session.add(user)
    await db_session.flush()
    tariff = Tariff(
        code="pro",
        name="Astro Pro",
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
    return user, tariff


@pytest.fixture
def auth_headers_user(user_with_tariff):
    from app.core.security import create_access_token

    user, _ = user_with_tariff
    token = create_access_token({"sub": str(user.id), "tv": user.token_version})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_resume_subscription_clears_cancel_flag(
    client: AsyncClient,
    db_session: AsyncSession,
    user_with_tariff,
    auth_headers_user,
):
    user, tariff = user_with_tariff
    sub = Subscription(
        user_id=user.id,
        tariff_id=tariff.id,
        status=SubscriptionStatus.ACTIVE.value,
        current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
        cancel_at_period_end=True,
    )
    db_session.add(sub)
    await db_session.commit()

    r = await client.post("/api/v1/subscriptions/me/resume", headers=auth_headers_user)
    assert r.status_code == 200
    body = r.json()
    assert body["cancel_at_period_end"] is False


@pytest.mark.asyncio
async def test_resume_without_pending_cancel_returns_400(
    client: AsyncClient,
    db_session: AsyncSession,
    user_with_tariff,
    auth_headers_user,
):
    user, tariff = user_with_tariff
    sub = Subscription(
        user_id=user.id,
        tariff_id=tariff.id,
        status=SubscriptionStatus.ACTIVE.value,
        current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
        cancel_at_period_end=False,
    )
    db_session.add(sub)
    await db_session.commit()

    r = await client.post("/api/v1/subscriptions/me/resume", headers=auth_headers_user)
    assert r.status_code == 400
    assert "not scheduled" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_resume_no_subscription_returns_404(client: AsyncClient, auth_headers_user):
    r = await client.post("/api/v1/subscriptions/me/resume", headers=auth_headers_user)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_me_subscription_past_due_includes_message(
    client: AsyncClient,
    db_session: AsyncSession,
    user_with_tariff,
    auth_headers_user,
):
    user, tariff = user_with_tariff
    sub = Subscription(
        user_id=user.id,
        tariff_id=tariff.id,
        status=SubscriptionStatus.PAST_DUE.value,
        current_period_end=datetime.now(timezone.utc) - timedelta(days=1),
        cancel_at_period_end=False,
    )
    db_session.add(sub)
    await db_session.commit()

    r = await client.get("/api/v1/subscriptions/me", headers=auth_headers_user)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "past_due"
    assert body["status_message"]
    assert "оплат" in body["status_message"].lower()
