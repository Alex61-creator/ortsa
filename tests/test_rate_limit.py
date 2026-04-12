import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.core.rate_limit import limiter


@pytest.fixture(autouse=True)
def _reset_rate_limit_storage():
    limiter.reset()
    yield
    limiter.reset()


@pytest.mark.asyncio
async def test_rate_limit_orders(
    client: AsyncClient,
    auth_headers,
    seed_report_tariff_and_natal,
    monkeypatch,
):
    async def fake_create_payment(
        self,
        order_id,
        amount,
        description,
        user_email,
        metadata=None,
        save_payment_method=False,
        **kwargs,
    ):
        return {
            "id": f"test-pay-{order_id}",
            "status": "pending",
            "confirmation_url": "https://test.example/pay",
        }

    monkeypatch.setattr(
        "app.api.v1.orders.YookassaPaymentService.create_payment",
        fake_create_payment,
    )

    payload = {
        "tariff_code": seed_report_tariff_and_natal["tariff_code"],
        "natal_data_id": seed_report_tariff_and_natal["natal_data_id"],
    }
    limit = settings.RATE_LIMIT_ORDERS_PER_MINUTE

    for _ in range(limit):
        response = await client.post("/api/v1/orders/", json=payload, headers=auth_headers)
        assert response.status_code == 200, response.text

    response = await client.post("/api/v1/orders/", json=payload, headers=auth_headers)
    assert response.status_code == 429
