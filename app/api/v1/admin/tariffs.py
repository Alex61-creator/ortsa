from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user
from app.db.session import get_db
from app.models.tariff import Tariff
from app.models.user import User
from app.schemas.admin_tariff import TariffAdminOut, TariffAdminPatch
from app.services.tariff import TariffService

router = APIRouter()


def _validate_patch(body: TariffAdminPatch) -> None:
    if body.billing_type is not None and body.billing_type not in ("one_time", "subscription"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="billing_type: one_time | subscription")
    if body.subscription_interval is not None and body.subscription_interval not in ("month", "year", ""):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="subscription_interval: month | year")
    if body.llm_tier is not None and body.llm_tier not in ("free", "natal_full", "pro"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="llm_tier: free | natal_full | pro")


@router.get("/", response_model=list[TariffAdminOut], summary="Список тарифов (админ)")
async def list_tariffs_admin(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    result = await db.execute(select(Tariff).order_by(Tariff.priority.desc(), Tariff.id))
    return list(result.scalars().all())


@router.get("/{tariff_id}", response_model=TariffAdminOut, summary="Тариф по id (админ)")
async def get_tariff_admin(
    tariff_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    result = await db.execute(select(Tariff).where(Tariff.id == tariff_id))
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tariff not found")
    return t


@router.patch("/{tariff_id}", response_model=TariffAdminOut, summary="Обновить тариф (админ)")
async def patch_tariff_admin(
    tariff_id: int,
    body: TariffAdminPatch,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    _validate_patch(body)
    result = await db.execute(select(Tariff).where(Tariff.id == tariff_id))
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tariff not found")

    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(t, k, v)
    await db.commit()
    await db.refresh(t)
    await TariffService.invalidate_cache()
    return t
