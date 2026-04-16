import pytest

import app.core.feature_flags as feature_flags_module
from app.models.feature_flag import FeatureFlag
from tests.conftest import TestingSessionLocal


@pytest.mark.asyncio
async def test_report_order_options_feature_disabled(client, db_session, monkeypatch):
    monkeypatch.setattr(feature_flags_module, "AsyncSessionLocal", TestingSessionLocal)
    db_session.add(
        FeatureFlag(
            key="report_upsell_sections_enabled",
            description="upsell",
            enabled=False,
        )
    )
    await db_session.commit()

    res = await client.get("/api/v1/report-order-options/")
    assert res.status_code == 200
    body = res.json()
    assert body["feature_enabled"] is False
    assert body["options"] == []


@pytest.mark.asyncio
async def test_report_order_options_feature_enabled_defaults(client, db_session, monkeypatch):
    monkeypatch.setattr(feature_flags_module, "AsyncSessionLocal", TestingSessionLocal)
    db_session.add(
        FeatureFlag(
            key="report_upsell_sections_enabled",
            description="upsell",
            enabled=True,
        )
    )
    await db_session.commit()

    res = await client.get("/api/v1/report-order-options/")
    assert res.status_code == 200
    body = res.json()
    assert body["feature_enabled"] is True
    assert body["multi_discount_percent"] == 30
    assert len(body["options"]) == 4
    keys = {o["key"] for o in body["options"]}
    assert keys == {"partnership", "children_parenting", "career", "money_boundaries"}
    for o in body["options"]:
        assert o["title"]
        assert len(o["description"]) > 10
        assert o["price"] == "199.00"
        assert o["currency"] == "RUB"
