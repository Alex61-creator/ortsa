from app.core.cache import cache
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.feature_flag import FeatureFlag


class FeatureFlags:
    @staticmethod
    async def is_enabled(flag_name: str, default: bool = True) -> bool:
        value = await cache.get(f"feature:{flag_name}")
        # Fast path: cache hit
        if value is not None:
            if isinstance(value, bool):
                return value
            return str(value).lower() == "true"

        # Cache miss: DB-backed read-through (DB source-of-truth for ops)
        async with AsyncSessionLocal() as db:
            row = await db.execute(select(FeatureFlag).where(FeatureFlag.key == flag_name))
            flag = row.scalar_one_or_none()

        enabled = flag.enabled if flag is not None else default
        # Keep Redis payload consistent with existing admin/flags implementation.
        await cache.set(f"feature:{flag_name}", "true" if enabled else "false")
        return enabled

    @staticmethod
    async def set_flag(flag_name: str, enabled: bool):
        await cache.set(f"feature:{flag_name}", "true" if enabled else "false")