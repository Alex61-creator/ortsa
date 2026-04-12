from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.order import Order, OrderStatus
from app.models.tariff import Tariff
from app.models.user import OAuthProvider, User


@pytest.mark.asyncio
async def test_ops_metrics_forbidden_without_admin(client: AsyncClient, auth_headers):
    r = await client.get("/api/v1/ops/metrics/orders", headers=auth_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_ops_metrics_ok_for_admin(client: AsyncClient, db_session: AsyncSession):
    admin = User(
        email="admin-ops@example.com",
        external_id="admin-ops",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
        is_admin=True,
    )
    db_session.add(admin)
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
    old = datetime.now(timezone.utc) - timedelta(hours=3)
    db_session.add(
        Order(
            user_id=admin.id,
            natal_data_id=None,
            tariff_id=tariff.id,
            amount=Decimal("100.00"),
            status=OrderStatus.FAILED,
        )
    )
    db_session.add(
        Order(
            user_id=admin.id,
            natal_data_id=None,
            tariff_id=tariff.id,
            amount=Decimal("100.00"),
            status=OrderStatus.PROCESSING,
            updated_at=old,
        )
    )
    await db_session.commit()

    token = create_access_token({"sub": str(admin.id), "tv": admin.token_version})
    r = await client.get(
        "/api/v1/ops/metrics/orders",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["failed_orders_total"] >= 1
    assert data["processing_stuck_over_2h"] >= 1
