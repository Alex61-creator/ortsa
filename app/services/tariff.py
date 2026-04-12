from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.tariff import Tariff
from app.core.cache import cache

TARIFF_CACHE_KEY = "tariffs:v2:config"
TARIFF_CACHE_TTL = 24 * 3600

class TariffService:
    @staticmethod
    async def get_by_code(db: AsyncSession, code: str) -> Optional[Tariff]:
        cache_key = f"{TARIFF_CACHE_KEY}:{code}"
        cached = await cache.get(cache_key)
        if cached:
            return Tariff(**cached)

        stmt = select(Tariff).where(Tariff.code == code)
        result = await db.execute(stmt)
        tariff = result.scalar_one_or_none()
        if tariff:
            tariff_dict = {c.name: getattr(tariff, c.name) for c in tariff.__table__.columns}
            await cache.set(cache_key, tariff_dict, TARIFF_CACHE_TTL)
        return tariff

    @staticmethod
    async def get_all(db: AsyncSession) -> list[Tariff]:
        cache_key = f"{TARIFF_CACHE_KEY}:all"
        cached = await cache.get(cache_key)
        if cached:
            return [Tariff(**item) for item in cached]

        stmt = select(Tariff)
        result = await db.execute(stmt)
        tariffs = result.scalars().all()
        if tariffs:
            tariffs_list = [{c.name: getattr(t, c.name) for c in t.__table__.columns} for t in tariffs]
            await cache.set(cache_key, tariffs_list, TARIFF_CACHE_TTL)
        return tariffs

    @staticmethod
    async def invalidate_cache():
        async for key in cache.redis.scan_iter(match=f"{TARIFF_CACHE_KEY}*"):
            await cache.delete(key)