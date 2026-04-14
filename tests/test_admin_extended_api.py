from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.user import OAuthProvider, User
from app.models.order import Order, OrderStatus
from app.models.tariff import Tariff
from decimal import Decimal


async def _admin_headers(db_session: AsyncSession) -> dict[str, str]:
    admin = User(
        email="adm-ext@example.com",
        external_id="adm-ext",
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
async def test_admin_funnel_summary(client: AsyncClient, db_session: AsyncSession):
    headers = await _admin_headers(db_session)
    r = await client.get("/api/v1/admin/funnel/summary", headers=headers)
    assert r.status_code == 200
    assert "steps" in r.json()


@pytest.mark.asyncio
async def test_admin_promos_crud(client: AsyncClient, db_session: AsyncSession):
    headers = await _admin_headers(db_session)
    c = await client.post(
        "/api/v1/admin/promos/",
        headers=headers,
        json={"code": "SPRING", "discount_percent": 20, "max_uses": 10},
    )
    assert c.status_code == 200
    promo_id = c.json()["id"]
    p = await client.patch(f"/api/v1/admin/promos/{promo_id}", headers=headers, json={"is_active": False})
    assert p.status_code == 200
    assert p.json()["is_active"] is False


@pytest.mark.asyncio
async def test_admin_flags_toggle(client: AsyncClient, db_session: AsyncSession):
    headers = await _admin_headers(db_session)
    r = await client.patch("/api/v1/admin/flags/admin_funnel_enabled", headers=headers, json={"enabled": True})
    assert r.status_code == 200
    assert r.json()["enabled"] is True


@pytest.mark.asyncio
async def test_admin_tasks_health_logs(client: AsyncClient, db_session: AsyncSession):
    headers = await _admin_headers(db_session)
    tasks = await client.get("/api/v1/admin/tasks/", headers=headers)
    health = await client.get("/api/v1/admin/health/", headers=headers)
    logs = await client.get("/api/v1/admin/logs/", headers=headers)
    assert tasks.status_code == 200
    assert health.status_code == 200
    assert logs.status_code == 200


@pytest.mark.asyncio
async def test_admin_support_notes(client: AsyncClient, db_session: AsyncSession):
    admin_headers = await _admin_headers(db_session)
    user = User(
        email="user-ext@example.com",
        external_id="user-ext",
        oauth_provider=OAuthProvider.TELEGRAM,
        consent_given_at=datetime.utcnow(),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    add = await client.post(
        f"/api/v1/admin/support/users/{user.id}/notes",
        headers=admin_headers,
        json={"text": "Пользователь запросил помощь"},
    )
    assert add.status_code == 200
    lst = await client.get(f"/api/v1/admin/support/users/{user.id}/notes", headers=admin_headers)
    assert lst.status_code == 200
    assert len(lst.json()) == 1


@pytest.mark.asyncio
async def test_admin_support_block_and_email_patch(client: AsyncClient, db_session: AsyncSession):
    headers = await _admin_headers(db_session)
    user = User(
        email="before@example.com",
        external_id="u2",
        oauth_provider=OAuthProvider.TELEGRAM,
        consent_given_at=datetime.utcnow(),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    b = await client.post(f"/api/v1/admin/support/users/{user.id}/block", headers=headers)
    assert b.status_code == 200
    p = await client.patch(
        f"/api/v1/admin/support/users/{user.id}/email",
        headers=headers,
        json={"email": "after@example.com"},
    )
    assert p.status_code == 200


@pytest.mark.asyncio
async def test_admin_payments_search(client: AsyncClient, db_session: AsyncSession):
    headers = await _admin_headers(db_session)
    user = User(
        email="payer@example.com",
        external_id="payer",
        oauth_provider=OAuthProvider.TELEGRAM,
        consent_given_at=datetime.utcnow(),
    )
    db_session.add(user)
    tariff = Tariff(
        code="report",
        name="Отчёт",
        price=Decimal("100.00"),
        price_usd=Decimal("1.00"),
        features={"max_natal_profiles": 1},
        retention_days=30,
        llm_tier="natal_full",
    )
    db_session.add(tariff)
    await db_session.flush()
    order = Order(
        user_id=user.id,
        natal_data_id=None,
        tariff_id=tariff.id,
        amount=Decimal("100.00"),
        status=OrderStatus.PAID,
    )
    db_session.add(order)
    await db_session.commit()
    r = await client.get("/api/v1/admin/payments/?q=payer@example.com", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1
