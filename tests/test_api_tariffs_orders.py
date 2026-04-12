import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token
from app.models.order import Order, OrderStatus
from app.models.tariff import Tariff
from app.models.user import OAuthProvider, User


@pytest.mark.asyncio
async def test_list_tariffs(client: AsyncClient, seed_report_tariff_and_natal):
    response = await client.get("/api/v1/tariffs/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["code"] == "report"
    assert data[0]["llm_tier"] == "natal_full"
    assert data[0]["max_natal_profiles"] == 1
    assert "price" in data[0]


@pytest.mark.asyncio
async def test_list_orders_empty(client: AsyncClient, auth_headers):
    response = await client.get("/api/v1/orders/", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_order_not_found(client: AsyncClient, auth_headers):
    response = await client.get("/api/v1/orders/99999", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_orders_one(
    client: AsyncClient,
    auth_headers,
    db_session,
    test_user,
    seed_report_tariff_and_natal,
):
    tariff_result = await db_session.execute(select(Tariff).where(Tariff.code == "report"))
    tariff = tariff_result.scalar_one()
    order = Order(
        user_id=test_user.id,
        natal_data_id=seed_report_tariff_and_natal["natal_data_id"],
        tariff_id=tariff.id,
        amount=tariff.price,
        status=OrderStatus.PAID,
    )
    db_session.add(order)
    await db_session.commit()

    response = await client.get("/api/v1/orders/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "paid"
    assert data[0]["report_ready"] is False
    assert data[0]["natal_data_id"] == seed_report_tariff_and_natal["natal_data_id"]
    assert data[0]["tariff"]["code"] == "report"


@pytest.mark.asyncio
async def test_natal_requires_privacy_without_prior_consent(client: AsyncClient, db_session):
    user = User(
        email="noprivacy@example.com",
        external_id="noprivacy",
        oauth_provider=OAuthProvider.TELEGRAM,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    token = create_access_token({"sub": str(user.id), "tv": user.token_version})
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "full_name": "Test User",
        "birth_date": "1990-01-01T00:00:00",
        "birth_time": "1990-01-01T12:00:00",
        "birth_place": "Moscow",
        "lat": 55.7558,
        "lon": 37.6173,
        "timezone": "Europe/Moscow",
        "house_system": "P",
        "accept_privacy_policy": False,
    }
    response = await client.post("/api/v1/natal-data/", json=payload, headers=headers)
    assert response.status_code == 400
