from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.models.analytics_event import AnalyticsEvent
from app.models.order import Order, OrderStatus
from app.models.tariff import Tariff
from app.schemas.llm import LLMResponseSchema
from app.tasks import report_generation as report_generation_module
from tests.conftest import TestingSessionLocal


@pytest.mark.asyncio
async def test_order_completed_event_has_cost_components_and_correlation(
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
        yookassa_id="pay_cost_components_1",
        variable_cost_amount=Decimal("1.23"),
        payment_fee_amount=Decimal("4.56"),
        ai_cost_amount=Decimal("0.78"),
        infra_cost_amount=Decimal("9.10"),
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

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
        return Path(report_generation_module.settings.STORAGE_DIR) / relative_path

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
        AsyncMock(side_effect=lambda *_args, **_kwargs: Path(report_generation_module.settings.STORAGE_DIR) / _args[2]),
    )
    monkeypatch.setattr(
        report_generation_module.EmailService,
        "send_email",
        AsyncMock(),
    )

    monkeypatch.setattr(report_generation_module, "AsyncSessionLocal", TestingSessionLocal)

    # Run report generation, which should emit analytics_events.order_completed.
    await report_generation_module._generate_report_async(order.id, task_id="test-task-cc-1")

    row = (
        await db_session.execute(
            select(AnalyticsEvent).where(
                AnalyticsEvent.event_name == "order_completed", AnalyticsEvent.order_id == order.id
            )
        )
    ).scalars().one()

    assert row.dedupe_key == f"order_completed:{order.id}"
    assert row.correlation_id == "pay_cost_components_1"
    assert row.cost_components is not None
    assert row.cost_components["variable_cost_amount"] == pytest.approx(1.23)
    assert row.cost_components["payment_fee_amount"] == pytest.approx(4.56)
    assert row.cost_components["ai_cost_amount"] == pytest.approx(0.78)
    assert row.cost_components["infra_cost_amount"] == pytest.approx(9.10)

