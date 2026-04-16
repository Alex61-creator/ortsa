from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.order import Order, OrderStatus
from app.models.natal_data import NatalData
from app.models.report import Report, ReportStatus
from app.models.synastry_report import SynastryReport, SynastryStatus
from app.models.tariff import Tariff
from app.services.storage import StorageService
import app.tasks.cleanup as cleanup_module
from tests.conftest import TestingSessionLocal


@pytest.mark.asyncio
async def test_reports_download_works_with_relative_pdf_path(
    client,
    db_session,
    test_user,
    auth_headers,
    seed_report_tariff_and_natal,
):
    tariff_stmt = select(Tariff).where(Tariff.code == seed_report_tariff_and_natal["tariff_code"])
    tariff = (await db_session.execute(tariff_stmt)).scalar_one()

    order = Order(
        user_id=test_user.id,
        natal_data_id=seed_report_tariff_and_natal["natal_data_id"],
        tariff_id=tariff.id,
        amount=Decimal("100.00"),
        status=OrderStatus.COMPLETED,
    )
    db_session.add(order)
    await db_session.flush()

    storage = StorageService()
    rel_pdf = f"reports/report_{order.id}.pdf"
    await storage.save_file(b"%PDF-1.4 test", rel_pdf)

    report = Report(
        order_id=order.id,
        pdf_path=rel_pdf,
        chart_path=None,
        status=ReportStatus.ACTIVE,
        generated_at=datetime.now(timezone.utc),
    )
    db_session.add(report)
    await db_session.commit()

    resp = await client.get(f"/api/v1/reports/{order.id}/download", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.headers.get("content-type", "").startswith("application/pdf")


@pytest.mark.asyncio
async def test_cleanup_archives_expired_report_and_deletes_files(
    db_session,
    test_user,
    seed_report_tariff_and_natal,
):
    tariff_stmt = select(Tariff).where(Tariff.code == "free")
    tariff = (await db_session.execute(tariff_stmt)).scalar_one_or_none()
    if tariff is None:
        tariff = Tariff(
            code="free",
            name="Free",
            price=Decimal("0.00"),
            price_usd=Decimal("0.00"),
            features={"max_natal_profiles": 1},
            retention_days=3,
            llm_tier="free",
        )
        db_session.add(tariff)
        await db_session.flush()
    else:
        tariff.retention_days = 3

    order = Order(
        user_id=test_user.id,
        natal_data_id=seed_report_tariff_and_natal["natal_data_id"],
        tariff_id=tariff.id,
        amount=Decimal("0.00"),
        status=OrderStatus.COMPLETED,
    )
    db_session.add(order)
    await db_session.flush()

    storage = StorageService()
    rel_pdf = f"reports/report_{order.id}.pdf"
    rel_chart = f"charts/{order.id}_slot0_test.png"
    await storage.save_file(b"pdf-data", rel_pdf)
    await storage.save_file(b"png-data", rel_chart)

    report = Report(
        order_id=order.id,
        pdf_path=rel_pdf,
        chart_path=rel_chart,
        status=ReportStatus.ACTIVE,
        generated_at=datetime.now(timezone.utc) - timedelta(days=5),
    )
    db_session.add(report)
    await db_session.commit()

    cleanup_module.AsyncSessionLocal = TestingSessionLocal
    result = await cleanup_module._cleanup_storage_async()
    assert result["archived_reports"] >= 1

    await db_session.refresh(report)
    assert report.status == ReportStatus.ARCHIVED
    assert report.pdf_path is None
    assert report.chart_path is None
    assert not (Path(settings.STORAGE_DIR) / rel_pdf).exists()
    assert not (Path(settings.STORAGE_DIR) / rel_chart).exists()


@pytest.mark.asyncio
async def test_cleanup_archives_expired_synastry_and_deletes_files(
    db_session,
    test_user,
    seed_report_tariff_and_natal,
):
    nd1 = (
        await db_session.execute(
            select(NatalData).where(NatalData.id == seed_report_tariff_and_natal["natal_data_id"])
        )
    ).scalar_one()
    nd2 = NatalData(
        user_id=test_user.id,
        full_name="Partner User",
        birth_date=datetime(1992, 3, 3),
        birth_time=datetime(1992, 3, 3, 11, 0, 0),
        birth_place="Moscow",
        lat=55.7558,
        lon=37.6173,
        timezone="Europe/Moscow",
        house_system="P",
    )
    db_session.add(nd2)
    await db_session.flush()

    storage = StorageService()
    rel_pdf = "reports/synastry_1.pdf"
    rel_chart = "charts/synastry_1.png"
    await storage.save_file(b"synastry-pdf", rel_pdf)
    await storage.save_file(b"synastry-png", rel_chart)

    syn = SynastryReport(
        user_id=test_user.id,
        natal_data_id_1=min(nd1.id, nd2.id),
        natal_data_id_2=max(nd1.id, nd2.id),
        status=SynastryStatus.COMPLETED,
        locale="ru",
        pdf_path=rel_pdf,
        chart_path=rel_chart,
        retention_days=3,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(syn)
    await db_session.commit()

    cleanup_module.AsyncSessionLocal = TestingSessionLocal
    result = await cleanup_module._cleanup_storage_async()
    assert result["archived_synastry"] >= 1

    await db_session.refresh(syn)
    assert syn.status == SynastryStatus.ARCHIVED
    assert syn.pdf_path is None
    assert syn.chart_path is None
    assert not (Path(settings.STORAGE_DIR) / rel_pdf).exists()
    assert not (Path(settings.STORAGE_DIR) / rel_chart).exists()
