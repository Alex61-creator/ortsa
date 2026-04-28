"""Коды тарифов и уровни LLM (согласованы с БД и лендингом)."""

from enum import StrEnum

# Поле tariffs.llm_tier
class LlmTier(StrEnum):
    FREE = "free"
    NATAL_FULL = "natal_full"
    PRO = "pro"
    MONTHLY_FORECAST = "monthly_forecast"
    WEEKLY_DIGEST = "weekly_digest"
    ANNUAL_PROGRESSIONS = "annual_progressions"


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
    "transit_month_pack": LlmTier.PRO,
    "forecast_month_pack": LlmTier.PRO,
    "compatibility_deep_dive": LlmTier.NATAL_FULL,
    "return_pack": LlmTier.NATAL_FULL,
}

REPORT_RETENTION_DAYS_BY_CODE: dict[str, int] = {
    "free": 3,
    "report": 30,
    "bundle": 30,
    "sub_monthly": 180,
    "sub_annual": 180,
    "transit_month_pack": 30,
    "forecast_month_pack": 30,
    "compatibility_deep_dive": 30,
    "return_pack": 180,
}

ADDON_TARIFF_CODES: frozenset[str] = frozenset(
    {"transit_month_pack", "forecast_month_pack", "compatibility_deep_dive", "return_pack", "synastry_addon"}
)

ADDON_REPORT_TARIFF_CODES: frozenset[str] = frozenset(
    {"transit_month_pack", "forecast_month_pack", "compatibility_deep_dive", "return_pack"}
)

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


# ── Подписки (billing_type = subscription) ──────────────────────────────────
SUBSCRIPTION_CODES: frozenset[str] = frozenset({"sub_monthly", "sub_annual"})

# ── Синастрия ─────────────────────────────────────────────────────────────────

# Тарифы, у которых есть базовый доступ к синастрии
SYNASTRY_ACCESS_CODES: frozenset[str] = frozenset({"bundle", "sub_monthly", "sub_annual"})

# Тарифы с безлимитными синастриями (подписки платят ежемесячно — лимит не нужен)
SYNASTRY_UNLIMITED_CODES: frozenset[str] = frozenset({"sub_monthly", "sub_annual"})

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
