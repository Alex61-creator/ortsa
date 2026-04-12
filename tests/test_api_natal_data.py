import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_natal_data(client: AsyncClient, auth_headers):
    payload = {
        "full_name": "Test User",
        "birth_date": "1990-01-01T00:00:00",
        "birth_time": "1990-01-01T12:00:00",
        "birth_place": "Moscow",
        "lat": 55.7558,
        "lon": 37.6173,
        "timezone": "Europe/Moscow",
        "house_system": "P",
        "accept_privacy_policy": True,
    }
    response = await client.post("/api/v1/natal-data/", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Test User"
    assert data.get("report_locale") == "ru"


@pytest.mark.asyncio
async def test_create_natal_data_report_locale_en(client: AsyncClient, auth_headers):
    payload = {
        "full_name": "Test User",
        "birth_date": "1990-01-01T00:00:00",
        "birth_time": "1990-01-01T12:00:00",
        "birth_place": "Moscow",
        "lat": 55.7558,
        "lon": 37.6173,
        "timezone": "Europe/Moscow",
        "house_system": "P",
        "accept_privacy_policy": True,
        "report_locale": "en",
    }
    response = await client.post("/api/v1/natal-data/", json=payload, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["report_locale"] == "en"