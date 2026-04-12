"""Коды тарифов и уровни LLM (согласованы с БД и лендингом)."""

from enum import StrEnum

# Поле tariffs.llm_tier
class LlmTier(StrEnum):
    FREE = "free"
    NATAL_FULL = "natal_full"
    PRO = "pro"


FEATURE_KEY_MAX_NATAL_PROFILES = "max_natal_profiles"

# Допустимые коды тарифов в БД и API: free, report, bundle, pro
CODE_TO_LLM_TIER: dict[str, LlmTier] = {
    "free": LlmTier.FREE,
    "report": LlmTier.NATAL_FULL,
    "bundle": LlmTier.NATAL_FULL,
    "pro": LlmTier.PRO,
}


def resolve_llm_tier(code: str, stored_tier: str | None) -> LlmTier:
    """Приоритет: колонка llm_tier; иначе маппинг по code; неизвестный code → natal_full."""
    if stored_tier:
        try:
            return LlmTier(stored_tier)
        except ValueError:
            pass
    if code in CODE_TO_LLM_TIER:
        return CODE_TO_LLM_TIER[code]
    return LlmTier.NATAL_FULL
