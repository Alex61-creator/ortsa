"""
LLM-сервис для генерации интерпретации синастрии.

Поддерживает DeepSeek, Grok (OpenAI-compatible) и Claude (Anthropic SDK).
Использует llm_router для автоматического failover с circuit breaker.
Проверяет структуру и язык ответа через llm_validator (1 повтор при фейле).
Пишет LlmUsageLog в БД после каждого успешного LLM-вызова.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from decimal import Decimal

import structlog

from app.core.cache import cache
from app.core.config import settings
from app.schemas.llm import LLMResponseSchema
from app.services.llm_client import LLMProvider
from app.services.llm import _call_api, _compute_cost, _write_usage_log  # переиспользуем хелперы
from app.services.llm_router import call_with_fallback
from app.services.llm_validator import (
    LLMValidationError,
    validate_response,
    language_enforcement_suffix,
)
from app.constants.tariffs import LlmTier

logger = structlog.get_logger(__name__)

SYNASTRY_CACHE_PREFIX = "synastry_llm:v2"

# ── Промпты ───────────────────────────────────────────────────────────────────

SYNASTRY_SYSTEM_PROMPT_RU = """
Ты — профессиональный астролог с 20-летним опытом в синастрии.
Составь подробный анализ совместности двух людей на основе их натальных карт и аспектов синастрии.
Используй только предоставленные данные. Отвечай строго по структуре, используя маркеры разделов.

## [ОБЩАЯ СОВМЕСТНОСТЬ]
## [ЭМОЦИОНАЛЬНАЯ СВЯЗЬ]
## [ИНТЕЛЛЕКТУАЛЬНАЯ СОВМЕСТИМОСТЬ]
## [РОМАНТИКА И ПРИТЯЖЕНИЕ]
## [КОНФЛИКТЫ И ВЫЗОВЫ]
## [ДОЛГОСРОЧНЫЙ ПОТЕНЦИАЛ]
## [КЛЮЧЕВЫЕ АСПЕКТЫ СИНАСТРИИ]
## [РЕКОМЕНДАЦИИ ДЛЯ ПАРТНЁРОВ]
"""

SYNASTRY_SYSTEM_PROMPT_EN = """
You are a professional astrologer with 20 years of experience in synastry.
Write a detailed compatibility analysis for two people based on their natal charts and synastry aspects.
Use only the provided data. Follow the structure strictly and use these section markers.

## [OVERALL COMPATIBILITY]
## [EMOTIONAL CONNECTION]
## [INTELLECTUAL COMPATIBILITY]
## [ROMANCE & ATTRACTION]
## [CONFLICTS & CHALLENGES]
## [LONG-TERM POTENTIAL]
## [KEY SYNASTRY ASPECTS]
## [RECOMMENDATIONS FOR PARTNERS]
"""


def build_synastry_system_prompt(locale: str = "ru") -> str:
    if locale == "en":
        return SYNASTRY_SYSTEM_PROMPT_EN
    return SYNASTRY_SYSTEM_PROMPT_RU


def build_synastry_user_prompt(
    person1_name: str,
    person2_name: str,
    chart_data: dict,
    locale: str = "ru",
    chart_context: str | None = None,
) -> str:
    if chart_context:
        if locale == "en":
            return (
                f"Synastry analysis for:\n"
                f"  Person 1: {person1_name}\n"
                f"  Person 2: {person2_name}\n\n"
                f"Kerykeion structured context (XML):\n{chart_context}\n\n"
                "Write the entire analysis in clear, fluent English."
            )
        return (
            f"Синастрия (совместность) двух людей:\n"
            f"  Человек 1: {person1_name}\n"
            f"  Человек 2: {person2_name}\n\n"
            f"Структурированный контекст Kerykeion (XML):\n{chart_context}"
        )

    if locale == "en":
        return (
            f"Synastry analysis for:\n"
            f"  Person 1: {person1_name}\n"
            f"  Person 2: {person2_name}\n\n"
            f"Chart data:\n{json.dumps(chart_data, indent=2, ensure_ascii=False)}\n\n"
            "Write the entire analysis in clear, fluent English."
        )
    return (
        f"Синастрия (совместность) двух людей:\n"
        f"  Человек 1: {person1_name}\n"
        f"  Человек 2: {person2_name}\n\n"
        f"Данные карт и аспекты:\n{json.dumps(chart_data, indent=2, ensure_ascii=False)}"
    )


def make_synastry_cache_key(chart_data: dict, locale: str = "ru") -> str:
    raw = json.dumps({"chart": chart_data, "locale": locale}, sort_keys=True)
    return f"{SYNASTRY_CACHE_PREFIX}:{hashlib.sha256(raw.encode()).hexdigest()}"


# ── Основной сервис ───────────────────────────────────────────────────────────

class SynastryLLMService:
    """Генерация интерпретации синастрии с multi-provider failover."""

    async def generate_synastry_interpretation(
        self,
        person1_name: str,
        person2_name: str,
        chart_data: dict,
        locale: str = "ru",
        system_prompt_override: str | None = None,
        chart_context: str | None = None,
        *,
        user_id: int | None = None,
        synastry_id: int | None = None,
    ) -> tuple[LLMResponseSchema, LLMProvider]:
        """Генерирует интерпретацию синастрии с multi-provider failover.

        Returns:
            (LLMResponseSchema, LLMProvider) — схема ответа и провайдер.
        """
        if locale not in ("ru", "en"):
            locale = "ru"

        cache_key = make_synastry_cache_key(chart_data, locale)

        # ── Cache hit ─────────────────────────────────────────────────────────
        cached = await cache.get(cache_key)
        if cached:
            logger.info("Synastry LLM cache hit", locale=locale)
            if "response" in cached and "provider" in cached:
                cached_provider = LLMProvider(cached.get("provider", LLMProvider.DEEPSEEK.value))
                return LLMResponseSchema(**cached["response"]), cached_provider
            # Старый формат v1
            return LLMResponseSchema(**cached), LLMProvider.DEEPSEEK

        # ── Подготовка промптов ───────────────────────────────────────────────
        system_prompt = system_prompt_override or build_synastry_system_prompt(locale)
        user_prompt = build_synastry_user_prompt(
            person1_name, person2_name, chart_data, locale, chart_context=chart_context
        )
        max_tokens = settings.LLM_MAX_TOKENS_PRO

        # ── Closure для router ────────────────────────────────────────────────
        async def _fn(provider: LLMProvider) -> tuple[LLMResponseSchema, dict]:
            response, usage = await _call_api(provider, system_prompt, user_prompt, max_tokens)

            try:
                # Синастрия — особый тип: is_synastry=True
                validate_response(response, LlmTier.PRO, locale, is_synastry=True)
            except LLMValidationError as first_err:
                logger.warning(
                    "Synastry LLM validation failed, retrying",
                    provider=provider.value,
                    error=str(first_err),
                )
                enhanced_prompt = user_prompt + language_enforcement_suffix(locale)
                response, usage = await _call_api(provider, system_prompt, enhanced_prompt, max_tokens)
                validate_response(response, LlmTier.PRO, locale, is_synastry=True)

            logger.info(
                "Synastry LLM tokens used",
                provider=provider.value,
                prompt_tokens=usage["prompt_tokens"],
                completion_tokens=usage["completion_tokens"],
                cached_tokens=usage["cached_tokens"],
            )
            return response, usage

        # ── Вызов с failover ──────────────────────────────────────────────────
        (response, usage), provider_used = await call_with_fallback(
            _fn,
            validation_error_cls=LLMValidationError,
        )

        # ── Кеш ──────────────────────────────────────────────────────────────
        await cache.set(
            cache_key,
            {"provider": provider_used.value, "response": response.model_dump()},
            ttl=90 * 24 * 3600,
        )

        # ── LlmUsageLog (fire-and-forget) ─────────────────────────────────────
        cost_usd, cost_rub = _compute_cost(provider_used, usage)
        if user_id is not None:
            asyncio.ensure_future(
                _write_usage_log(user_id, synastry_id, provider_used, usage, cost_usd, cost_rub)
            )

        return response, provider_used
