from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user
from app.core.cache import cache
from app.db.session import get_db
from app.models.tariff import Tariff
from app.models.user import User
from app.schemas.admin_extra import TariffHistoryRow
from app.schemas.admin_tariff import TariffAdminOut, TariffAdminPatch
from app.services.admin_logs import append_admin_log
from app.services.tariff import TariffService

router = APIRouter()
TARIFF_HISTORY_KEY = "admin:tariffs:history"


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
    actor: User = Depends(get_current_admin_user),
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
    history = await cache.get(TARIFF_HISTORY_KEY)
    rows = history if isinstance(history, list) else []
    rows.insert(
        0,
        TariffHistoryRow(
            id=str(uuid4()),
            tariff_id=t.id,
            actor=actor.email or f"user:{actor.id}",
            payload=data,
            created_at=datetime.utcnow(),
        ).model_dump(mode="json"),
    )
    await cache.set(TARIFF_HISTORY_KEY, rows[:100])
    await append_admin_log(db, actor.email or f"user:{actor.id}", "tariff_patch", f"tariff:{t.id}")
    return t


@router.get("/history/list", response_model=list[TariffHistoryRow], summary="История изменений тарифов")
async def tariff_history(_: User = Depends(get_current_admin_user)):
    rows = await cache.get(TARIFF_HISTORY_KEY)
    if not isinstance(rows, list):
        return []
    return [TariffHistoryRow(**row) for row in rows]
