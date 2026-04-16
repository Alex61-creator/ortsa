from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user
from app.core.cache import cache
from app.db.session import get_db
from app.models.feature_flag import FeatureFlag, FeatureFlagChange
from app.models.user import User
from app.schemas.admin_extra import FlagOut, FlagPatch
from app.services.admin_logs import append_admin_log

router = APIRouter()

FLAGS_META = {
    "admin_funnel_enabled": "Включает экран воронки",
    "promo_codes_enabled": "Включает применение промокодов",
    "health_panel_enabled": "Включает расширенный мониторинг",
    "addons_enabled": "Глобальный kill switch add-on продаж и офферинга",
    "report_upsell_sections_enabled": "Доп. разделы отчёта (тумблеры) в визарде report/bundle",
}


@router.get("/", response_model=list[FlagOut], summary="Feature flags: список")
async def list_flags(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    existing = {
        row.key: row
        for row in (await db.execute(select(FeatureFlag))).scalars().all()
    }
    rows: list[FlagOut] = []
    for key, description in FLAGS_META.items():
        row = existing.get(key)
        if row is None:
            row = FeatureFlag(key=key, description=description, enabled=False)
            db.add(row)
            await db.commit()
            await db.refresh(row)
        await cache.set(f"feature:{key}", "true" if row.enabled else "false")
        rows.append(FlagOut(key=key, description=row.description, enabled=row.enabled, updated_at=row.updated_at, updated_by=row.updated_by))
    return rows


@router.patch("/{flag_key}", response_model=FlagOut, summary="Feature flags: переключить")
async def patch_flag(
    flag_key: str,
    payload: FlagPatch,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_admin_user),
):
    if flag_key not in FLAGS_META:
        raise HTTPException(status_code=404, detail="Flag not found")
    flag = (await db.execute(select(FeatureFlag).where(FeatureFlag.key == flag_key))).scalar_one_or_none()
    if flag is None:
        flag = FeatureFlag(key=flag_key, description=FLAGS_META[flag_key], enabled=False)
        db.add(flag)
        await db.flush()
    previous = bool(flag.enabled)
    flag.enabled = payload.enabled
    flag.description = FLAGS_META[flag_key]
    flag.updated_by = actor.email or f"user:{actor.id}"
    flag.updated_at = datetime.utcnow()
    db.add(
        FeatureFlagChange(
            flag_key=flag_key,
            previous_enabled=previous,
            new_enabled=payload.enabled,
            actor_email=actor.email or f"user:{actor.id}",
            reason=payload.reason,
        )
    )
    await db.commit()
    await cache.set(f"feature:{flag_key}", "true" if payload.enabled else "false")
    await append_admin_log(db, actor.email or f"user:{actor.id}", "flag_patch", flag_key, details={"enabled": payload.enabled, "reason": payload.reason})
    return FlagOut(
        key=flag_key,
        description=FLAGS_META[flag_key],
        enabled=payload.enabled,
        updated_at=flag.updated_at,
        updated_by=flag.updated_by,
    )
