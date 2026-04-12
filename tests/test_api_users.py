import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_delete_me_invalidates_access_token(client: AsyncClient, auth_headers):
    del_resp = await client.delete("/api/v1/users/me", headers=auth_headers)
    assert del_resp.status_code == 204
    me = await client.get("/api/v1/users/me", headers=auth_headers)
    assert me.status_code == 401
