import asyncio
import json
import sys
from decimal import Decimal
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.models.order import Order, OrderStatus
from app.models.tariff import Tariff
from app.services.payment import YookassaPaymentService
from app.services.yookassa_webhook import parse_notification
from app.utils.yookassa_ip import is_yookassa_notification_ip
from tests.conftest import TestingSessionLocal


def _payment_succeeded_body(order_id: int = 1) -> dict:
    return {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {
            "id": "22d6d597-000f-5000-9000-145f6df21d6f",
            "status": "succeeded",
            "paid": True,
            "amount": {"value": "2.00", "currency": "RUB"},
            "metadata": {"order_id": str(order_id)},
            "created_at": "2018-07-10T14:27:54.691Z",
            "description": "test",
            "payment_method": {
                "type": "bank_card",
                "id": "pm_x",
                "saved": False,
                "card": {
                    "first6": "555555",
                    "last4": "4444",
                    "expiry_month": "07",
                    "expiry_year": "2021",
                    "card_type": "MasterCard",
                    "issuer_country": "RU",
                    "issuer_name": "Sberbank",
                },
                "title": "Bank card *4444",
            },
            "refundable": False,
            "test": True,
        },
    }


def test_yookassa_ip_allowlist():
    assert is_yookassa_notification_ip("185.71.76.5") is True
    assert is_yookassa_notification_ip("77.75.156.11") is True
    assert is_yookassa_notification_ip("1.2.3.4") is False
    assert is_yookassa_notification_ip("") is False


def test_parse_notification_accepts_sdk():
    body = _payment_succeeded_body()
    parsed = parse_notification(json.dumps(body).encode())
    assert parsed["event"] == "payment.succeeded"


@pytest.mark.asyncio
async def test_yookassa_webhook_invalid_body(client: AsyncClient):
    response = await client.post("/api/v1/webhooks/yookassa", content=b"not-json")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_yookassa_webhook_rejects_non_yookassa_ip(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "YOOKASSA_WEBHOOK_VERIFY_IP", True)
    body = _payment_succeeded_body()
    response = await client.post(
        "/api/v1/webhooks/yookassa",
        content=json.dumps(body).encode(),
        headers={"X-Forwarded-For": "8.8.8.8", "Content-Type": "application/json"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_yookassa_webhook_processes_with_valid_ip(
    client: AsyncClient, monkeypatch
):
    monkeypatch.setattr(settings, "YOOKASSA_WEBHOOK_VERIFY_IP", True)
    mock_process = AsyncMock()
    monkeypatch.setattr(YookassaPaymentService, "process_webhook_event", mock_process)
    body = _payment_succeeded_body()
    response = await client.post(
        "/api/v1/webhooks/yookassa",
        content=json.dumps(body).encode(),
        headers={"X-Forwarded-For": "185.71.76.5", "Content-Type": "application/json"},
    )
    assert response.status_code == 200
    mock_process.assert_awaited_once()


@pytest.mark.asyncio
async def test_yookassa_webhook_idempotent(client: AsyncClient, monkeypatch):
    mock_process = AsyncMock()
    monkeypatch.setattr(YookassaPaymentService, "process_webhook_event", mock_process)
    body = _payment_succeeded_body()
    raw = json.dumps(body).encode()
    h = {"Content-Type": "application/json"}
    assert (await client.post("/api/v1/webhooks/yookassa", content=raw, headers=h)).status_code == 200
    assert (await client.post("/api/v1/webhooks/yookassa", content=raw, headers=h)).status_code == 200
    assert mock_process.await_count == 1


@pytest.mark.asyncio
async def test_api_verify_mismatch_returns_400(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "YOOKASSA_WEBHOOK_VERIFY_API", True)
    monkeypatch.setattr(settings, "YOOKASSA_WEBHOOK_VERIFY_IP", False)

    async def bad_verify(*args, **kwargs):
        return False

    monkeypatch.setattr(
        YookassaPaymentService,
        "verify_payment_notification_matches_api",
        bad_verify,
    )
    body = _payment_succeeded_body()
    response = await client.post(
        "/api/v1/webhooks/yookassa",
        content=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_api_verify_ok_calls_process(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "YOOKASSA_WEBHOOK_VERIFY_API", True)
    monkeypatch.setattr(settings, "YOOKASSA_WEBHOOK_VERIFY_IP", False)

    async def good_verify(*args, **kwargs):
        return True

    mock_process = AsyncMock()
    monkeypatch.setattr(
        YookassaPaymentService,
        "verify_payment_notification_matches_api",
        good_verify,
    )
    monkeypatch.setattr(YookassaPaymentService, "process_webhook_event", mock_process)
    body = _payment_succeeded_body()
    response = await client.post(
        "/api/v1/webhooks/yookassa",
        content=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200
    mock_process.assert_awaited_once()


@pytest.mark.asyncio
async def test_payment_succeeded_webhook_enqueues_report_once_under_parallel_sessions(
    db_session,
    test_user,
    monkeypatch,
):
    tariff = Tariff(
        code="whook_t",
        name="Webhook T",
        price=Decimal("10.00"),
        price_usd=Decimal("0.11"),
        features={"max_natal_profiles": 1},
        retention_days=30,
        llm_tier="natal_full",
    )
    db_session.add(tariff)
    await db_session.flush()
    order = Order(
        user_id=test_user.id,
        natal_data_id=None,
        tariff_id=tariff.id,
        amount=Decimal("10.00"),
        status=OrderStatus.PENDING,
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    mock_delay = MagicMock()
    fake_task = MagicMock()
    fake_task.delay = mock_delay
    stub_rg = ModuleType("app.tasks.report_generation")
    stub_rg.generate_report_task = fake_task
    monkeypatch.setitem(sys.modules, "app.tasks.report_generation", stub_rg)

    body = _payment_succeeded_body(order_id=order.id)
    event = json.loads(json.dumps(body))
    svc = YookassaPaymentService()

    async def run():
        async with TestingSessionLocal() as db:
            await svc.process_webhook_event(event, db)

    await asyncio.gather(run(), run())
    assert mock_delay.call_count == 1
