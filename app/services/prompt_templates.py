from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
from app.models.prompt_template import LlmPromptTemplate

PROMPT_TEMPLATE_CACHE_PREFIX = "prompt_template:v2"
PROMPT_TEMPLATE_CACHE_TTL = 3600


def _prompt_key(tariff_code: str, locale: str, provider: str | None = None) -> str:
    provider_part = provider or "any"
    return f"{PROMPT_TEMPLATE_CACHE_PREFIX}:{tariff_code}:{locale}:{provider_part}"


class PromptTemplateService:
    @staticmethod
    async def get_system_prompt(
        db: AsyncSession,
        tariff_code: str,
        locale: str,
        provider: str | None = None,
    ) -> str | None:
        """Ищет системный промпт в порядке:
        1. (tariff_code, locale, provider)  — если provider задан
        2. (tariff_code, locale, NULL)       — общий для всех провайдеров
        3. None                              — использовать хардкод из LLMService
        """
        cache_key = _prompt_key(tariff_code, locale, provider)
        cached = await cache.get(cache_key)
        if cached is not None:
            return cached.get("system_prompt")

        system_prompt: str | None = None

        # 1) Ищем провайдер-специфичный шаблон
        if provider:
            stmt = select(LlmPromptTemplate).where(
                LlmPromptTemplate.tariff_code == tariff_code,
                LlmPromptTemplate.locale == locale,
                LlmPromptTemplate.llm_provider == provider,
            )
            result = await db.execute(stmt)
            rec = result.scalar_one_or_none()
            if rec:
                system_prompt = rec.system_prompt

        # 2) Fallback: шаблон с llm_provider=NULL (для всех провайдеров)
        if system_prompt is None:
            stmt = select(LlmPromptTemplate).where(
                LlmPromptTemplate.tariff_code == tariff_code,
                LlmPromptTemplate.locale == locale,
                LlmPromptTemplate.llm_provider.is_(None),
            )
            result = await db.execute(stmt)
            rec = result.scalar_one_or_none()
            if rec:
                system_prompt = rec.system_prompt

        payload = {"system_prompt": system_prompt}
        await cache.set(cache_key, payload, PROMPT_TEMPLATE_CACHE_TTL)
        return system_prompt

    @staticmethod
    async def invalidate(
        tariff_code: str,
        locale: str,
        provider: str | None = None,
    ) -> None:
        """Инвалидирует кеш для шаблона.
        Если provider=None — инвалидирует общий кеш (any).
        """
        await cache.delete(_prompt_key(tariff_code, locale, provider))
        # Также инвалидируем общий ключ (any), т.к. он мог закешировать NULL-шаблон
        if provider is not None:
            await cache.delete(_prompt_key(tariff_code, locale, None))
