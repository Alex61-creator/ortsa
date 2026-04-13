import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_live(client: AsyncClient):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_ready(client: AsyncClient):
    r = await client.get("/health/ready")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ok"
