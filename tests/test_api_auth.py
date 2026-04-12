from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_twa_auth_invalid_hash(client: AsyncClient):
    response = await client.post("/api/v1/auth/twa", json={"initData": "invalid"})
    assert response.status_code in (400, 401)


@pytest.mark.asyncio
async def test_apple_callback_post_form_urlencoded(client: AsyncClient, monkeypatch):
    monkeypatch.setattr("app.api.v1.auth.consume_state", AsyncMock(return_value=True))
    monkeypatch.setattr(
        "app.api.v1.auth.apple_oauth_client.get_access_token",
        AsyncMock(return_value={"id_token": "tok"}),
    )
    monkeypatch.setattr(
        "app.api.v1.auth.apple_oauth_client.get_id_email",
        AsyncMock(return_value=("apple_sub_1", "u@example.com")),
    )
    response = await client.post(
        "/api/v1/auth/apple/callback",
        data={"code": "c1", "state": "s1"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code in (302, 307)
    assert "auth/callback" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_apple_callback_post_missing_fields_returns_400(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/apple/callback",
        data={},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 400