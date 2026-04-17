import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.order import Order, OrderStatus
from app.models.tariff import Tariff
from app.models.user import OAuthProvider, User


@pytest.mark.asyncio
async def test_admin_export_orders_csv_ok(client: AsyncClient, db_session: AsyncSession):
    admin = User(
        email="adm-csv@example.com",
        external_id="adm-csv",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=__import__("datetime").datetime.utcnow(),
        is_admin=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    token = create_access_token({"sub": str(admin.id), "tv": admin.token_version})
    r = await client.get(
        "/api/v1/admin/export/orders.csv",
        headers={"Authorization": f"Bearer {token}"},
        params={"excel_bom": "1", "limit": "10"},
    )
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("text/csv")
    body = r.content
    assert body.startswith(b"\xef\xbb\xbf") or body.startswith(b"id")


@pytest.mark.asyncio
async def test_admin_export_campaign_csv_ok(client: AsyncClient, db_session: AsyncSession):
    admin = User(
        email="adm-csv2@example.com",
        external_id="adm-csv2",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=__import__("datetime").datetime.utcnow(),
        is_admin=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    token = create_access_token({"sub": str(admin.id), "tv": admin.token_version})
    r = await client.get(
        "/api/v1/admin/export/campaign-performance.csv",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert "segment_key" in r.text


@pytest.mark.asyncio
async def test_admin_order_timeline_csv_ok(client: AsyncClient, db_session: AsyncSession):
    import datetime

    admin = User(
        email="adm-tl-csv@example.com",
        external_id="adm-tl-csv",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.datetime.utcnow(),
        is_admin=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)

    tariff = Tariff(
        code="report-tl-test",
        name="Report",
        billing_type="one_time",
        price=990,
        features={},
        retention_days=365,
    )
    db_session.add(tariff)
    await db_session.commit()
    await db_session.refresh(tariff)

    order = Order(
        user_id=admin.id,
        tariff_id=tariff.id,
        status=OrderStatus.COMPLETED,
        amount=990,
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    token = create_access_token({"sub": str(admin.id), "tv": admin.token_version})
    r = await client.get(
        f"/api/v1/admin/orders/{order.id}/timeline.csv",
        headers={"Authorization": f"Bearer {token}"},
        params={"excel_bom": "1"},
    )
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("text/csv")
    assert "content-disposition" in r.headers
    body = r.content
    assert body.startswith(b"\xef\xbb\xbf") or b"time_utc" in body


@pytest.mark.asyncio
async def test_admin_export_redemptions_csv_ok(client: AsyncClient, db_session: AsyncSession):
    import datetime

    admin = User(
        email="adm-red-csv@example.com",
        external_id="adm-red-csv",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.datetime.utcnow(),
        is_admin=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    token = create_access_token({"sub": str(admin.id), "tv": admin.token_version})
    r = await client.get(
        "/api/v1/admin/export/promocode-redemptions.csv",
        headers={"Authorization": f"Bearer {token}"},
        params={"limit": "10"},
    )
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("text/csv")
    assert b"id" in r.content or b"\xef\xbb\xbf" in r.content


@pytest.mark.asyncio
async def test_admin_order_timeline_csv_not_found(client: AsyncClient, db_session: AsyncSession):
    import datetime

    admin = User(
        email="adm-tl-404@example.com",
        external_id="adm-tl-404",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.datetime.utcnow(),
        is_admin=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    token = create_access_token({"sub": str(admin.id), "tv": admin.token_version})
    r = await client.get(
        "/api/v1/admin/orders/999999/timeline.csv",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404
