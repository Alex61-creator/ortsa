"""Константы для расчёта транзитов и прогрессий."""

# ── Шаг сетки для расчёта транзитов ─────────────────────────────────────────
# 6 часов → ~120–124 точки на 30-дневное окно (достаточная точность)
TRANSIT_GRID_HOURS: int = 6

# ── Орбы по типу аспекта (в градусах) ────────────────────────────────────────
DEFAULT_ORBS: dict[str, float] = {
    "conjunction": 8.0,
    "opposition": 8.0,
    "trine": 6.0,
    "square": 6.0,
    "sextile": 4.0,
    "semisquare": 2.0,
    "sesquisquare": 2.0,
    "quincunx": 3.0,
    "semisextile": 2.0,
}

# ── Планеты «первого плана» (повышают приоритет аспекта) ─────────────────────
PRIORITY_PLANETS: frozenset[str] = frozenset(
    {"Sun", "Moon", "Mercury", "Venus", "Mars", "Ascendant", "Medium_Coeli"}
)

# ── Медленные планеты (аспекты помечаются как фоновые в прогрессиях) ─────────
SLOW_PLANETS: frozenset[str] = frozenset(
    {"Saturn", "Uranus", "Neptune", "Pluto", "Chiron"}
)

# ── Тарифы, дающие доступ к forecast (транзиты + прогрессии) ─────────────────
# Используется в pipeline для определения типа отчёта.
FORECAST_TARIFF_CODES: frozenset[str] = frozenset(
    {
        "sub_monthly",
        "sub_annual",
        "transit_month_pack",
        "forecast_month_pack",
    }
)

# ── Окно forecast по умолчанию (дни) ─────────────────────────────────────────
DEFAULT_FORECAST_WINDOW_DAYS: int = 30

# ── TTL кэша расчёта транзитов (секунды) ─────────────────────────────────────
FORECAST_CACHE_TTL: int = 24 * 3600  # 24 часа
