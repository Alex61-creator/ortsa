"""Расчёт строки «тумблеры» для заказа report/bundle (без промокода на тариф)."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.report_options import REPORT_OPTION_KEYS, REPORT_OPTION_KEYS_SET
from app.models.app_settings import AppSettings

MONEY_QUANT = Decimal("0.01")

# Ключи в app_settings (админка)
REPORT_OPTION_PRICE_SETTING_KEYS: dict[str, str] = {
    "partnership": "report_option_price_partnership",
    "children_parenting": "report_option_price_children_parenting",
    "career": "report_option_price_career",
    "money_boundaries": "report_option_price_money_boundaries",
}
REPORT_OPTION_MULTI_DISCOUNT_KEY = "report_option_multi_discount_percent"

DEFAULT_REPORT_OPTION_PRICE = Decimal("199.00")
DEFAULT_MULTI_DISCOUNT_PERCENT = Decimal("30")


def compute_toggle_line(
    *,
    selected_keys: set[str] | frozenset[str],
    price_by_key: dict[str, Decimal],
    multi_discount_percent: Decimal,
) -> Decimal:
    """
    Сумма цен включённых опций; при 2+ включённых — скидка multi_discount_percent на сумму опций.
    Промокод сюда не входит.
    """
    keys = [k for k in REPORT_OPTION_KEYS if k in selected_keys and k in REPORT_OPTION_KEYS_SET]
    if not keys:
        return Decimal("0.00")

    raw = Decimal("0.00")
    for k in keys:
        p = price_by_key.get(k)
        if p is None or p < 0:
            continue
        raw += p.quantize(MONEY_QUANT)

    n = len(keys)
    if n >= 2 and multi_discount_percent > 0:
        factor = (Decimal(100) - multi_discount_percent) / Decimal(100)
        raw = (raw * factor).quantize(MONEY_QUANT)

    return raw.quantize(MONEY_QUANT)


def parse_percent_setting(raw: str | None, *, default: Decimal) -> Decimal:
    if raw is None or not str(raw).strip():
        return default
    try:
        v = Decimal(str(raw).strip())
    except Exception:
        return default
    if v < 0:
        return Decimal(0)
    if v > 100:
        return Decimal(100)
    return v


def parse_price_setting(raw: str | None, *, default: Decimal) -> Decimal:
    if raw is None or not str(raw).strip():
        return default
    try:
        v = Decimal(str(raw).strip())
    except Exception:
        return default
    if v < 0:
        return Decimal(0)
    return v.quantize(MONEY_QUANT)


async def load_report_option_price_map_and_multi(
    db: AsyncSession,
) -> tuple[dict[str, Decimal], Decimal]:
    """Читает цены тумблеров и процент multi-скидки из app_settings."""
    keys = list(REPORT_OPTION_PRICE_SETTING_KEYS.values()) + [REPORT_OPTION_MULTI_DISCOUNT_KEY]
    result = await db.execute(select(AppSettings).where(AppSettings.key.in_(keys)))
    rows = {r.key: r.value for r in result.scalars().all()}
    price_by_key: dict[str, Decimal] = {}
    for opt_key, setting_key in REPORT_OPTION_PRICE_SETTING_KEYS.items():
        price_by_key[opt_key] = parse_price_setting(
            rows.get(setting_key), default=DEFAULT_REPORT_OPTION_PRICE
        )
    multi = parse_percent_setting(
        rows.get(REPORT_OPTION_MULTI_DISCOUNT_KEY),
        default=DEFAULT_MULTI_DISCOUNT_PERCENT,
    )
    return price_by_key, multi
