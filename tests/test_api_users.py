import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_me_dashboard_summary(client: AsyncClient, auth_headers):
    r = await client.get("/api/v1/users/me/dashboard-summary", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert "natal_count" in body
    assert "reports_ready_count" in body
    assert "recent_orders" in body
    assert isinstance(body["natal_count"], int)


@pytest.mark.asyncio
async def test_delete_me_invalidates_access_token(client: AsyncClient, auth_headers):
    del_resp = await client.delete("/api/v1/users/me", headers=auth_headers)
    assert del_resp.status_code == 204
    me = await client.get("/api/v1/users/me", headers=auth_headers)
    assert me.status_code == 401
