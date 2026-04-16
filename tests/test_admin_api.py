from datetime import datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token
from app.models.order import Order, OrderStatus
from app.models.report import Report, ReportStatus
from app.models.tariff import Tariff
from app.models.user import OAuthProvider, User
from app.services.admin_allowlist import sync_admin_allowlist_from_env


@pytest.mark.asyncio
async def test_admin_dashboard_forbidden_for_non_admin(client: AsyncClient, auth_headers):
    r = await client.get("/api/v1/admin/dashboard/summary", headers=auth_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_dashboard_ok_for_admin(client: AsyncClient, db_session: AsyncSession):
    admin = User(
        email="adm-dash@example.com",
        external_id="adm-dash",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
        is_admin=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    token = create_access_token({"sub": str(admin.id), "tv": admin.token_version})
    r = await client.get(
        "/api/v1/admin/dashboard/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "order_metrics" in data
    assert data["analytics_stub"] is False
    assert data["business_metrics"]["users_total"] >= 1
    assert "mrr" in data["business_metrics"]
    assert "llm_cost" in data["llm_metrics"]
    assert "ai_cost_history" in data
    assert "tariff_kpis" in data


@pytest.mark.asyncio
async def test_admin_orders_list_includes_promo_and_report_options(client: AsyncClient, db_session: AsyncSession):
    admin = User(
        email="adm-ordlist@example.com",
        external_id="adm-ordlist",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
        is_admin=True,
    )
    db_session.add(admin)
    user = User(
        email="u-ordlist@example.com",
        external_id="u-ordlist",
        oauth_provider=OAuthProvider.TELEGRAM,
        consent_given_at=datetime.utcnow(),
    )
    db_session.add(user)
    tariff = Tariff(
        code="report",
        name="Отчёт",
        price=Decimal("100.00"),
        price_usd=Decimal("1.00"),
        features={"max_natal_profiles": 1},
        retention_days=30,
        llm_tier="natal_full",
        billing_type="one_time",
    )
    db_session.add(tariff)
    await db_session.flush()
    order = Order(
        user_id=user.id,
        natal_data_id=None,
        tariff_id=tariff.id,
        amount=Decimal("577.00"),
        status=OrderStatus.PAID,
        promo_code="SUMMER",
        report_option_flags={"partnership": True, "career": True},
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    token = create_access_token({"sub": str(admin.id), "tv": admin.token_version})
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.get("/api/v1/admin/orders/", headers=headers)
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    row = rows[0]
    assert row["promo_code"] == "SUMMER"
    assert row["report_option_flags"] == {"partnership": True, "career": True}
    # Default prices 199+199 with 30% multi-discount on 2+ toggles: 398 * 0.7 = 278.60
    assert float(row["report_options_line_amount"]) == pytest.approx(278.60, rel=1e-4)


@pytest.mark.asyncio
async def test_allowlist_sync_sets_is_admin(monkeypatch, db_session: AsyncSession):
    monkeypatch.setattr(settings, "ADMIN_GOOGLE_EMAILS", "boss@example.com")
    user = User(
        email="boss@example.com",
        external_id="g1",
        oauth_provider=OAuthProvider.GOOGLE,
        privacy_policy_version="1.0",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    assert user.is_admin is False
    await sync_admin_allowlist_from_env(db_session, user)
    assert user.is_admin is True


@pytest.mark.asyncio
async def test_admin_tariff_patch_does_not_change_order_amount(
    client: AsyncClient,
    db_session: AsyncSession,
):
    admin = User(
        email="adm-tar@example.com",
        external_id="adm-tar",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
        is_admin=True,
    )
    db_session.add(admin)
    user = User(
        email="u-tar@example.com",
        external_id="u-tar",
        oauth_provider=OAuthProvider.TELEGRAM,
        consent_given_at=datetime.utcnow(),
    )
    db_session.add(user)
    tariff = Tariff(
        code="report",
        name="Отчёт",
        price=Decimal("100.00"),
        price_usd=Decimal("1.00"),
        features={"max_natal_profiles": 1},
        retention_days=30,
        llm_tier="natal_full",
    )
    db_session.add(tariff)
    await db_session.flush()
    order = Order(
        user_id=user.id,
        natal_data_id=None,
        tariff_id=tariff.id,
        amount=Decimal("100.00"),
        status=OrderStatus.PAID,
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(tariff)
    await db_session.refresh(order)

    token = create_access_token({"sub": str(admin.id), "tv": admin.token_version})
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.patch(
        f"/api/v1/admin/tariffs/{tariff.id}",
        headers=headers,
        json={"price": "250.00"},
    )
    assert r.status_code == 200
    await db_session.refresh(order)
    assert order.amount == Decimal("100.00")


@pytest.mark.asyncio
@patch("app.api.v1.admin.orders.generate_report_task.delay")
async def test_admin_retry_report_daily_limit(mock_delay, client: AsyncClient, db_session: AsyncSession):
    admin = User(
        email="adm-retry@example.com",
        external_id="adm-retry",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
        is_admin=True,
    )
    db_session.add(admin)
    user = User(
        email="u-retry@example.com",
        external_id="u-retry",
        oauth_provider=OAuthProvider.TELEGRAM,
        consent_given_at=datetime.utcnow(),
    )
    db_session.add(user)
    tariff = Tariff(
        code="report",
        name="Отчёт",
        price=Decimal("100.00"),
        price_usd=Decimal("1.00"),
        features={"max_natal_profiles": 1},
        retention_days=30,
        llm_tier="natal_full",
    )
    db_session.add(tariff)
    await db_session.flush()
    order = Order(
        user_id=user.id,
        natal_data_id=None,
        tariff_id=tariff.id,
        amount=Decimal("100.00"),
        status=OrderStatus.PAID,
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    token = create_access_token({"sub": str(admin.id), "tv": admin.token_version})
    headers = {"Authorization": f"Bearer {token}"}

    for _ in range(5):
        r = await client.post(f"/api/v1/admin/orders/{order.id}/retry-report", headers=headers)
        assert r.status_code == 200, r.text

    r6 = await client.post(f"/api/v1/admin/orders/{order.id}/retry-report", headers=headers)
    assert r6.status_code == 429


@pytest.mark.asyncio
async def test_admin_report_pdf_404_when_missing(
    client: AsyncClient,
    db_session: AsyncSession,
):
    admin = User(
        email="adm-pdf@example.com",
        external_id="adm-pdf",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
        is_admin=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    token = create_access_token({"sub": str(admin.id), "tv": admin.token_version})
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.get("/api/v1/admin/reports/orders/999999/pdf", headers=headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_admin_report_pdf_ok(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch,
    tmp_path: Path,
):
    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path)
    admin = User(
        email="adm-pdf2@example.com",
        external_id="adm-pdf2",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
        is_admin=True,
    )
    db_session.add(admin)
    user = User(
        email="u-pdf@example.com",
        external_id="u-pdf",
        oauth_provider=OAuthProvider.TELEGRAM,
        consent_given_at=datetime.utcnow(),
    )
    db_session.add(user)
    tariff = Tariff(
        code="report",
        name="Отчёт",
        price=Decimal("100.00"),
        price_usd=Decimal("1.00"),
        features={"max_natal_profiles": 1},
        retention_days=30,
        llm_tier="natal_full",
    )
    db_session.add(tariff)
    await db_session.flush()
    order = Order(
        user_id=user.id,
        natal_data_id=None,
        tariff_id=tariff.id,
        amount=Decimal("100.00"),
        status=OrderStatus.COMPLETED,
    )
    db_session.add(order)
    await db_session.flush()
    rel = "reports/t1.pdf"
    (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / rel).write_bytes(b"%PDF-1.4 test")
    db_session.add(
        Report(
            order_id=order.id,
            pdf_path=rel,
            chart_path=None,
            status=ReportStatus.ACTIVE,
        )
    )
    await db_session.commit()

    token = create_access_token({"sub": str(admin.id), "tv": admin.token_version})
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.get(f"/api/v1/admin/reports/orders/{order.id}/pdf", headers=headers)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")


@pytest.mark.asyncio
async def test_admin_delete_user_forbidden_self(client: AsyncClient, db_session: AsyncSession):
    admin = User(
        email="adm-del@example.com",
        external_id="adm-del",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
        is_admin=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    token = create_access_token({"sub": str(admin.id), "tv": admin.token_version})
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.delete(f"/api/v1/admin/users/{admin.id}", headers=headers)
    assert r.status_code == 400
