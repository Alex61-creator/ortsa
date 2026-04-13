import redis.asyncio as redis
from typing import Optional, Any
import json
import hashlib
from app.core.config import settings

class RedisCache:
    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def get(self, key: str) -> Optional[Any]:
        data = await self.redis.get(key)
        if data:
            return json.loads(data)
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        serialized = json.dumps(value, default=str)
        if ttl:
            await self.redis.setex(key, ttl, serialized)
        else:
            await self.redis.set(key, serialized)

    async def delete(self, key: str) -> None:
        await self.redis.delete(key)

    async def exists(self, key: str) -> bool:
        return await self.redis.exists(key) > 0

    async def incr(self, key: str) -> int:
        """Атомарный INCR (счётчики лимитов; ключ без префикса cache:)."""
        return int(await self.redis.incr(key))

    async def decr(self, key: str) -> int:
        return int(await self.redis.decr(key))

    async def expire(self, key: str, seconds: int) -> None:
        await self.redis.expire(key, seconds)

    def make_key(self, prefix: str, *args, **kwargs) -> str:
        parts = [prefix]
        for arg in args:
            parts.append(str(arg))
        for k in sorted(kwargs.keys()):
            parts.append(f"{k}={kwargs[k]}")
        raw = ":".join(parts)
        return f"cache:{hashlib.md5(raw.encode()).hexdigest()}"

cache = RedisCache()