from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.core.cache import cache
from app.core.config import settings
from app.models.order import Order, OrderStatus
from app.models.tariff import Tariff
from app.schemas.llm import LLMResponseSchema
from app.tasks import report_generation as report_generation_module
from tests.conftest import TestingSessionLocal


@pytest.mark.asyncio
async def test_report_generation_writes_paid_to_completed_latency(
    db_session,
    test_user,
    seed_report_tariff_and_natal,
    monkeypatch,
):
    # Arrange: seed order in PAID state + paid_at timestamp in Redis.
    tariff_stmt = select(Tariff).where(Tariff.code == seed_report_tariff_and_natal["tariff_code"])
    tariff = (await db_session.execute(tariff_stmt)).scalar_one()

    order = Order(
        user_id=test_user.id,
        natal_data_id=seed_report_tariff_and_natal["natal_data_id"],
        tariff_id=tariff.id,
        amount=Decimal("100.00"),
        status=OrderStatus.PAID,
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    paid_at_key = f"ops:paid_at:{order.id}"
    latencies_key = "ops:paid_completed_latencies"

    await cache.redis.delete(paid_at_key)
    await cache.redis.delete(latencies_key)

    paid_at_ts = datetime.now(timezone.utc).timestamp() - 10.0
    await cache.set(paid_at_key, paid_at_ts, ttl=7 * 24 * 3600)

    fake_chart_result = {
        "report": {},
        "svg": "<svg></svg>",
        "instance": {"planets": [], "houses": [], "angles": []},
        "png": b"png-bytes",
        "llm_context": "<chart_analysis></chart_analysis>",
    }
    fake_interpretation = LLMResponseSchema(
        raw_content="**Test**",
        sections={"GENERAL OVERVIEW": "hello"},
    )

    async def _fake_save_file(_: bytes, relative_path: str) -> Path:
        return Path(settings.STORAGE_DIR) / relative_path

    monkeypatch.setattr(
        report_generation_module.AstrologyService,
        "calculate_chart",
        AsyncMock(return_value=fake_chart_result),
    )
    monkeypatch.setattr(
        report_generation_module.LLMService,
        "generate_interpretation",
        AsyncMock(return_value=fake_interpretation),
    )
    monkeypatch.setattr(
        report_generation_module.StorageService,
        "save_file",
        AsyncMock(side_effect=_fake_save_file),
    )
    monkeypatch.setattr(
        report_generation_module.PDFGenerator,
        "generate",
        AsyncMock(side_effect=lambda *_args, **_kwargs: Path(settings.STORAGE_DIR) / _args[2]),
    )
    monkeypatch.setattr(
        report_generation_module.EmailService,
        "send_email",
        AsyncMock(),
    )

    # _generate_report_async uses AsyncSessionLocal directly (not FastAPI deps),
    # so for tests we must route it to the in-memory TestingSessionLocal.
    monkeypatch.setattr(report_generation_module, "AsyncSessionLocal", TestingSessionLocal)

    # Act
    await report_generation_module._generate_report_async(order.id, task_id="test-task-1")

    # Assert: order completed + latency persisted + paid_at cleared.
    order_db = (await db_session.execute(select(Order).where(Order.id == order.id))).scalar_one()
    # report_generation пишет в БД через другую сессию; обновляем ORM-объект перед проверкой.
    await db_session.refresh(order_db)
    assert order_db.status == OrderStatus.COMPLETED

    paid_at_value = await cache.get(paid_at_key)
    assert paid_at_value is None

    lat_vals_raw = await cache.redis.lrange(latencies_key, 0, 10)
    assert lat_vals_raw, "expected at least one latency sample"
    latency_seconds = float(lat_vals_raw[0])
    assert 8.0 <= latency_seconds <= 20.0

