from datetime import datetime
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.analytics_event import AnalyticsEvent
from app.models.user import OAuthProvider, User


async def _admin_headers(db_session: AsyncSession) -> dict[str, str]:
    admin = User(
        email="adm-acc-cost@example.com",
        external_id="adm-acc-cost",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
        is_admin=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    token = create_access_token({"sub": str(admin.id), "tv": admin.token_version})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_acquisition_cost_recorded_emitted(
    client: AsyncClient,
    db_session: AsyncSession,
):
    headers = await _admin_headers(db_session)

    period_start = datetime.utcnow().isoformat()
    period_end = datetime.utcnow().isoformat()
    channel = "tg_ads"
    spend_amount = Decimal("1000.00")

    resp = await client.post(
        "/api/v1/admin/metrics/spend",
        headers=headers,
        json={
            "period_start": period_start,
            "period_end": period_end,
            "channel": channel,
            "campaign_name": "camp1",
            "spend_amount": str(spend_amount),
            "currency": "RUB",
            "notes": "test",
        },
    )
    assert resp.status_code == 200

    rows = (
        await db_session.execute(
            select(AnalyticsEvent).where(AnalyticsEvent.event_name == "acquisition_cost_recorded")
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].source_channel == channel
    assert rows[0].amount == spend_amount
    assert rows[0].dedupe_key is not None

