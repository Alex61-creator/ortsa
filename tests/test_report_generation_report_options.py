"""LLM prompt and cache key include report_option_flags for paid report orders."""

from __future__ import annotations

import json
from datetime import datetime, timezone
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
async def test_report_generation_appends_options_to_system_prompt_and_cache_extra(
    db_session,
    test_user,
    seed_report_tariff_and_natal,
    monkeypatch,
):
    tariff_stmt = select(Tariff).where(Tariff.code == seed_report_tariff_and_natal["tariff_code"])
    tariff = (await db_session.execute(tariff_stmt)).scalar_one()

    order = Order(
        user_id=test_user.id,
        natal_data_id=seed_report_tariff_and_natal["natal_data_id"],
        tariff_id=tariff.id,
        amount=Decimal("100.00"),
        status=OrderStatus.PAID,
        report_option_flags={"partnership": True, "career": True},
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    paid_at_key = f"ops:paid_at:{order.id}"
    await cache.redis.delete(paid_at_key)
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

    mock_llm = AsyncMock(return_value=fake_interpretation)

    monkeypatch.setattr(
        report_generation_module.AstrologyService,
        "calculate_chart",
        AsyncMock(return_value=fake_chart_result),
    )
    monkeypatch.setattr(report_generation_module.LLMService, "generate_interpretation", mock_llm)
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

    class _FakeNotifyTask:
        @staticmethod
        def delay(order_id: int):
            pass

    import sys

    fake_module = type(sys)("app.tasks.report_notifications")
    fake_module.send_report_email_task = _FakeNotifyTask()
    monkeypatch.setitem(sys.modules, "app.tasks.report_notifications", fake_module)

    monkeypatch.setattr(report_generation_module, "AsyncSessionLocal", TestingSessionLocal)

    await report_generation_module._generate_report_async(order.id, task_id="test-task-ro")

    assert mock_llm.await_count >= 1
    call_kw = mock_llm.await_args.kwargs
    sp = call_kw.get("system_prompt_override") or ""
    assert "## [ПАРТНЁРСТВО]" in sp
    assert "## [КАРЬЕРА И РЕАЛИЗАЦИЯ]" in sp
    assert call_kw.get("llm_cache_extra") == json.dumps(
        {"career": True, "partnership": True}, sort_keys=True
    )
