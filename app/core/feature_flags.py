from app.core.cache import cache

class FeatureFlags:
    @staticmethod
    async def is_enabled(flag_name: str, default: bool = True) -> bool:
        value = await cache.get(f"feature:{flag_name}")
        if value is None:
            return default
        return value == "true"

    @staticmethod
    async def set_flag(flag_name: str, enabled: bool):
        await cache.set(f"feature:{flag_name}", "true" if enabled else "false")