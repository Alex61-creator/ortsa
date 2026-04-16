from datetime import datetime

import pytest

import app.core.feature_flags as feature_flags_module
from app.core.cache import cache
from app.core.feature_flags import FeatureFlags
from app.models.feature_flag import FeatureFlag
from tests.conftest import TestingSessionLocal


@pytest.mark.asyncio
async def test_feature_flags_read_through_cache_miss(db_session, monkeypatch):
    # Ensure FeatureFlags uses the in-memory test DB session.
    monkeypatch.setattr(feature_flags_module, "AsyncSessionLocal", TestingSessionLocal)

    flag = FeatureFlag(key="admin_funnel_enabled", description="Enable funnel", enabled=True)
    db_session.add(flag)
    await db_session.commit()
    await db_session.refresh(flag)

    await cache.redis.flushdb()
    assert await cache.get("feature:admin_funnel_enabled") is None

    enabled = await FeatureFlags.is_enabled("admin_funnel_enabled", default=False)
    assert enabled is True

    # FeatureFlags should reflect the value into cache on miss.
    cached = await cache.get("feature:admin_funnel_enabled")
    assert cached in ("true", True)

