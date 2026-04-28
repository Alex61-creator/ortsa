"""
LLM-сервис для генерации интерпретации натальной карты.

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
from app.models.tariff import Tariff
from app.constants.tariffs import LlmTier, resolve_llm_tier
from app.services.llm_client import (
    LLMProvider,
    create_client_for_provider,
    model_for_provider,
    pricing_for_provider,
)
from app.services.llm_router import call_with_fallback
from app.services.llm_validator import (
    LLMValidationError,
    validate_response,
    language_enforcement_suffix,
)

logger = structlog.get_logger(__name__)

LLM_CACHE_PREFIX = "llm:v3"


# ── Вспомогательные: вызов провайдера ────────────────────────────────────────

async def _call_openai_provider(
    provider: LLMProvider,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
) -> tuple[LLMResponseSchema, dict]:
    """Вызов DeepSeek или Grok через OpenAI-совместимый клиент."""
    client = create_client_for_provider(provider)
    model = model_for_provider(provider)

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=settings.LLM_TEMPERATURE,
        top_p=settings.LLM_TOP_P,
        max_tokens=max_tokens,
    )

    content = response.choices[0].message.content or ""
    usage = response.usage
    return LLMResponseSchema.from_markdown(content), {
        "model": model,
        "prompt_tokens": usage.prompt_tokens if usage else 0,
        "completion_tokens": usage.completion_tokens if usage else 0,
        "total_tokens": usage.total_tokens if usage else 0,
        "cached_tokens": 0,
    }


async def _call_claude_provider(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
) -> tuple[LLMResponseSchema, dict]:
    """Вызов Claude через Anthropic SDK с cache_control на системный промпт."""
    client = create_client_for_provider(LLMProvider.CLAUDE)
    model = model_for_provider(LLMProvider.CLAUDE)

    response = await client.messages.create(
        model=model,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_prompt}],
        temperature=settings.LLM_TEMPERATURE,
        top_p=settings.LLM_TOP_P,
        max_tokens=max_tokens,
    )

    content = response.content[0].text if response.content else ""
    usage = response.usage
    prompt_tokens = getattr(usage, "input_tokens", 0)
    completion_tokens = getattr(usage, "output_tokens", 0)
    cached_tokens = getattr(usage, "cache_read_input_tokens", 0) or 0
    return LLMResponseSchema.from_markdown(content), {
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "cached_tokens": cached_tokens,
    }


async def _call_api(
    provider: LLMProvider,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
) -> tuple[LLMResponseSchema, dict]:
    """Универсальный вызов API по провайдеру."""
    if provider == LLMProvider.CLAUDE:
        return await _call_claude_provider(system_prompt, user_prompt, max_tokens)
    return await _call_openai_provider(provider, system_prompt, user_prompt, max_tokens)


# ── Расчёт стоимости ──────────────────────────────────────────────────────────

def _compute_cost(provider: LLMProvider, usage: dict) -> tuple[Decimal, Decimal]:
    """Считает (cost_usd, cost_rub) для вызова LLM."""
    pricing = pricing_for_provider(provider)

    regular_input = max(0, usage["prompt_tokens"] - usage["cached_tokens"])
    cost_usd = (
        regular_input * pricing["input"]
        + usage["cached_tokens"] * pricing["cache_read"]
        + usage["completion_tokens"] * pricing["output"]
    ) / 1_000_000

    cost_rub = cost_usd * settings.LLM_USD_TO_RUB_RATE
    return Decimal(str(round(cost_usd, 6))), Decimal(str(round(cost_rub, 4)))


# ── Запись LlmUsageLog (fire-and-forget) ─────────────────────────────────────

async def _write_usage_log(
    user_id: int,
    order_id: int | None,
    provider: LLMProvider,
    usage: dict,
    cost_usd: Decimal,
    cost_rub: Decimal,
) -> None:
    try:
        from app.db.session import AsyncSessionLocal
        from app.models.llm_usage_log import LlmUsageLog

        async with AsyncSessionLocal() as db:
            log = LlmUsageLog(
                user_id=user_id,
                order_id=order_id,
                model=usage["model"],
                provider=provider.value,
                prompt_tokens=usage["prompt_tokens"],
                completion_tokens=usage["completion_tokens"],
                total_tokens=usage["total_tokens"],
                cached_tokens=usage["cached_tokens"],
                cost_usd=cost_usd,
                cost_rub=cost_rub,
            )
            db.add(log)
            await db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to write LlmUsageLog", error=str(exc))


# ── Основной сервис ───────────────────────────────────────────────────────────

class LLMService:
    """Генерация интерпретации натальной карты с multi-provider failover."""

    def _max_tokens_for_tier(self, tier: LlmTier) -> int:
        if tier == LlmTier.FREE:
            return settings.LLM_MAX_TOKENS_FREE
        if tier == LlmTier.PRO:
            return settings.LLM_MAX_TOKENS_PRO
        return settings.LLM_MAX_TOKENS_FULL

    def build_system_prompt(self, tier: LlmTier, locale: str = "ru") -> str:
        if locale == "en":
            if tier == LlmTier.FREE:
                return """
        You are a professional astrologer. Write a very brief natal chart snapshot for a one-page PDF.
        Use only the provided data. Follow the structure strictly and use these section markers.

        ## [OVERVIEW]
        ## [SUN]
        ## [MOON]
        ## [ASCENDANT]
        """
            if tier == LlmTier.NATAL_FULL:
                return """
        You are a professional astrologer with 20 years of experience. Write a detailed natal chart interpretation.
        Use only the provided data. Follow the structure strictly and use these section markers.

        ## [GENERAL OVERVIEW]
        ## [SUN]
        ## [MOON]
        ## [MERCURY]
        ## [VENUS]
        ## [MARS]
        ## [JUPITER]
        ## [SATURN]
        ## [OUTER PLANETS]
        ## [ASCENDANT & HOUSES]
        ## [ASPECTS]
        ## [NODAL AXIS & KARMA]
        ## [RECOMMENDATIONS]
        """
            # PRO
            base = """
        You are a professional astrologer with 20 years of experience. Write a detailed natal chart interpretation.
        Use only the provided data. Follow the structure strictly and use these section markers.

        ## [GENERAL OVERVIEW]
        ## [SUN]
        ## [MOON]
        ## [MERCURY]
        ## [VENUS]
        ## [MARS]
        ## [JUPITER]
        ## [SATURN]
        ## [OUTER PLANETS]
        ## [ASCENDANT & HOUSES]
        ## [ASPECTS]
        ## [NODAL AXIS & KARMA]
        ## [RECOMMENDATIONS]
        """
            base += "\n## [TRANSITS FOR THE MONTH]"
            base += "\n## [DEEP DIVE]\n## [ORBS & HOUSE SYSTEMS]"
            return base

        if tier == LlmTier.FREE:
            return """
        Ты — профессиональный астролог. Напиши очень краткий снимок натальной карты для одностраничного PDF.
        Используй только предоставленные данные. Строго по структуре, с маркерами разделов.

        ## [ОБЩИЙ ОБЗОР]
        ## [СОЛНЦЕ]
        ## [ЛУНА]
        ## [АСЦЕНДЕНТ]
        """
        if tier == LlmTier.NATAL_FULL:
            return """
        Ты — профессиональный астролог с 20-летним опытом. Составь подробную интерпретацию натальной карты.
        Используй только предоставленные данные. Отвечай строго по структуре, используя маркеры разделов.

        ## [ОБЩАЯ ХАРАКТЕРИСТИКА]
        ## [СОЛНЦЕ]
        ## [ЛУНА]
        ## [МЕРКУРИЙ]
        ## [ВЕНЕРА]
        ## [МАРС]
        ## [ЮПИТЕР]
        ## [САТУРН]
        ## [ВЫСШИЕ ПЛАНЕТЫ]
        ## [АСЦЕНДЕНТ И ДОМА]
        ## [АСПЕКТЫ]
        ## [НОДАЛЬНАЯ ОСЬ И КАРМА]
        ## [РЕКОМЕНДАЦИИ]
        """
        base = """
        Ты — профессиональный астролог с 20-летним опытом. Составь подробную интерпретацию натальной карты.
        Используй только предоставленные данные. Отвечай строго по структуре, используя маркеры разделов.

        ## [ОБЩАЯ ХАРАКТЕРИСТИКА]
        ## [СОЛНЦЕ]
        ## [ЛУНА]
        ## [МЕРКУРИЙ]
        ## [ВЕНЕРА]
        ## [МАРС]
        ## [ЮПИТЕР]
        ## [САТУРН]
        ## [ВЫСШИЕ ПЛАНЕТЫ]
        ## [АСЦЕНДЕНТ И ДОМА]
        ## [АСПЕКТЫ]
        ## [НОДАЛЬНАЯ ОСЬ И КАРМА]
        ## [РЕКОМЕНДАЦИИ]
        """
        base += "\n## [ТРАНЗИТЫ НА МЕСЯЦ]"
        base += "\n## [УГЛУБЛЁННЫЙ АНАЛИЗ]\n## [ОРБИСЫ И СИСТЕМЫ ДОМОВ]"
        return base

    def build_forecast_system_prompt(self, locale: str = "ru") -> str:
        """Системный промпт для forecast-отчёта с реальными данными транзитов/прогрессий."""
        if locale == "en":
            return """
        You are a professional astrologer with 20 years of experience.
        You will receive: (1) the natal chart data and (2) computed transit and progression data
        for a specific calendar period.

        Your task: write a detailed monthly forecast interpretation based on the actual transit
        and progression data provided. Use ONLY the data given — do not invent aspects not present.

        Follow this structure strictly, using section markers:

        ## [PERIOD OVERVIEW]
        ## [KEY DATES]
        ## [TRANSITS FOR THE MONTH]
        ## [SECONDARY PROGRESSIONS]
        ## [BACKGROUND THEMES]
        ## [PRACTICAL RECOMMENDATIONS]
        """
        return """
        Ты — профессиональный астролог с 20-летним опытом.
        Ты получишь: (1) данные натальной карты и (2) вычисленные транзиты и прогрессии
        за конкретный календарный период.

        Твоя задача: составить подробную интерпретацию месячного прогноза на основе
        предоставленных расчётных данных. Используй ТОЛЬКО переданные данные —
        не придумывай аспекты, которых нет в списке.

        Строго следуй структуре, используя маркеры разделов:

        ## [ОБЗОР ПЕРИОДА]
        ## [КЛЮЧЕВЫЕ ДАТЫ]
        ## [ТРАНЗИТЫ НА МЕСЯЦ]
        ## [ВТОРИЧНЫЕ ПРОГРЕССИИ]
        ## [ФОНОВЫЕ ТЕМЫ]
        ## [ПРАКТИЧЕСКИЕ РЕКОМЕНДАЦИИ]
        """

    def build_user_prompt(
        self,
        chart_data: dict,
        include_transits: bool = False,
        locale: str = "ru",
        chart_context: str | None = None,
        forecast_context_text: str | None = None,
    ) -> str:
        if chart_context:
            if locale == "en":
                prompt = f"Kerykeion structured context (XML):\n{chart_context}"
                if forecast_context_text:
                    prompt += f"\n\n{forecast_context_text}"
                elif include_transits:
                    prompt += "\n\nInclude current transits at the time of report generation."
                prompt += "\n\nWrite the entire interpretation in clear, fluent English."
                return prompt
            prompt = f"Структурированный контекст Kerykeion (XML):\n{chart_context}"
            if forecast_context_text:
                prompt += f"\n\n{forecast_context_text}"
            elif include_transits:
                prompt += "\n\nТекущие транзиты на момент составления отчёта: необходимо учесть."
            return prompt

        if locale == "en":
            prompt = "Natal chart data:\n" + json.dumps(chart_data, indent=2, ensure_ascii=False)
            if forecast_context_text:
                prompt += f"\n\n{forecast_context_text}"
            elif include_transits:
                prompt += "\n\nInclude current transits at the time of report generation."
            prompt += "\n\nWrite the entire interpretation in clear, fluent English."
            return prompt
        prompt = "Данные натальной карты:\n" + json.dumps(chart_data, indent=2, ensure_ascii=False)
        if forecast_context_text:
            prompt += f"\n\n{forecast_context_text}"
        elif include_transits:
            prompt += "\n\nТекущие транзиты на момент составления отчёта: необходимо учесть."
        return prompt

    def make_cache_key(
        self,
        chart_data: dict,
        tier: LlmTier,
        locale: str = "ru",
        *,
        cache_extra: str | None = None,
    ) -> str:
        data: dict = {"chart": chart_data, "llm_tier": tier.value, "locale": locale}
        if cache_extra:
            data["cache_extra"] = cache_extra
        raw = json.dumps(data, sort_keys=True)
        return f"{LLM_CACHE_PREFIX}:{hashlib.sha256(raw.encode()).hexdigest()}"

    async def generate_interpretation(
        self,
        chart_data: dict,
        tariff: Tariff,
        locale: str = "ru",
        system_prompt_override: str | None = None,
        chart_context: str | None = None,
        *,
        llm_cache_extra: str | None = None,
        forecast_context_text: str | None = None,
        user_id: int | None = None,
        order_id: int | None = None,
    ) -> tuple[LLMResponseSchema, LLMProvider]:
        """Генерирует интерпретацию натальной карты с multi-provider failover.

        Returns:
            (LLMResponseSchema, LLMProvider) — схема ответа и провайдер, который её сгенерировал.
        """
        if locale not in ("ru", "en"):
            locale = "ru"

        tier = resolve_llm_tier(tariff.code, getattr(tariff, "llm_tier", None))
        cache_key = self.make_cache_key(chart_data, tier, locale, cache_extra=llm_cache_extra)

        # ── Cache hit ─────────────────────────────────────────────────────────
        cached = await cache.get(cache_key)
        if cached:
            logger.info("LLM cache hit", tier=tier.value, locale=locale)
            if "response" in cached and "provider" in cached:
                cached_provider = LLMProvider(cached.get("provider", LLMProvider.DEEPSEEK.value))
                return LLMResponseSchema(**cached["response"]), cached_provider
            # Старый формат v2
            return LLMResponseSchema(**cached), LLMProvider.DEEPSEEK

        # ── Подготовка промптов ───────────────────────────────────────────────
        system_prompt = system_prompt_override or self.build_system_prompt(tier, locale)
        include_transits = tier == LlmTier.PRO
        user_prompt = self.build_user_prompt(
            chart_data,
            include_transits,
            locale,
            chart_context=chart_context,
            forecast_context_text=forecast_context_text,
        )
        max_tokens = self._max_tokens_for_tier(tier)

        # ── Closure для router ────────────────────────────────────────────────
        async def _fn(provider: LLMProvider) -> tuple[LLMResponseSchema, dict]:
            response, usage = await _call_api(provider, system_prompt, user_prompt, max_tokens)

            try:
                validate_response(response, tier, locale)
            except LLMValidationError as first_err:
                logger.warning(
                    "LLM validation failed, retrying with reinforced prompt",
                    provider=provider.value,
                    error=str(first_err),
                )
                enhanced_prompt = user_prompt + language_enforcement_suffix(locale)
                response, usage = await _call_api(provider, system_prompt, enhanced_prompt, max_tokens)
                validate_response(response, tier, locale)  # при повторном сбое → LLMValidationError → router

            logger.info(
                "LLM tokens used",
                provider=provider.value,
                prompt_tokens=usage["prompt_tokens"],
                completion_tokens=usage["completion_tokens"],
                cached_tokens=usage["cached_tokens"],
                total_tokens=usage["total_tokens"],
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
                _write_usage_log(user_id, order_id, provider_used, usage, cost_usd, cost_rub)
            )

        return response, provider_used

    # ── Подписочные услуги ───────────────────────────────────────────────────

    def build_monthly_forecast_prompt(self, locale: str = "ru") -> str:
        if locale == "en":
            return (
                "You are a professional astrologer. Write a concise 3-4 page personal monthly forecast PDF.\n"
                "Use only the provided natal chart data and transit list. Follow the structure strictly.\n\n"
                "## [MAIN THEMES]\n## [TOP 3 FAVORABLE DATES]\n## [TOP 2 CAUTION DATES]\n"
                "## [CAREER & FINANCES]\n## [RELATIONSHIPS]\n## [HEALTH & ENERGY]\n## [PLANET OF THE MONTH]"
            )
        return (
            "Ты — профессиональный астролог. Составь краткий персональный прогноз на месяц (3–4 страницы PDF).\n"
            "Используй только предоставленные данные натальной карты и список транзитов. Строго по структуре.\n\n"
            "## [ГЛАВНЫЕ ТЕМЫ МЕСЯЦА]\n## [ТОП-3 БЛАГОПРИЯТНЫХ ДАТЫ]\n## [ТОП-2 ДАТЫ ПОВЫШЕННОГО ВНИМАНИЯ]\n"
            "## [КАРЬЕРА И ФИНАНСЫ]\n## [ОТНОШЕНИЯ]\n## [ЗДОРОВЬЕ И ЭНЕРГИЯ]\n## [ПЛАНЕТА МЕСЯЦА]"
        )

    def build_weekly_digest_prompt(self, locale: str = "ru") -> str:
        if locale == "en":
            return (
                "You are a professional astrologer. Write a short weekly transit digest (max 400 words).\n"
                "List 3-5 key transits for the week ahead with brief interpretations (1-2 sentences each).\n"
                "End with a 1-sentence 'Astro tip' for the week. Warm, accessible tone for a Monday morning email."
            )
        return (
            "Ты — профессиональный астролог. Составь короткий еженедельный дайджест транзитов (максимум 400 слов).\n"
            "Укажи 3–5 ключевых транзитов на предстоящую неделю с краткими интерпретациями (1–2 предложения).\n"
            "Заверши абзацем «Астросовет недели» — 1–2 предложения с практической рекомендацией.\n"
            "Пиши тепло, доступно — это письмо приходит в понедельник утром."
        )

    def build_annual_progressions_prompt(self, locale: str = "ru") -> str:
        if locale == "en":
            return (
                "You are a professional astrologer with 20 years of experience.\n"
                "Write a detailed annual progression report (6-8 pages) for the current year of life.\n"
                "Use only the provided natal and progressed chart data. Follow the structure strictly.\n\n"
                "## [YEAR OVERVIEW]\n## [PROGRESSED SUN]\n## [PROGRESSED MOON]\n"
                "## [KEY PROGRESSED ASPECTS]\n## [Q1 — JANUARY TO MARCH]\n## [Q2 — APRIL TO JUNE]\n"
                "## [Q3 — JULY TO SEPTEMBER]\n## [Q4 — OCTOBER TO DECEMBER]\n"
                "## [CAREER & PURPOSE]\n## [RELATIONSHIPS & EMOTIONS]\n## [HEALTH & VITALITY]\n"
                "## [ANNUAL RECOMMENDATIONS]"
            )
        return (
            "Ты — профессиональный астролог с 20-летним опытом.\n"
            "Составь подробный отчёт по вторичным прогрессиям на текущий год жизни (6–8 страниц).\n"
            "Используй только предоставленные данные натальной и прогрессированной карты. Строго по структуре.\n\n"
            "## [ОБЩИЙ ОБЗОР ГОДА]\n## [ПРОГРЕССИРОВАННОЕ СОЛНЦЕ]\n## [ПРОГРЕССИРОВАННАЯ ЛУНА]\n"
            "## [КЛЮЧЕВЫЕ ПРОГРЕССИРОВАННЫЕ АСПЕКТЫ]\n## [Q1 — ЯНВАРЬ–МАРТ]\n## [Q2 — АПРЕЛЬ–ИЮНЬ]\n"
            "## [Q3 — ИЮЛЬ–СЕНТЯБРЬ]\n## [Q4 — ОКТЯБРЬ–ДЕКАБРЬ]\n"
            "## [КАРЬЕРА И ПРЕДНАЗНАЧЕНИЕ]\n## [ОТНОШЕНИЯ И ЭМОЦИИ]\n## [ЗДОРОВЬЕ И ВИТАЛЬНОСТЬ]\n"
            "## [РЕКОМЕНДАЦИИ НА ГОД]"
        )

    async def generate_monthly_forecast(
        self,
        chart_data: dict,
        transit_context: str,
        locale: str = "ru",
        *,
        cache_key_extra: str | None = None,
        user_id: int | None = None,
    ) -> LLMResponseSchema:
        """Персональный месячный прогноз на основе транзитов."""
        if locale not in ("ru", "en"):
            locale = "ru"
        raw = json.dumps(
            {
                "ch": hashlib.sha256(json.dumps(chart_data, sort_keys=True).encode()).hexdigest()[:16],
                "tr": hashlib.sha256(transit_context.encode()).hexdigest()[:16],
                "tier": "monthly_forecast", "locale": locale,
                "extra": cache_key_extra or "",
            },
            sort_keys=True,
        )
        cache_key = f"{LLM_CACHE_PREFIX}:{hashlib.sha256(raw.encode()).hexdigest()}"
        cached = await cache.get(cache_key)
        if cached:
            logger.info("LLM cache hit", tier="monthly_forecast", locale=locale)
            return LLMResponseSchema(**(cached.get("response", cached)))

        system_prompt = self.build_monthly_forecast_prompt(locale)
        if locale == "en":
            user_prompt = (
                f"Natal chart data:\n{json.dumps(chart_data, indent=2, ensure_ascii=False)}\n\n"
                f"Monthly transits:\n{transit_context}\n\nWrite in clear, fluent English."
            )
        else:
            user_prompt = (
                f"Данные натальной карты:\n{json.dumps(chart_data, indent=2, ensure_ascii=False)}\n\n"
                f"Транзиты на месяц:\n{transit_context}"
            )
        max_tokens = 1800

        async def _fn(provider: LLMProvider) -> tuple[LLMResponseSchema, dict]:
            return await _call_api(provider, system_prompt, user_prompt, max_tokens)

        (response, usage), provider_used = await call_with_fallback(
            _fn, validation_error_cls=LLMValidationError
        )
        logger.info("LLM tokens (monthly_forecast)",
                    provider=provider_used.value, total=usage["total_tokens"])
        await cache.set(cache_key,
                        {"provider": provider_used.value, "response": response.model_dump()},
                        ttl=30 * 24 * 3600)
        if user_id is not None:
            cost_usd, cost_rub = _compute_cost(provider_used, usage)
            asyncio.ensure_future(_write_usage_log(user_id, None, provider_used, usage, cost_usd, cost_rub))
        return response

    async def generate_weekly_digest(
        self,
        transit_context: str,
        locale: str = "ru",
        *,
        cache_key_extra: str | None = None,
        user_id: int | None = None,
    ) -> str:
        """Текст еженедельного дайджеста. Возвращает plain-text строку."""
        if locale not in ("ru", "en"):
            locale = "ru"
        raw = json.dumps(
            {
                "tr": hashlib.sha256(transit_context.encode()).hexdigest()[:16],
                "tier": "weekly_digest", "locale": locale,
                "extra": cache_key_extra or "",
            },
            sort_keys=True,
        )
        cache_key = f"{LLM_CACHE_PREFIX}:{hashlib.sha256(raw.encode()).hexdigest()}"
        cached = await cache.get(cache_key)
        if cached and isinstance(cached, dict) and "text" in cached:
            logger.info("LLM cache hit", tier="weekly_digest")
            return cached["text"]

        system_prompt = self.build_weekly_digest_prompt(locale)
        suffix = "\n\nWrite in clear, fluent English." if locale == "en" else ""
        label = "Weekly transits" if locale == "en" else "Транзиты на неделю"
        user_prompt = f"{label}:\n{transit_context}{suffix}"
        max_tokens = 800

        async def _fn(provider: LLMProvider) -> tuple[LLMResponseSchema, dict]:
            return await _call_api(provider, system_prompt, user_prompt, max_tokens)

        (response, usage), provider_used = await call_with_fallback(
            _fn, validation_error_cls=LLMValidationError
        )
        text = response.raw_content or ""
        logger.info("LLM tokens (weekly_digest)",
                    provider=provider_used.value, total=usage["total_tokens"])
        await cache.set(cache_key, {"text": text}, ttl=7 * 24 * 3600)
        return text

    async def generate_annual_progressions(
        self,
        chart_data: dict,
        progression_context: dict,
        locale: str = "ru",
        *,
        cache_key_extra: str | None = None,
        user_id: int | None = None,
    ) -> LLMResponseSchema:
        """Ежегодный отчёт по прогрессиям."""
        if locale not in ("ru", "en"):
            locale = "ru"
        raw = json.dumps(
            {
                "ch": hashlib.sha256(json.dumps(chart_data, sort_keys=True).encode()).hexdigest()[:16],
                "py": progression_context.get("target_year"),
                "tier": "annual_progressions", "locale": locale,
                "extra": cache_key_extra or "",
            },
            sort_keys=True,
        )
        cache_key = f"{LLM_CACHE_PREFIX}:{hashlib.sha256(raw.encode()).hexdigest()}"
        cached = await cache.get(cache_key)
        if cached:
            logger.info("LLM cache hit", tier="annual_progressions", locale=locale)
            return LLMResponseSchema(**(cached.get("response", cached)))

        system_prompt = self.build_annual_progressions_prompt(locale)
        prog_json = json.dumps(progression_context, indent=2, ensure_ascii=False)
        if locale == "en":
            user_prompt = (
                f"Natal chart data:\n{json.dumps(chart_data, indent=2, ensure_ascii=False)}\n\n"
                f"Progressed chart data:\n{prog_json}\n\nWrite in clear, fluent English."
            )
        else:
            user_prompt = (
                f"Данные натальной карты:\n{json.dumps(chart_data, indent=2, ensure_ascii=False)}\n\n"
                f"Данные прогрессий:\n{prog_json}"
            )
        max_tokens = settings.LLM_MAX_TOKENS_FULL

        async def _fn(provider: LLMProvider) -> tuple[LLMResponseSchema, dict]:
            return await _call_api(provider, system_prompt, user_prompt, max_tokens)

        (response, usage), provider_used = await call_with_fallback(
            _fn, validation_error_cls=LLMValidationError
        )
        logger.info("LLM tokens (annual_progressions)",
                    provider=provider_used.value, total=usage["total_tokens"])
        await cache.set(cache_key,
                        {"provider": provider_used.value, "response": response.model_dump()},
                        ttl=365 * 24 * 3600)
        if user_id is not None:
            cost_usd, cost_rub = _compute_cost(provider_used, usage)
            asyncio.ensure_future(_write_usage_log(user_id, None, provider_used, usage, cost_usd, cost_rub))
        return response
