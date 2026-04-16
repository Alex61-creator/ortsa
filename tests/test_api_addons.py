from datetime import datetime
from decimal import Decimal

import pytest

from app.models.feature_flag import FeatureFlag
from app.models.natal_data import NatalData
from app.models.order import Order, OrderStatus
from app.models.tariff import Tariff


@pytest.mark.asyncio
async def test_addons_list_shows_eligibility_when_enabled(client, db_session, test_user, auth_headers):
    base_tariff = Tariff(
        code="report",
        name="Report",
        price=Decimal("100.00"),
        price_usd=Decimal("1.00"),
        features={},
        retention_days=30,
        llm_tier="natal_full",
    )
    addon_tariff = Tariff(
        code="transit_month_pack",
        name="Transit month pack",
        price=Decimal("590.00"),
        price_usd=Decimal("7.00"),
        features={
            "is_addon": True,
            "addon_requires_tariff_codes": ["report"],
            "addon_offer_ttl_hours": 72,
            "addon_repeat_limit": 1,
        },
        retention_days=30,
        llm_tier="natal_full",
    )
    db_session.add_all(
        [
            base_tariff,
            addon_tariff,
            FeatureFlag(key="addons_enabled", description="addons", enabled=True),
        ]
    )
    await db_session.flush()

    natal = NatalData(
        user_id=test_user.id,
        full_name="Test User",
        birth_date=datetime(1990, 1, 1),
        birth_time=datetime(1990, 1, 1, 12, 0),
        birth_place="Moscow",
        lat=55.7,
        lon=37.6,
        timezone="Europe/Moscow",
        house_system="P",
    )
    db_session.add(natal)
    await db_session.flush()
    db_session.add(
        Order(
            user_id=test_user.id,
            natal_data_id=natal.id,
            tariff_id=base_tariff.id,
            status=OrderStatus.COMPLETED,
            amount=Decimal("100.00"),
            report_delivery_email=test_user.email,
        )
    )
    await db_session.commit()

    res = await client.get("/api/v1/addons", headers=auth_headers)
    assert res.status_code == 200
    payload = res.json()
    assert len(payload) == 1
    assert payload[0]["addon_code"] == "transit_month_pack"
    assert payload[0]["eligible"] is True


@pytest.mark.asyncio
async def test_addon_purchase_blocked_when_global_flag_off(client, db_session, test_user, auth_headers):
    base_tariff = Tariff(
        code="report",
        name="Report",
        price=Decimal("100.00"),
        price_usd=Decimal("1.00"),
        features={},
        retention_days=30,
        llm_tier="natal_full",
    )
    addon_tariff = Tariff(
        code="transit_month_pack",
        name="Transit month pack",
        price=Decimal("590.00"),
        price_usd=Decimal("7.00"),
        features={
            "is_addon": True,
            "addon_requires_tariff_codes": ["report"],
            "addon_offer_ttl_hours": 72,
            "addon_repeat_limit": 1,
        },
        retention_days=30,
        llm_tier="natal_full",
    )
    db_session.add_all(
        [
            base_tariff,
            addon_tariff,
            FeatureFlag(key="addons_enabled", description="addons", enabled=False),
        ]
    )
    await db_session.commit()

    res = await client.post("/api/v1/addons/transit_month_pack/purchase", headers=auth_headers)
    assert res.status_code == 422
    detail = res.json()["detail"]
    assert detail["code"] == "ADDONS_DISABLED"
