from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_admin_user
from app.api.v1.admin.logs import append_admin_log
from app.core.cache import cache
from app.models.user import User
from app.schemas.admin_extra import PromoCreate, PromoOut, PromoPatch

router = APIRouter()

PROMOS_KEY = "admin:promos:list"


async def _get_promos() -> list[dict]:
    data = await cache.get(PROMOS_KEY)
    return data if isinstance(data, list) else []


@router.get("/", response_model=list[PromoOut], summary="Промокоды: список")
async def list_promos(_: User = Depends(get_current_admin_user)):
    return await _get_promos()


@router.post("/", response_model=PromoOut, summary="Промокоды: создать")
async def create_promo(payload: PromoCreate, actor: User = Depends(get_current_admin_user)):
    promos = await _get_promos()
    if any(p["code"].lower() == payload.code.lower() for p in promos):
        raise HTTPException(status_code=400, detail="Promo code already exists")
    row = PromoOut(
        id=str(uuid4()),
        code=payload.code.upper(),
        discount_percent=payload.discount_percent,
        max_uses=payload.max_uses,
        used_count=0,
        active_until=payload.active_until,
        is_active=True,
    ).model_dump()
    row["created_at"] = datetime.utcnow().isoformat()
    promos.append(row)
    await cache.set(PROMOS_KEY, promos)
    await append_admin_log(actor.email or f"user:{actor.id}", "promo_create", f"promo:{row['code']}")
    return PromoOut(**row)


@router.patch("/{promo_id}", response_model=PromoOut, summary="Промокоды: обновить")
async def patch_promo(promo_id: str, payload: PromoPatch, actor: User = Depends(get_current_admin_user)):
    promos = await _get_promos()
    for idx, promo in enumerate(promos):
        if promo["id"] == promo_id:
            update = payload.model_dump(exclude_unset=True)
            promos[idx] = {**promo, **update}
            await cache.set(PROMOS_KEY, promos)
            await append_admin_log(actor.email or f"user:{actor.id}", "promo_patch", f"promo:{promos[idx]['code']}")
            return PromoOut(**promos[idx])
    raise HTTPException(status_code=404, detail="Promo not found")
