"""Расчёт строки «тумблеры» для заказа report/bundle (без промокода на тариф)."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.report_options import REPORT_OPTION_KEYS, REPORT_OPTION_KEYS_SET
from app.models.app_settings import AppSettings
from app.models.order import Order

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


def estimate_report_options_line_amount(
    flags: dict[str, Any] | None,
    *,
    price_by_key: dict[str, Decimal],
    multi_discount_percent: Decimal,
) -> Decimal:
    """Оценка суммы строки тумблеров по флагам заказа и ценам из app_settings (без промо на тариф)."""
    if not flags:
        return Decimal("0.00")
    selected: set[str] = {str(k) for k, v in flags.items() if v is True}
    return compute_toggle_line(
        selected_keys=selected,
        price_by_key=price_by_key,
        multi_discount_percent=multi_discount_percent,
    )


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


async def aggregate_report_option_analytics(
    db: AsyncSession,
    *,
    max_orders: int = 3000,
) -> dict[str, Any]:
    """
    Популярность ключей, распределение числа включённых опций (0–4),
    оценка выручки строки тумблеров (без промо) по последним заказам с флагами.
    """
    price_by_key, multi = await load_report_option_price_map_and_multi(db)
    stmt = (
        select(Order)
        .where(Order.report_option_flags.isnot(None))
        .order_by(Order.created_at.desc())
        .limit(max_orders)
    )
    orders = (await db.execute(stmt)).scalars().all()
    key_counts: Counter[str] = Counter()
    bucket: Counter[int] = Counter()
    line_rev = Decimal("0.00")
    for o in orders:
        flags = o.report_option_flags
        if not flags or not isinstance(flags, dict):
            continue
        sel = {str(k) for k, v in flags.items() if v is True}
        canonical = sel & REPORT_OPTION_KEYS_SET
        for k in canonical:
            key_counts[k] += 1
        n = len(canonical)
        bucket[min(n, 4)] += 1
        line_rev += estimate_report_options_line_amount(
            flags,
            price_by_key=price_by_key,
            multi_discount_percent=multi,
        )
    return {
        "key_counts": dict(key_counts),
        "bucket_counts": {str(i): bucket.get(i, 0) for i in range(5)},
        "estimated_options_revenue_rub": float(line_rev.quantize(MONEY_QUANT)),
        "orders_sampled": len(orders),
    }


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
