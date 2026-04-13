"""Эндпоинты /auth/*/authorize должны отдавать HTTP-редирект на провайдера, а не URL в теле ответа."""

import pytest


@pytest.mark.parametrize(
    "path,expected_prefix",
    [
        ("/api/v1/auth/google/authorize", "https://accounts.google.com"),
        ("/api/v1/auth/yandex/authorize", "https://oauth.yandex.ru"),
    ],
)
async def test_oauth_authorize_redirects_to_provider(client, path, expected_prefix):
    r = await client.get(path, follow_redirects=False)
    assert r.status_code == 302, r.text
    loc = r.headers.get("location") or ""
    assert loc.startswith(expected_prefix)
    assert "state=" in loc


async def test_google_authorize_admin_redirects(client):
    r = await client.get("/api/v1/auth/google/authorize-admin", follow_redirects=False)
    assert r.status_code == 302, r.text
    loc = r.headers.get("location") or ""
    assert loc.startswith("https://accounts.google.com")
    assert "state=" in loc
