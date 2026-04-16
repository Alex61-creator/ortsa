import asyncio
import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.rate_limit import limiter
from app.api.v1.orders import _build_order_request_fingerprint
from app.models.order import Order, OrderStatus
from app.models.order_idempotency import OrderIdempotency, OrderIdempotencyState
from app.models.user import User
@pytest.fixture(autouse=True)
def _reset_rate_limit_storage():
    limiter.reset()
    yield
    limiter.reset()



@pytest.mark.asyncio
async def test_post_orders_idempotent_returns_same_order_and_does_not_recreate_payment(
    client: AsyncClient,
    auth_headers,
    test_user,
    db_session,
    seed_report_tariff_and_natal,
    monkeypatch,
):
    idem_key = "idem-order-1"

    payment = {
        "id": "ym_idempotent_1",
        "status": "pending",
        "confirmation_url": "https://yookassa.example/pay/idem-order-1",
    }
    mock_create_payment = AsyncMock(return_value=payment)

    async def fake_create_payment(*args, **kwargs):
        return await mock_create_payment(*args, **kwargs)

    monkeypatch.setattr(
        "app.api.v1.orders.YookassaPaymentService.create_payment",
        fake_create_payment,
    )

    r1 = await client.post(
        "/api/v1/orders/",
        json={
            "tariff_code": seed_report_tariff_and_natal["tariff_code"],
            "natal_data_id": seed_report_tariff_and_natal["natal_data_id"],
        },
        headers={**auth_headers, "Idempotency-Key": idem_key},
    )
    assert r1.status_code == 200
    data1 = r1.json()

    r2 = await client.post(
        "/api/v1/orders/",
        json={
            "tariff_code": seed_report_tariff_and_natal["tariff_code"],
            "natal_data_id": seed_report_tariff_and_natal["natal_data_id"],
        },
        headers={**auth_headers, "Idempotency-Key": idem_key},
    )
    assert r2.status_code == 200
    data2 = r2.json()

    assert data2["id"] == data1["id"]
    assert data2["yookassa_id"] == data1["yookassa_id"]
    assert data2["confirmation_url"] == data1["confirmation_url"]

    res = await db_session.execute(select(Order).where(Order.user_id == test_user.id))
    orders = res.scalars().all()
    assert len(orders) == 1

    assert mock_create_payment.await_count == 1
    assert mock_create_payment.call_args.kwargs.get("idempotency_key") == idem_key

    idem_stmt = select(OrderIdempotency).where(
        OrderIdempotency.user_id == test_user.id,
        OrderIdempotency.idempotency_key == idem_key,
    )
    idem_row = (await db_session.execute(idem_stmt)).scalar_one()
    assert idem_row.state == OrderIdempotencyState.COMPLETED
    assert idem_row.order_id == data1["id"]


@pytest.mark.asyncio
async def test_post_orders_idempotent_parallel_requests_second_gets_409(
    client: AsyncClient,
    auth_headers,
    test_user,
    db_session,
    seed_report_tariff_and_natal,
    monkeypatch,
):
    idem_key = "idem-order-2"

    payment = {
        "id": "ym_idempotent_2",
        "status": "pending",
        "confirmation_url": "https://yookassa.example/pay/idem-order-2",
    }

    started = asyncio.Event()
    release = asyncio.Event()

    async def fake_create_payment(*args, **kwargs):
        started.set()
        await release.wait()
        return payment

    mock_create_payment = AsyncMock(side_effect=fake_create_payment)
    monkeypatch.setattr(
        "app.api.v1.orders.YookassaPaymentService.create_payment",
        mock_create_payment,
    )

    async def post_once():
        return await client.post(
            "/api/v1/orders/",
            json={
                "tariff_code": seed_report_tariff_and_natal["tariff_code"],
                "natal_data_id": seed_report_tariff_and_natal["natal_data_id"],
            },
            headers={**auth_headers, "Idempotency-Key": idem_key},
        )

    # 1) Стартуем первый запрос.
    t1 = asyncio.create_task(post_once())
    await asyncio.wait_for(started.wait(), timeout=5.0)

    # 2) Пока create_payment первого заблокирован, запускаем второй.
    r2 = await post_once()
    assert r2.status_code == 409

    # 3) Разблокируем create_payment первого и получаем его ответ.
    release.set()
    r1 = await t1

    statuses = sorted([r1.status_code, r2.status_code])
    assert statuses == [200, 409]

    assert mock_create_payment.await_count == 1

    res = await db_session.execute(select(Order).where(Order.user_id == test_user.id))
    orders = res.scalars().all()
    assert len(orders) == 1


@pytest.mark.asyncio
async def test_post_orders_idempotent_failed_attempt_returns_same_502_and_does_not_retry_create_payment(
    client: AsyncClient,
    auth_headers,
    test_user,
    db_session,
    seed_report_tariff_and_natal,
    monkeypatch,
    caplog,
):
    idem_key = "idem-order-3"
    caplog.set_level(logging.ERROR, logger="app.api.v1.orders")

    async def boom(*args, **kwargs):
        raise RuntimeError("YooKassa down")

    mock_create_payment = AsyncMock(side_effect=boom)
    monkeypatch.setattr(
        "app.api.v1.orders.YookassaPaymentService.create_payment",
        mock_create_payment,
    )

    r1 = await client.post(
        "/api/v1/orders/",
        json={
            "tariff_code": seed_report_tariff_and_natal["tariff_code"],
            "natal_data_id": seed_report_tariff_and_natal["natal_data_id"],
        },
        headers={**auth_headers, "Idempotency-Key": idem_key},
    )
    assert r1.status_code == 502
    assert "YooKassa create_payment failed" in caplog.text

    r2 = await client.post(
        "/api/v1/orders/",
        json={
            "tariff_code": seed_report_tariff_and_natal["tariff_code"],
            "natal_data_id": seed_report_tariff_and_natal["natal_data_id"],
        },
        headers={**auth_headers, "Idempotency-Key": idem_key},
    )
    assert r2.status_code == 502

    assert mock_create_payment.await_count == 1

    res = await db_session.execute(select(Order).where(Order.user_id == test_user.id))
    orders = res.scalars().all()
    assert len(orders) == 1
    assert orders[0].status == OrderStatus.FAILED_TO_INIT_PAYMENT

    idem_stmt = select(OrderIdempotency).where(
        OrderIdempotency.user_id == test_user.id,
        OrderIdempotency.idempotency_key == idem_key,
    )
    idem_row = (await db_session.execute(idem_stmt)).scalar_one()
    assert idem_row.state == OrderIdempotencyState.FAILED


@pytest.mark.asyncio
async def test_post_orders_idempotent_same_key_with_different_payload_returns_409(
    client: AsyncClient,
    auth_headers,
    seed_report_tariff_and_natal,
    monkeypatch,
):
    idem_key = "idem-order-payload-mismatch"
    payment = {
        "id": "ym_idempotent_mismatch",
        "status": "pending",
        "confirmation_url": "https://yookassa.example/pay/idem-order-payload-mismatch",
    }
    monkeypatch.setattr(
        "app.api.v1.orders.YookassaPaymentService.create_payment",
        AsyncMock(return_value=payment),
    )

    r1 = await client.post(
        "/api/v1/orders/",
        json={
            "tariff_code": seed_report_tariff_and_natal["tariff_code"],
            "natal_data_id": seed_report_tariff_and_natal["natal_data_id"],
        },
        headers={**auth_headers, "Idempotency-Key": idem_key},
    )
    assert r1.status_code == 200

    r2 = await client.post(
        "/api/v1/orders/",
        json={
            "tariff_code": seed_report_tariff_and_natal["tariff_code"],
            "natal_data_id": seed_report_tariff_and_natal["natal_data_id"],
            "report_delivery_email": "different@example.com",
        },
        headers={**auth_headers, "Idempotency-Key": idem_key},
    )
    assert r2.status_code == 409
    assert "different request payload" in r2.text


@pytest.mark.asyncio
async def test_post_orders_idempotent_legacy_empty_fingerprint_allows_backward_compatible_retry(
    client: AsyncClient,
    auth_headers,
    db_session,
    seed_report_tariff_and_natal,
    monkeypatch,
    caplog,
):
    idem_key = "idem-order-legacy-empty-fingerprint"
    user_id = (await db_session.execute(select(User.id).order_by(User.id.asc()).limit(1))).scalar_one()
    caplog.set_level(logging.WARNING, logger="app.api.v1.orders")

    monkeypatch.setattr(
        "app.api.v1.orders.YookassaPaymentService.create_payment",
        AsyncMock(
            return_value={
                "id": "ym_idempotent_legacy_empty",
                "status": "pending",
                "confirmation_url": "https://yookassa.example/pay/idem-order-legacy-empty-fingerprint",
            }
        ),
    )

    row = OrderIdempotency(
        user_id=user_id,
        idempotency_key=idem_key,
        request_fingerprint="",
        state=OrderIdempotencyState.PROCESSING,
        processing_started_at=datetime.now(timezone.utc) - timedelta(minutes=10),
    )
    db_session.add(row)
    await db_session.commit()

    r = await client.post(
        "/api/v1/orders/",
        json={
            "tariff_code": seed_report_tariff_and_natal["tariff_code"],
            "natal_data_id": seed_report_tariff_and_natal["natal_data_id"],
            "report_delivery_email": "different@example.com",
        },
        headers={**auth_headers, "Idempotency-Key": idem_key},
    )
    assert r.status_code == 200
    assert "Idempotency strict payload check skipped for legacy fingerprint" in caplog.text


@pytest.mark.asyncio
async def test_post_orders_reclaims_stale_processing_lock(
    client: AsyncClient,
    auth_headers,
    db_session,
    seed_report_tariff_and_natal,
    monkeypatch,
    caplog,
):
    idem_key = "idem-order-stale-reclaim"
    caplog.set_level(logging.INFO, logger="app.api.v1.orders")
    user_id = (await db_session.execute(select(User.id).order_by(User.id.asc()).limit(1))).scalar_one()
    stale_started_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    stale_fingerprint = _build_order_request_fingerprint(
        user_id=user_id,
        tariff_code=seed_report_tariff_and_natal["tariff_code"],
        primary_natal_data_id=seed_report_tariff_and_natal["natal_data_id"],
        natal_data_ids=[seed_report_tariff_and_natal["natal_data_id"]],
        report_delivery_email=None,
    )

    monkeypatch.setattr(
        "app.api.v1.orders.YookassaPaymentService.create_payment",
        AsyncMock(
            return_value={
                "id": "ym_idempotent_reclaim",
                "status": "pending",
                "confirmation_url": "https://yookassa.example/pay/idem-order-stale-reclaim",
            }
        ),
    )

    row = OrderIdempotency(
        user_id=user_id,
        idempotency_key=idem_key,
        request_fingerprint=stale_fingerprint,
        state=OrderIdempotencyState.PROCESSING,
        processing_started_at=stale_started_at,
    )
    db_session.add(row)
    await db_session.commit()

    r = await client.post(
        "/api/v1/orders/",
        json={
            "tariff_code": seed_report_tariff_and_natal["tariff_code"],
            "natal_data_id": seed_report_tariff_and_natal["natal_data_id"],
        },
        headers={**auth_headers, "Idempotency-Key": idem_key},
    )
    assert r.status_code == 200
    assert "Idempotency stale processing lock reclaimed" in caplog.text


@pytest.mark.asyncio
async def test_post_orders_idempotency_key_too_long_returns_422(
    client: AsyncClient,
    auth_headers,
    seed_report_tariff_and_natal,
):
    too_long_key = "x" * 256
    r = await client.post(
        "/api/v1/orders/",
        json={
            "tariff_code": seed_report_tariff_and_natal["tariff_code"],
            "natal_data_id": seed_report_tariff_and_natal["natal_data_id"],
        },
        headers={**auth_headers, "Idempotency-Key": too_long_key},
    )
    assert r.status_code == 422

