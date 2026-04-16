from datetime import datetime

import pytest

import app.core.feature_flags as feature_flags_module
from app.core.cache import cache
from app.core.feature_flags import FeatureFlags
from app.core.security import create_access_token
from app.models.user import OAuthProvider, User
from tests.conftest import TestingSessionLocal


@pytest.mark.asyncio
async def test_feature_flags_persist_after_flushdb_via_admin_api(client, db_session, monkeypatch):
    # Ensure FeatureFlags uses the in-memory test DB session.
    monkeypatch.setattr(feature_flags_module, "AsyncSessionLocal", TestingSessionLocal)

    admin = User(
        email="adm-flags@example.com",
        external_id="adm-flags",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
        is_admin=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    token = create_access_token({"sub": str(admin.id), "tv": admin.token_version})
    headers = {"Authorization": f"Bearer {token}"}

    # Toggle via admin-API write path (DB write + Redis reflection).
    r = await client.patch(
        "/api/v1/admin/flags/admin_funnel_enabled",
        headers=headers,
        json={"enabled": True, "reason": "test"},
    )
    assert r.status_code == 200
    assert r.json()["enabled"] is True

    # Clear Redis: runtime must still resolve from DB.
    await cache.redis.flushdb()

    enabled = await FeatureFlags.is_enabled("admin_funnel_enabled", default=False)
    assert enabled is True

