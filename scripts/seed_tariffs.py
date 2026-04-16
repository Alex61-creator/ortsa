"""
Идемпотентное заполнение базовых тарифов (free, report, bundle, pro — как в лендинге и CODE_TO_LLM_TIER).

Запуск из корня проекта:
  PYTHONPATH=. python -m scripts.seed_tariffs

Повторный запуск не дублирует строки с тем же `code`.
"""
import asyncio
from decimal import Decimal

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.tariff import Tariff

DEFAULT_TARIFFS: list[dict] = [
    {
        "code": "free",
        "name": "Бесплатный отчёт",
        "price": Decimal("0.00"),
        "price_usd": Decimal("0.00"),
        "features": {"max_natal_profiles": 1},
        "retention_days": 3,
        "billing_type": "one_time",
        "subscription_interval": None,
        "llm_tier": "free",
        "priority": 0,
    },
    {
        "code": "report",
        "name": "Разовый полный отчёт",
        "price": Decimal("990.00"),
        "price_usd": Decimal("10.00"),
        "features": {"max_natal_profiles": 3},
        "retention_days": 30,
        "billing_type": "one_time",
        "subscription_interval": None,
        "llm_tier": "natal_full",
        "priority": 10,
    },
    {
        "code": "pro",
        "name": "Astro Pro (месяц)",
        "price": Decimal("490.00"),
        "price_usd": Decimal("5.00"),
        "compare_price_usd": Decimal("8.00"),
        "annual_total_usd": Decimal("60.00"),
        "features": {"max_natal_profiles": 5},
        "retention_days": 180,
        "billing_type": "subscription",
        "subscription_interval": "month",
        "llm_tier": "pro",
        "priority": 20,
    },
    {
        "code": "bundle",
        "name": "Bundle: 3 отчёта",
        "price": Decimal("2490.00"),
        "price_usd": Decimal("25.00"),
        "features": {"max_natal_profiles": 3, "synastry_included": 1},
        "retention_days": 30,
        "billing_type": "one_time",
        "subscription_interval": None,
        "llm_tier": "natal_full",
        "priority": 15,
    },
    {
        "code": "synastry_addon",
        "name": "Дополнительная синастрия",
        "price": Decimal("190.00"),
        "price_usd": Decimal("2.00"),
        "features": {"synastry_credits": 1},
        "retention_days": 365,
        "billing_type": "one_time",
        "subscription_interval": None,
        "llm_tier": "natal_full",
        "priority": 99,   # служебный тариф, не показывается на лендинге
    },
]


async def seed_tariffs() -> None:
    async with AsyncSessionLocal() as db:
        for spec in DEFAULT_TARIFFS:
            code = spec["code"]
            r = await db.execute(select(Tariff.id).where(Tariff.code == code))
            if r.scalar_one_or_none() is not None:
                continue
            kwargs = {k: v for k, v in spec.items() if v is not None}
            db.add(Tariff(**kwargs))
        await db.commit()
    print("seed_tariffs: done")


if __name__ == "__main__":
    asyncio.run(seed_tariffs())
