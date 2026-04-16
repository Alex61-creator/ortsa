from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.core.cache import cache
from app.core.config import settings
from app.models.natal_data import NatalData
from app.models.order import Order, OrderStatus
from app.models.order_natal_item import OrderNatalItem
from app.models.report import Report, ReportStatus
from app.models.tariff import Tariff
from app.schemas.llm import LLMResponseSchema
from app.tasks import report_generation as report_generation_module


@pytest.mark.asyncio
async def test_report_generation_marks_failed_when_pdf_generation_returns_none(
    db_session,
    test_user,
    seed_report_tariff_and_natal,
    monkeypatch,
):
    # Тариф уже есть в БД из fixtures:
    tariff_stmt = select(Tariff).where(Tariff.code == seed_report_tariff_and_natal["tariff_code"])
    tariff_db = (await db_session.execute(tariff_stmt)).scalar_one()

    order = Order(
        user_id=test_user.id,
        natal_data_id=seed_report_tariff_and_natal["natal_data_id"],
        tariff_id=tariff_db.id,
        amount=Decimal("100.00"),
        status=OrderStatus.PAID,
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    paid_at_key = f"ops:paid_at:{order.id}"
    await cache.redis.delete(paid_at_key)
    await cache.set(paid_at_key, datetime.now(timezone.utc).timestamp() - 10.0, ttl=7 * 24 * 3600)

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
        AsyncMock(return_value=None),
    )

    with pytest.raises(Exception):
        await report_generation_module._generate_report_async(order.id, task_id="test-task-1")

    order_db = (await db_session.execute(select(Order).where(Order.id == order.id))).scalar_one()
    report_db = (await db_session.execute(select(Report).where(Report.order_id == order.id))).scalar_one()
    # Фоновая логика делает коммит в другой сессии, поэтому здесь принудительно перечитываем свежие значения.
    await db_session.refresh(order_db)
    await db_session.refresh(report_db)
    assert order_db.status == OrderStatus.FAILED
    assert report_db.status == ReportStatus.FAILED

    # Guard-check сработал до записи latency-метрики; paid_at ключ должен остаться.
    assert await cache.get(paid_at_key) is not None


@pytest.mark.asyncio
async def test_report_generation_marks_failed_on_chart_step_error(
    db_session,
    test_user,
    seed_report_tariff_and_natal,
    monkeypatch,
):
    tariff_stmt = select(Tariff).where(Tariff.code == seed_report_tariff_and_natal["tariff_code"])
    tariff_db = (await db_session.execute(tariff_stmt)).scalar_one()

    order = Order(
        user_id=test_user.id,
        natal_data_id=seed_report_tariff_and_natal["natal_data_id"],
        tariff_id=tariff_db.id,
        amount=Decimal("100.00"),
        status=OrderStatus.PAID,
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    paid_at_key = f"ops:paid_at:{order.id}"
    await cache.redis.delete(paid_at_key)
    await cache.set(paid_at_key, datetime.now(timezone.utc).timestamp() - 10.0, ttl=7 * 24 * 3600)

    monkeypatch.setattr(
        report_generation_module.AstrologyService,
        "calculate_chart",
        AsyncMock(side_effect=RuntimeError("chart fail")),
    )
    monkeypatch.setattr(
        report_generation_module.LLMService,
        "generate_interpretation",
        AsyncMock(),
    )

    with pytest.raises(Exception):
        await report_generation_module._generate_report_async(order.id, task_id="test-task-1")

    order_db = (await db_session.execute(select(Order).where(Order.id == order.id))).scalar_one()
    report_db = (await db_session.execute(select(Report).where(Report.order_id == order.id))).scalar_one()
    await db_session.refresh(order_db)
    await db_session.refresh(report_db)
    assert order_db.status == OrderStatus.FAILED
    assert report_db.status == ReportStatus.FAILED
    assert await cache.get(paid_at_key) is not None


@pytest.mark.asyncio
async def test_report_generation_bundle_canonical_paths(
    db_session,
    test_user,
    seed_report_tariff_and_natal,
    monkeypatch,
):
    bundle_tariff = Tariff(
        code="bundle",
        name="Bundle",
        price=Decimal("200.00"),
        price_usd=Decimal("2.00"),
        features={"max_natal_profiles": 3},
        retention_days=30,
        llm_tier="natal_full",
    )
    db_session.add(bundle_tariff)
    await db_session.flush()

    # Primary natal data from fixture
    primary_natal_id = seed_report_tariff_and_natal["natal_data_id"]
    primary_natal = (await db_session.execute(select(NatalData).where(NatalData.id == primary_natal_id))).scalar_one()

    extra_natal = NatalData(
        user_id=test_user.id,
        full_name="Extra User",
        birth_date=datetime(1991, 2, 2, tzinfo=None),
        birth_time=datetime(1991, 2, 2, 13, 0, 0),
        birth_place="Moscow",
        lat=55.7558,
        lon=37.6173,
        timezone="Europe/Moscow",
        house_system="P",
    )
    db_session.add(extra_natal)
    await db_session.flush()

    order = Order(
        user_id=test_user.id,
        natal_data_id=primary_natal.id,
        tariff_id=bundle_tariff.id,
        amount=Decimal("200.00"),
        status=OrderStatus.PAID,
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    db_session.add(
        OrderNatalItem(
            order_id=order.id,
            natal_data_id=extra_natal.id,
            slot_index=2,
        )
    )
    await db_session.commit()

    paid_at_key = f"ops:paid_at:{order.id}"
    latencies_key = "ops:paid_completed_latencies"
    await cache.redis.delete(paid_at_key)
    await cache.redis.delete(latencies_key)
    await cache.set(paid_at_key, datetime.now(timezone.utc).timestamp() - 10.0, ttl=7 * 24 * 3600)

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

    def _fake_pdf_generate(_template_name: str, _context: dict, pdf_filename: str) -> Path:
        return Path(settings.STORAGE_DIR) / pdf_filename

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
        AsyncMock(side_effect=_fake_pdf_generate),
    )
    queued_notifications: list[int] = []

    class _FakeNotifyTask:
        @staticmethod
        def delay(order_id: int):
            queued_notifications.append(order_id)

    import sys
    fake_module = type(sys)("app.tasks.report_notifications")
    fake_module.send_report_email_task = _FakeNotifyTask()
    monkeypatch.setitem(sys.modules, "app.tasks.report_notifications", fake_module)

    await report_generation_module._generate_report_async(order.id, task_id="test-task-1")

    order_db = (await db_session.execute(select(Order).where(Order.id == order.id))).scalar_one()
    report_db = (await db_session.execute(select(Report).where(Report.order_id == order.id))).scalar_one()
    await db_session.refresh(order_db)
    await db_session.refresh(report_db)
    assert order_db.status == OrderStatus.COMPLETED
    assert report_db.status == ReportStatus.ACTIVE

    assert report_db.pdf_path.endswith(f"reports/report_{order.id}.pdf")
    assert f"charts/{order.id}_slot0_" in report_db.chart_path

    assert queued_notifications == [order.id]

