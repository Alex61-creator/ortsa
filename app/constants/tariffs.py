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

# Тарифы, у которых есть доступ к синастрии
SYNASTRY_ACCESS_CODES: frozenset[str] = frozenset({"bundle", "sub_monthly", "sub_annual", "pro"})

# Максимальное число активных синастрий на пользователя
SYNASTRY_MAX_PAIRS: dict[str, int] = {
    "bundle": 1,
    "sub_monthly": 3,
    "sub_annual": 3,
    "pro": 3,
}

# Cooldown (часы) между регенерациями одной и той же пары
SYNASTRY_REGEN_COOLDOWN_HOURS: dict[str, int] = {
    "bundle": 168,      # 7 дней — одноразовая покупка, строгий лимит
    "sub_monthly": 72,  # 3 дня
    "sub_annual": 72,   # 3 дня
    "pro": 72,
}

# Для bundle: максимальное число регенераций одной пары
SYNASTRY_MAX_REGEN_BUNDLE: int = 2  # initial + 1 fix


def has_synastry_access(tariff_code: str) -> bool:
    """Возвращает True, если тариф даёт доступ к синастрии."""
    return tariff_code in SYNASTRY_ACCESS_CODES


def synastry_max_pairs(tariff_code: str) -> int:
    return SYNASTRY_MAX_PAIRS.get(tariff_code, 0)


def synastry_regen_cooldown_hours(tariff_code: str) -> int:
    return SYNASTRY_REGEN_COOLDOWN_HOURS.get(tariff_code, 168)
