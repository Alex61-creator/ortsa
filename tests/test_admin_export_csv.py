import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
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
