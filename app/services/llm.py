import hashlib
import json
from openai import AsyncOpenAI, RateLimitError, APIError
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings
from app.core.cache import cache
from app.schemas.llm import LLMResponseSchema
from app.models.tariff import Tariff
from app.constants.tariffs import LlmTier, resolve_llm_tier

logger = structlog.get_logger(__name__)

LLM_CACHE_PREFIX = "llm:v2"


class LLMService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com"
        )
        self.model = settings.LLM_MODEL

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
                return base
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

    def build_user_prompt(self, chart_data: dict, include_transits: bool = False, locale: str = "ru") -> str:
        if locale == "en":
            prompt = "Natal chart data:\n" + json.dumps(chart_data, indent=2, ensure_ascii=False)
            if include_transits:
                prompt += "\n\nInclude current transits at the time of report generation."
            prompt += "\n\nWrite the entire interpretation in clear, fluent English."
            return prompt
        prompt = "Данные натальной карты:\n" + json.dumps(chart_data, indent=2, ensure_ascii=False)
        if include_transits:
            prompt += "\n\nТекущие транзиты на момент составления отчёта: необходимо учесть."
        return prompt

    def make_cache_key(self, chart_data: dict, tier: LlmTier, locale: str = "ru") -> str:
        data = {"chart": chart_data, "llm_tier": tier.value, "locale": locale}
        raw = json.dumps(data, sort_keys=True)
        return f"{LLM_CACHE_PREFIX}:{hashlib.md5(raw.encode()).hexdigest()}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((RateLimitError, APIError)),
        reraise=True
    )
    async def generate_interpretation(
        self, chart_data: dict, tariff: Tariff, locale: str = "ru"
    ) -> LLMResponseSchema:
        if locale not in ("ru", "en"):
            locale = "ru"
        tier = resolve_llm_tier(tariff.code, getattr(tariff, "llm_tier", None))
        cache_key = self.make_cache_key(chart_data, tier, locale)
        cached = await cache.get(cache_key)
        if cached:
            logger.info("LLM cache hit", tier=tier.value, locale=locale)
            return LLMResponseSchema(**cached)

        system_prompt = self.build_system_prompt(tier, locale)
        include_transits = tier == LlmTier.PRO
        user_prompt = self.build_user_prompt(chart_data, include_transits, locale)
        max_tokens = self._max_tokens_for_tier(tier)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=settings.LLM_TEMPERATURE,
            top_p=settings.LLM_TOP_P,
            max_tokens=max_tokens,
        )

        content = response.choices[0].message.content
        logger.info("LLM tokens used",
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens)

        validated = LLMResponseSchema.from_markdown(content)
        await cache.set(cache_key, validated.model_dump(), ttl=90*24*3600)
        return validated
