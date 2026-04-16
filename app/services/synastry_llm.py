"""
LLM-сервис для генерации интерпретации синастрии.

Использует тот же DeepSeek клиент, что и LLMService,
но со своими промптами и разделами.
"""

from __future__ import annotations

import hashlib
import json

import httpx
import structlog
from openai import AsyncOpenAI, APIError, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.cache import cache
from app.core.config import settings
from app.schemas.llm import LLMResponseSchema

logger = structlog.get_logger(__name__)

SYNASTRY_CACHE_PREFIX = "synastry_llm:v1"


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
    """
    Строит user-промпт с данными двух карт и аспектами синастрии.
    chart_data содержит: subject1, subject2, aspects
    """
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
        prompt = (
            f"Synastry analysis for:\n"
            f"  Person 1: {person1_name}\n"
            f"  Person 2: {person2_name}\n\n"
            f"Chart data:\n{json.dumps(chart_data, indent=2, ensure_ascii=False)}\n\n"
            "Write the entire analysis in clear, fluent English."
        )
    else:
        prompt = (
            f"Синастрия (совместность) двух людей:\n"
            f"  Человек 1: {person1_name}\n"
            f"  Человек 2: {person2_name}\n\n"
            f"Данные карт и аспекты:\n{json.dumps(chart_data, indent=2, ensure_ascii=False)}"
        )
    return prompt


def make_synastry_cache_key(chart_data: dict, locale: str = "ru") -> str:
    raw = json.dumps({"chart": chart_data, "locale": locale}, sort_keys=True)
    return f"{SYNASTRY_CACHE_PREFIX}:{hashlib.sha256(raw.encode()).hexdigest()}"


class SynastryLLMService:
    def __init__(self) -> None:
        timeout = httpx.Timeout(
            settings.LLM_HTTP_TIMEOUT_SECONDS,
            connect=min(30.0, float(settings.LLM_HTTP_TIMEOUT_SECONDS)),
        )
        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com",
            timeout=timeout,
        )
        self.model = settings.LLM_MODEL

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((RateLimitError, APIError)),
        reraise=True,
    )
    async def generate_synastry_interpretation(
        self,
        person1_name: str,
        person2_name: str,
        chart_data: dict,
        locale: str = "ru",
        system_prompt_override: str | None = None,
        chart_context: str | None = None,
    ) -> LLMResponseSchema:
        if locale not in ("ru", "en"):
            locale = "ru"

        cache_key = make_synastry_cache_key(chart_data, locale)
        cached = await cache.get(cache_key)
        if cached:
            logger.info("Synastry LLM cache hit", locale=locale)
            return LLMResponseSchema(**cached)

        system_prompt = system_prompt_override or build_synastry_system_prompt(locale)
        user_prompt = build_synastry_user_prompt(
            person1_name,
            person2_name,
            chart_data,
            locale,
            chart_context=chart_context,
        )

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=settings.LLM_TEMPERATURE,
            top_p=settings.LLM_TOP_P,
            max_tokens=settings.LLM_MAX_TOKENS_PRO,
        )

        content = response.choices[0].message.content
        logger.info(
            "Synastry LLM tokens used",
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
        )

        validated = LLMResponseSchema.from_markdown(content)
        await cache.set(cache_key, validated.model_dump(), ttl=90 * 24 * 3600)
        return validated
