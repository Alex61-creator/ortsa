import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.user import OAuthProvider, User


@pytest.mark.asyncio
async def test_admin_one_time_monthly_ok(client: AsyncClient, db_session: AsyncSession):
    admin = User(
        email="adm-otm@example.com",
        external_id="adm-otm",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=__import__("datetime").datetime.utcnow(),
        is_admin=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    token = create_access_token({"sub": str(admin.id), "tv": admin.token_version})
    r = await client.get("/api/v1/admin/metrics/one-time-monthly", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert "rows" in r.json()


@pytest.mark.asyncio
async def test_admin_report_options_analytics_ok(client: AsyncClient, db_session: AsyncSession):
    admin = User(
        email="adm-ro@example.com",
        external_id="adm-ro",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=__import__("datetime").datetime.utcnow(),
        is_admin=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    token = create_access_token({"sub": str(admin.id), "tv": admin.token_version})
    r = await client.get("/api/v1/admin/metrics/report-options-analytics", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert "key_counts" in data
    assert "bucket_counts" in data


@pytest.mark.asyncio
async def test_admin_subscriptions_overview_ok(client: AsyncClient, db_session: AsyncSession):
    admin = User(
        email="adm-so@example.com",
        external_id="adm-so",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=__import__("datetime").datetime.utcnow(),
        is_admin=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    token = create_access_token({"sub": str(admin.id), "tv": admin.token_version})
    r = await client.get("/api/v1/admin/metrics/subscriptions-overview", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert "monthly_rows" in r.json()
