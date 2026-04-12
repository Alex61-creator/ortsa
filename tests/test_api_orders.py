from datetime import datetime
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token
from app.models.natal_data import NatalData
from app.models.order import Order, OrderStatus
from app.models.tariff import Tariff
from app.models.user import OAuthProvider, User


@pytest.mark.asyncio
async def test_create_order_second_free_tariff_rejected(
    client: AsyncClient,
    auth_headers,
    test_user,
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        "app.api.v1.orders._queue_free_report",
        lambda order_id: None,
    )
    tariff = Tariff(
        code="free",
        name="Free",
        price=Decimal("0.00"),
        price_usd=Decimal("0.00"),
        features={"max_natal_profiles": 1},
        retention_days=30,
        llm_tier="free",
    )
    db_session.add(tariff)
    await db_session.flush()
    natal = NatalData(
        user_id=test_user.id,
        full_name="Test User",
        birth_date=datetime(1990, 1, 1, 0, 0, 0),
        birth_time=datetime(1990, 1, 1, 12, 0, 0),
        birth_place="Moscow",
        lat=55.7558,
        lon=37.6173,
        timezone="Europe/Moscow",
        house_system="P",
    )
    db_session.add(natal)
    await db_session.commit()
    await db_session.refresh(natal)

    r1 = await client.post(
        "/api/v1/orders/",
        json={"tariff_code": "free", "natal_data_id": natal.id},
        headers=auth_headers,
    )
    assert r1.status_code == 200
    r2 = await client.post(
        "/api/v1/orders/",
        json={"tariff_code": "free", "natal_data_id": natal.id},
        headers=auth_headers,
    )
    assert r2.status_code == 400
    assert "бесплатн" in r2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_order_requires_auth(client: AsyncClient):
    response = await client.post(
        "/api/v1/orders/",
        json={"tariff_code": "report", "natal_data_id": 1},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_order_yookassa_failure_marks_order_failed(
    client: AsyncClient,
    auth_headers,
    seed_report_tariff_and_natal,
    db_session,
    monkeypatch,
):
    async def boom(*args, **kwargs):
        raise RuntimeError("YooKassa unavailable")

    monkeypatch.setattr(
        "app.api.v1.orders.YookassaPaymentService.create_payment",
        boom,
    )
    response = await client.post(
        "/api/v1/orders/",
        json={
            "tariff_code": "report",
            "natal_data_id": seed_report_tariff_and_natal["natal_data_id"],
        },
        headers=auth_headers,
    )
    assert response.status_code == 502
    res = await db_session.execute(select(Order))
    orders = res.scalars().all()
    assert len(orders) == 1
    assert orders[0].status == OrderStatus.FAILED_TO_INIT_PAYMENT


@pytest.mark.asyncio
async def test_create_order_placeholder_user_requires_report_delivery_email(
    client,
    db_session,
    monkeypatch,
):
    """Аккаунт tg_*@telegram.local не может оплатить заказ без явного email."""
    tariff = Tariff(
        code="report",
        name="Отчёт",
        price=Decimal("100.00"),
        price_usd=Decimal("1.05"),
        features={"max_natal_profiles": 1},
        retention_days=30,
        llm_tier="natal_full",
    )
    db_session.add(tariff)
    user = User(
        email="tg_999@telegram.local",
        external_id="999",
        oauth_provider=OAuthProvider.TELEGRAM,
        consent_given_at=datetime.utcnow(),
    )
    db_session.add(user)
    await db_session.flush()
    natal = NatalData(
        user_id=user.id,
        full_name="T",
        birth_date=datetime(1990, 1, 1, 0, 0, 0),
        birth_time=datetime(1990, 1, 1, 12, 0, 0),
        birth_place="Moscow",
        lat=55.7558,
        lon=37.6173,
        timezone="Europe/Moscow",
        house_system="P",
    )
    db_session.add(natal)
    await db_session.commit()
    await db_session.refresh(natal)

    async def _no_payment(*args, **kwargs):
        raise AssertionError("create_payment should not be called")

    monkeypatch.setattr(
        "app.api.v1.orders.YookassaPaymentService.create_payment",
        _no_payment,
    )

    token = create_access_token({"sub": str(user.id), "tv": user.token_version})
    response = await client.post(
        "/api/v1/orders/",
        json={"tariff_code": "report", "natal_data_id": natal.id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert "report_delivery_email" in response.json().get("detail", "").lower()


@pytest.mark.asyncio
async def test_create_order_placeholder_user_passes_delivery_email_to_yookassa(
    client,
    db_session,
    monkeypatch,
):
    """С явным report_delivery_email в ЮKassa уходит этот адрес, а не tg_*@telegram.local."""
    tariff = Tariff(
        code="report",
        name="Отчёт",
        price=Decimal("100.00"),
        price_usd=Decimal("1.05"),
        features={"max_natal_profiles": 1},
        retention_days=30,
        llm_tier="natal_full",
    )
    db_session.add(tariff)
    user = User(
        email="tg_1001@telegram.local",
        external_id="1001",
        oauth_provider=OAuthProvider.TELEGRAM,
        consent_given_at=datetime.utcnow(),
    )
    db_session.add(user)
    await db_session.flush()
    natal = NatalData(
        user_id=user.id,
        full_name="T",
        birth_date=datetime(1990, 1, 1, 0, 0, 0),
        birth_time=datetime(1990, 1, 1, 12, 0, 0),
        birth_place="Moscow",
        lat=55.7558,
        lon=37.6173,
        timezone="Europe/Moscow",
        house_system="P",
    )
    db_session.add(natal)
    await db_session.commit()
    await db_session.refresh(natal)

    captured: dict = {}

    async def fake_create_payment(
        self,
        order_id,
        amount,
        description,
        user_email,
        metadata=None,
        *,
        save_payment_method=False,
    ):
        captured["user_email"] = user_email
        return {
            "id": "ym_test_1",
            "status": "pending",
            "confirmation_url": "https://yookassa.example/pay",
        }

    monkeypatch.setattr(
        "app.api.v1.orders.YookassaPaymentService.create_payment",
        fake_create_payment,
    )

    token = create_access_token({"sub": str(user.id), "tv": user.token_version})
    response = await client.post(
        "/api/v1/orders/",
        json={
            "tariff_code": "report",
            "natal_data_id": natal.id,
            "report_delivery_email": "invoice@customer.com",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert captured.get("user_email") == "invoice@customer.com"


@pytest.mark.asyncio
async def test_create_order_real_user_uses_account_email_for_yookassa_when_no_delivery(
    client,
    auth_headers,
    seed_report_tariff_and_natal,
    monkeypatch,
):
    """У пользователя с реальным email чек уходит на user.email, если delivery не указан."""
    captured: dict = {}

    async def fake_create_payment(
        self,
        order_id,
        amount,
        description,
        user_email,
        metadata=None,
        *,
        save_payment_method=False,
    ):
        captured["user_email"] = user_email
        return {
            "id": "ym_test_2",
            "status": "pending",
            "confirmation_url": "https://yookassa.example/pay",
        }

    monkeypatch.setattr(
        "app.api.v1.orders.YookassaPaymentService.create_payment",
        fake_create_payment,
    )

    response = await client.post(
        "/api/v1/orders/",
        json={
            "tariff_code": "report",
            "natal_data_id": seed_report_tariff_and_natal["natal_data_id"],
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert captured.get("user_email") == "test@example.com"
