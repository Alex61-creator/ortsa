from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func

from app.db.session import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.natal_data import NatalData
from app.schemas.natal import NatalDataCreate, NatalDataUpdate, NatalDataOut
from app.utils.sanitize import sanitize_string
from app.services.natal_limits import get_effective_max_natal_profiles

router = APIRouter()

@router.post("/", response_model=NatalDataOut)
async def create_natal_data(
    data: NatalDataCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not current_user.consent_given_at and not data.accept_privacy_policy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Privacy policy must be accepted",
        )
    if data.accept_privacy_policy:
        current_user.consent_given_at = datetime.now(timezone.utc)

    count_stmt = select(func.count()).select_from(NatalData).where(NatalData.user_id == current_user.id)
    existing_n = (await db.execute(count_stmt)).scalar_one()
    max_profiles = await get_effective_max_natal_profiles(db, current_user.id)
    if existing_n >= max_profiles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Достигнут лимит сохранённых карт ({max_profiles}). "
                "Оформите тариф с большим числом профилей или удалите лишнюю карту."
            ),
        )

    sanitized_name = sanitize_string(data.full_name)
    sanitized_place = sanitize_string(data.birth_place)

    natal = NatalData(
        user_id=current_user.id,
        full_name=sanitized_name,
        birth_date=data.birth_date,
        birth_time=data.birth_time,
        birth_place=sanitized_place,
        lat=data.lat,
        lon=data.lon,
        timezone=data.timezone,
        house_system=data.house_system,
        report_locale=data.report_locale,
    )
    db.add(natal)
    await db.commit()
    await db.refresh(natal)
    return natal

@router.get("/", response_model=list[NatalDataOut])
async def list_natal_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    stmt = select(NatalData).where(NatalData.user_id == current_user.id).order_by(NatalData.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/{natal_id}", response_model=NatalDataOut)
async def get_natal_data(
    natal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    stmt = select(NatalData).where(NatalData.id == natal_id, NatalData.user_id == current_user.id)
    result = await db.execute(stmt)
    natal = result.scalar_one_or_none()
    if not natal:
        raise HTTPException(status_code=404, detail="Not found")
    return natal

@router.patch("/{natal_id}", response_model=NatalDataOut)
async def update_natal_data(
    natal_id: int,
    update: NatalDataUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    stmt = select(NatalData).where(NatalData.id == natal_id, NatalData.user_id == current_user.id)
    result = await db.execute(stmt)
    natal = result.scalar_one_or_none()
    if not natal:
        raise HTTPException(status_code=404, detail="Not found")

    update_data = update.dict(exclude_unset=True)
    if "full_name" in update_data:
        update_data["full_name"] = sanitize_string(update_data["full_name"])
    if "birth_place" in update_data:
        update_data["birth_place"] = sanitize_string(update_data["birth_place"])

    for field, value in update_data.items():
        setattr(natal, field, value)

    await db.commit()
    await db.refresh(natal)
    return natal

@router.delete("/{natal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_natal_data(
    natal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    stmt = delete(NatalData).where(NatalData.id == natal_id, NatalData.user_id == current_user.id)
    result = await db.execute(stmt)
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Not found")
    await db.commit()
    return