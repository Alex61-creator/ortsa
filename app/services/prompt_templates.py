from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
from app.models.prompt_template import LlmPromptTemplate

PROMPT_TEMPLATE_CACHE_PREFIX = "prompt_template:v1"
PROMPT_TEMPLATE_CACHE_TTL = 3600


def _prompt_key(tariff_code: str, locale: str) -> str:
    return f"{PROMPT_TEMPLATE_CACHE_PREFIX}:{tariff_code}:{locale}"


class PromptTemplateService:
    @staticmethod
    async def get_system_prompt(
        db: AsyncSession,
        tariff_code: str,
        locale: str,
    ) -> str | None:
        key = _prompt_key(tariff_code, locale)
        cached = await cache.get(key)
        if cached is not None:
            return cached.get("system_prompt")

        stmt = select(LlmPromptTemplate).where(
            LlmPromptTemplate.tariff_code == tariff_code,
            LlmPromptTemplate.locale == locale,
        )
        result = await db.execute(stmt)
        rec = result.scalar_one_or_none()
        payload = {"system_prompt": rec.system_prompt if rec else None}
        await cache.set(key, payload, PROMPT_TEMPLATE_CACHE_TTL)
        return payload["system_prompt"]

    @staticmethod
    async def invalidate(tariff_code: str, locale: str) -> None:
        await cache.delete(_prompt_key(tariff_code, locale))
