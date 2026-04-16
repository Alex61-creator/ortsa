from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy import select

from app.models.addon_offer_dispatch import AddonOfferDispatch
from app.models.feature_flag import FeatureFlag
from app.models.natal_data import NatalData
from app.models.order import Order, OrderStatus
from app.models.tariff import Tariff
from app.tasks import addon_offer_retargeting as retargeting_module
from tests.conftest import TestingSessionLocal


@pytest.mark.asyncio
async def test_schedule_addon_offer_followups_creates_email_and_push_dispatches(db_session, test_user):
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
    parent_order = Order(
        user_id=test_user.id,
        natal_data_id=natal.id,
        tariff_id=base_tariff.id,
        status=OrderStatus.COMPLETED,
        amount=Decimal("100.00"),
        report_delivery_email=test_user.email,
    )
    db_session.add(parent_order)
    await db_session.commit()
    await db_session.refresh(parent_order)

    retargeting_module.send_addon_offer_email_task.delay = Mock()
    retargeting_module.send_addon_offer_push_task.delay = Mock()
    retargeting_module.AsyncSessionLocal = TestingSessionLocal
    await retargeting_module._schedule_addon_offer_followups(
        parent_order_id=parent_order.id, user_id=test_user.id
    )

    rows = (
        await db_session.execute(
            select(AddonOfferDispatch).where(AddonOfferDispatch.parent_order_id == parent_order.id)
        )
    ).scalars().all()
    assert len(rows) == 4
    channels = sorted(r.channel for r in rows)
    assert channels == ["email", "email", "push", "push"]


@pytest.mark.asyncio
async def test_send_addon_offer_email_marks_sent(db_session, test_user):
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
    parent_order = Order(
        user_id=test_user.id,
        natal_data_id=None,
        tariff_id=base_tariff.id,
        status=OrderStatus.COMPLETED,
        amount=Decimal("100.00"),
        report_delivery_email=test_user.email,
    )
    db_session.add(parent_order)
    await db_session.flush()
    dispatch = AddonOfferDispatch(
        user_id=test_user.id,
        parent_order_id=parent_order.id,
        addon_code="transit_month_pack",
        channel="email",
        attempt_no=1,
        scheduled_at=datetime.utcnow(),
        status="scheduled",
        dedupe_key="d1",
        payload={},
    )
    db_session.add(dispatch)
    await db_session.commit()
    await db_session.refresh(dispatch)

    retargeting_module.EmailService.send_email = AsyncMock()
    retargeting_module.AsyncSessionLocal = TestingSessionLocal
    await retargeting_module._send_addon_offer_email(dispatch.id)
    async with TestingSessionLocal() as verify_session:
        refreshed = (
            await verify_session.execute(
                select(AddonOfferDispatch).where(AddonOfferDispatch.id == dispatch.id)
            )
        ).scalar_one()
    assert refreshed.status == "sent"

