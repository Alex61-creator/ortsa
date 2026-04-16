from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.addon_offer_dispatch import AddonOfferDispatch
from app.models.order import Order, OrderStatus
from app.models.tariff import Tariff
from app.models.user import OAuthProvider, User


@pytest.mark.asyncio
async def test_admin_can_list_addon_offer_dispatches(client, db_session: AsyncSession):
    admin = User(
        email="admin-addon@example.com",
        external_id="admin-addon-1",
        oauth_provider=OAuthProvider.TELEGRAM,
        is_admin=True,
        consent_given_at=datetime.utcnow(),
    )
    user = User(
        email="user-addon@example.com",
        external_id="user-addon-1",
        oauth_provider=OAuthProvider.TELEGRAM,
        consent_given_at=datetime.utcnow(),
    )
    tariff = Tariff(
        code="report",
        name="Report",
        price=Decimal("100.00"),
        price_usd=Decimal("1.00"),
        features={},
        retention_days=30,
        llm_tier="natal_full",
    )
    db_session.add_all([admin, user, tariff])
    await db_session.flush()
    order = Order(
        user_id=user.id,
        natal_data_id=None,
        tariff_id=tariff.id,
        status=OrderStatus.COMPLETED,
        amount=Decimal("100.00"),
        report_delivery_email=user.email,
    )
    db_session.add(order)
    await db_session.flush()
    dispatch = AddonOfferDispatch(
        user_id=user.id,
        parent_order_id=order.id,
        addon_code="transit_month_pack",
        channel="email",
        attempt_no=1,
        scheduled_at=datetime.utcnow(),
        status="scheduled",
        dedupe_key="admin-dispatch-key",
        payload={},
    )
    db_session.add(dispatch)
    await db_session.commit()

    token = create_access_token({"sub": str(admin.id), "tv": admin.token_version})
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.get("/api/v1/admin/support/addon-offer-dispatches", headers=headers)
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) >= 1
    assert any(r["dedupe_key"] == "admin-dispatch-key" for r in rows)
