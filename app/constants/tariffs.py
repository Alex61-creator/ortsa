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
    "sub_monthly": LlmTier.PRO,
    "sub_annual": LlmTier.PRO,
    "pro": LlmTier.PRO,  # backward-compat alias
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


# ── Подписки ─────────────────────────────────────────────────────────────────
SUBSCRIPTION_CODES: frozenset[str] = frozenset({"sub_monthly", "sub_annual", "pro"})

# ── Синастрия ─────────────────────────────────────────────────────────────────

# Тарифы, у которых есть базовый доступ к синастрии
SYNASTRY_ACCESS_CODES: frozenset[str] = frozenset({"bundle", "sub_monthly", "sub_annual", "pro"})

# Тарифы с безлимитными синастриями (подписки платят ежемесячно — лимит не нужен)
SYNASTRY_UNLIMITED_CODES: frozenset[str] = frozenset({"sub_monthly", "sub_annual", "pro"})

# Для bundle: количество включённых бесплатных синастрий
SYNASTRY_BUNDLE_FREE_COUNT: int = 1

# Ключ в таблице app_settings для цены дополнительной синастрии
SYNASTRY_REPEAT_PRICE_KEY: str = "synastry_repeat_price"
SYNASTRY_REPEAT_PRICE_DEFAULT: str = "190.00"


def has_synastry_access(tariff_code: str) -> bool:
    """Возвращает True, если тариф даёт доступ к синастрии."""
    return tariff_code in SYNASTRY_ACCESS_CODES


def is_synastry_unlimited(tariff_code: str) -> bool:
    """Возвращает True, если тариф даёт безлимитные синастрии."""
    return tariff_code in SYNASTRY_UNLIMITED_CODES


def synastry_free_count(tariff_code: str) -> int:
    """Количество бесплатных синастрий для тарифа (0 — нет доступа)."""
    if tariff_code in SYNASTRY_UNLIMITED_CODES:
        return -1  # -1 = безлимитно
    if tariff_code == "bundle":
        return SYNASTRY_BUNDLE_FREE_COUNT
    return 0
