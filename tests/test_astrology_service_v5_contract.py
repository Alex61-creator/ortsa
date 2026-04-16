from __future__ import annotations

import sys
import types
from datetime import datetime

import pytest

from app.services.astrology import AstrologyService


@pytest.mark.asyncio
async def test_calculate_chart_v5_contract(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "cairosvg",
        types.SimpleNamespace(svg2png=lambda bytestring: b"png-bytes"),
    )
    service = AstrologyService()
    result = await service.calculate_chart(
        name="Test",
        birth_date=datetime(1992, 5, 24),
        birth_time=datetime(1992, 5, 24, 14, 35),
        lat=55.7558,
        lon=37.6173,
        tz_str="Europe/Moscow",
        house_system="P",
    )

    assert isinstance(result["report"], dict)
    assert isinstance(result["svg"], str) and "<svg" in result["svg"]
    assert result["png"] == b"png-bytes"
    assert set(result["instance"].keys()) == {"planets", "houses", "angles"}
    assert isinstance(result["llm_context"], str) and result["llm_context"]


@pytest.mark.asyncio
async def test_calculate_synastry_v5_contract(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "cairosvg",
        types.SimpleNamespace(svg2png=lambda bytestring: b"png-bytes"),
    )
    service = AstrologyService()
    result = await service.calculate_synastry(
        person1={
            "name": "Person1",
            "birth_date": datetime(1992, 5, 24),
            "birth_time": datetime(1992, 5, 24, 14, 35),
            "lat": 55.7558,
            "lon": 37.6173,
            "tz_str": "Europe/Moscow",
            "house_system": "P",
        },
        person2={
            "name": "Person2",
            "birth_date": datetime(1991, 9, 10),
            "birth_time": datetime(1991, 9, 10, 8, 15),
            "lat": 59.9343,
            "lon": 30.3351,
            "tz_str": "Europe/Moscow",
            "house_system": "P",
        },
    )

    assert result["png"] == b"png-bytes"
    assert "subject1" in result and "subject2" in result
    assert isinstance(result["aspects"], list)
    assert isinstance(result["chart_data"], dict)
    assert isinstance(result["llm_context"], str) and result["llm_context"]
