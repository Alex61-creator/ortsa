from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_admin_user
from app.api.v1.admin.logs import append_admin_log
from app.core.cache import cache
from app.models.user import User
from app.schemas.admin_extra import FlagOut, FlagPatch

router = APIRouter()

FLAGS_META = {
    "admin_funnel_enabled": "Включает экран воронки",
    "promo_codes_enabled": "Включает применение промокодов",
    "health_panel_enabled": "Включает расширенный мониторинг",
}


@router.get("/", response_model=list[FlagOut], summary="Feature flags: список")
async def list_flags(_: User = Depends(get_current_admin_user)):
    rows: list[FlagOut] = []
    for key, description in FLAGS_META.items():
        value = await cache.get(f"feature:{key}")
        rows.append(FlagOut(key=key, description=description, enabled=bool(value)))
    return rows


@router.patch("/{flag_key}", response_model=FlagOut, summary="Feature flags: переключить")
async def patch_flag(flag_key: str, payload: FlagPatch, actor: User = Depends(get_current_admin_user)):
    if flag_key not in FLAGS_META:
        raise HTTPException(status_code=404, detail="Flag not found")
    await cache.set(f"feature:{flag_key}", payload.enabled)
    await append_admin_log(actor.email or f"user:{actor.id}", "flag_patch", flag_key)
    return FlagOut(key=flag_key, description=FLAGS_META[flag_key], enabled=payload.enabled)
