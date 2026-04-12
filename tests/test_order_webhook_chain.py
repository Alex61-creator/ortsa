"""
Сквозной сценарий на моках: POST /orders (оплата замокана) → POST /webhooks/yookassa → заказ PAID, постановка отчёта.
Без реальных ключей ЮKassa.
"""

import json
import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.models.order import Order, OrderStatus
from tests.test_webhooks import _payment_succeeded_body


@pytest.mark.asyncio
async def test_http_create_order_then_yookassa_webhook_paid_and_enqueue_report(
    client: AsyncClient,
    auth_headers,
    seed_report_tariff_and_natal,
    db_session,
    monkeypatch,
):
    mock_delay = MagicMock()
    fake_task = MagicMock()
    fake_task.delay = mock_delay
    stub_rg = ModuleType("app.tasks.report_generation")
    stub_rg.generate_report_task = fake_task
    monkeypatch.setitem(sys.modules, "app.tasks.report_generation", stub_rg)

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
        return {
            "id": "ym_chain_1",
            "status": "pending",
            "confirmation_url": "https://yookassa.example/pay",
        }

    monkeypatch.setattr(
        "app.api.v1.orders.YookassaPaymentService.create_payment",
        fake_create_payment,
    )
    monkeypatch.setattr(settings, "YOOKASSA_WEBHOOK_VERIFY_IP", False)
    monkeypatch.setattr(settings, "YOOKASSA_WEBHOOK_VERIFY_API", False)

    r = await client.post(
        "/api/v1/orders/",
        json={
            "tariff_code": "report",
            "natal_data_id": seed_report_tariff_and_natal["natal_data_id"],
        },
        headers=auth_headers,
    )
    assert r.status_code == 200
    oid = r.json()["id"]

    body = _payment_succeeded_body(order_id=oid)
    wr = await client.post(
        "/api/v1/webhooks/yookassa",
        content=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    assert wr.status_code == 200

    res = await db_session.execute(select(Order).where(Order.id == oid))
    order = res.scalar_one()
    assert order.status == OrderStatus.PAID
    mock_delay.assert_called_once_with(oid)


@pytest.mark.asyncio
async def test_landing_html_includes_content_security_policy(client: AsyncClient):
    r = await client.get("/")
    assert r.status_code == 200
    assert "content-security-policy" in {k.lower() for k in r.headers.keys()}
    csp = r.headers.get("content-security-policy") or r.headers.get("Content-Security-Policy")
    assert csp and "default-src" in csp
