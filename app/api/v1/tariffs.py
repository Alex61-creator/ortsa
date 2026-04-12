from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.tariff import TariffService
from app.schemas.tariff import TariffPublicOut
from app.utils.tariff_features import max_natal_profiles_from_tariff

router = APIRouter()


@router.get("/", response_model=list[TariffPublicOut])
async def list_tariffs(db: AsyncSession = Depends(get_db)):
    """Публичный каталог тарифов (цены и описание из БД / админки)."""
    tariffs = await TariffService.get_all(db)
    out: list[TariffPublicOut] = []
    for t in sorted(tariffs, key=lambda x: (-x.priority, x.id)):
        out.append(
            TariffPublicOut(
                code=t.code,
                name=t.name,
                price=t.price,
                price_usd=t.price_usd,
                compare_price_usd=t.compare_price_usd,
                annual_total_usd=t.annual_total_usd,
                features=t.features,
                retention_days=t.retention_days,
                priority=t.priority,
                billing_type=t.billing_type,
                subscription_interval=t.subscription_interval,
                llm_tier=t.llm_tier,
                max_natal_profiles=max_natal_profiles_from_tariff(t),
            )
        )
    return out
