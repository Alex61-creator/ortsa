"""Коды тарифов и уровни LLM (согласованы с БД и лендингом)."""

from enum import StrEnum

# Поле tariffs.llm_tier
class LlmTier(StrEnum):
    FREE = "free"
    NATAL_FULL = "natal_full"
    PRO = "pro"


FEATURE_KEY_MAX_NATAL_PROFILES = "max_natal_profiles"

# Допустимые коды тарифов в БД и API
# free        — бесплатный (1 профиль)
# report      — полный разовый отчёт (1 профиль)
# bundle      — набор 3 отчётов (до 3 профилей)
# sub_monthly — помесячная подписка (до 5 профилей)
# sub_annual  — подписка на год (до 5 профилей)
CODE_TO_LLM_TIER: dict[str, LlmTier] = {
    "free": LlmTier.FREE,
    "report": LlmTier.NATAL_FULL,
    "bundle": LlmTier.NATAL_FULL,
    "sub_monthly": LlmTier.PRO,
    "sub_annual": LlmTier.PRO,
    # backward-compat alias для старых заказов с кодом 'pro'
    "pro": LlmTier.PRO,
}

# Коды подписочных тарифов (billing_type = subscription)
SUBSCRIPTION_CODES = frozenset({"sub_monthly", "sub_annual", "pro"})

# Максимум натальных профилей по умолчанию (если features.max_natal_profiles не задан)
DEFAULT_MAX_NATAL_PROFILES = 1


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
