from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user
from app.db.session import get_db
from app.models.promocode import Promocode
from app.models.user import User
from app.schemas.admin_extra import PromoCreate, PromoOut, PromoPatch
from app.services.admin_logs import append_admin_log

router = APIRouter()


@router.get("/", response_model=list[PromoOut], summary="Промокоды: список")
async def list_promos(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    rows = (await db.execute(select(Promocode).order_by(Promocode.created_at.desc()))).scalars().all()
    return [PromoOut.model_validate(row) for row in rows]


@router.post("/", response_model=PromoOut, summary="Промокоды: создать")
async def create_promo(
    payload: PromoCreate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_admin_user),
):
    existing = await db.execute(select(Promocode).where(Promocode.code == payload.code.upper()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Promo code already exists")
    row = Promocode(
        code=payload.code.upper(),
        discount_percent=payload.discount_percent,
        max_uses=payload.max_uses,
        active_until=payload.active_until,
        is_active=True,
        created_by=actor.email or f"user:{actor.id}",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    await append_admin_log(db, actor.email or f"user:{actor.id}", "promo_create", f"promo:{row.code}")
    return PromoOut.model_validate(row)


@router.patch("/{promo_id}", response_model=PromoOut, summary="Промокоды: обновить")
async def patch_promo(
    promo_id: str,
    payload: PromoPatch,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_admin_user),
):
    row = (await db.execute(select(Promocode).where(Promocode.id == promo_id))).scalar_one_or_none()
    if row:
        update = payload.model_dump(exclude_unset=True)
        for key, value in update.items():
            setattr(row, key, value)
        await db.commit()
        await db.refresh(row)
        await append_admin_log(db, actor.email or f"user:{actor.id}", "promo_patch", f"promo:{row.code}")
        return PromoOut.model_validate(row)
    raise HTTPException(status_code=404, detail="Promo not found")
