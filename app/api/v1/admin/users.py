from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user
from app.db.session import get_db
from app.models.natal_data import NatalData
from app.models.synastry_report import SynastryReport
from app.models.user import User
from app.models.user_synastry_override import UserSynastryOverride
from app.schemas.admin_user import AdminUserListItem, AdminUserOut

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class SynastryOverrideOut(BaseModel):
    user_id: int
    synastry_enabled: bool
    free_synastries_granted: int
    admin_note: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SynastryOverridePatch(BaseModel):
    synastry_enabled: Optional[bool] = None
    free_synastries_granted: Optional[int] = None
    admin_note: Optional[str] = None


class AdminSynastryReportOut(BaseModel):
    id: int
    natal_data_id_1: int
    natal_data_id_2: int
    person1_name: Optional[str]
    person2_name: Optional[str]
    status: str
    generation_count: int
    pdf_ready: bool
    created_at: datetime
    updated_at: datetime


# ── User list / detail / delete ───────────────────────────────────────────────

@router.get("/", response_model=list[AdminUserListItem], summary="Пользователи (админ)")
async def list_users_admin(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: Optional[str] = Query(None, description="Поиск по email"),
):
    stmt = select(User).order_by(User.created_at.desc())
    if q and q.strip():
        term = f"%{q.strip()}%"
        stmt = stmt.where(User.email.isnot(None)).where(User.email.ilike(term))
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{user_id}", response_model=AdminUserOut, summary="Пользователь по id (админ)")
async def get_user_admin(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.delete("/{user_id}", summary="Удалить пользователя (админ)")
async def delete_user_admin(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить свою учётную запись",
        )
    result = await db.execute(select(User).where(User.id == user_id))
    victim = result.scalar_one_or_none()
    if not victim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()
    return {"deleted": True, "user_id": user_id}


# ── Synastry override ─────────────────────────────────────────────────────────

@router.get(
    "/{user_id}/synastry/override",
    response_model=SynastryOverrideOut,
    summary="Получить override синастрии пользователя",
)
async def get_synastry_override_admin(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """Возвращает текущий override для пользователя (или дефолт если не установлен)."""
    _ensure_user_exists(user_id, await db.execute(select(User).where(User.id == user_id)))

    result = await db.execute(
        select(UserSynastryOverride).where(UserSynastryOverride.user_id == user_id)
    )
    override = result.scalar_one_or_none()

    if not override:
        return SynastryOverrideOut(
            user_id=user_id,
            synastry_enabled=False,
            free_synastries_granted=0,
            admin_note=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    return override


@router.patch(
    "/{user_id}/synastry/override",
    response_model=SynastryOverrideOut,
    summary="Обновить override синастрии пользователя",
)
async def patch_synastry_override_admin(
    user_id: int,
    payload: SynastryOverridePatch,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    Администратор может:
    - включить/выключить синастрию для любого пользователя
    - выдать дополнительные бесплатные генерации
    - добавить внутреннюю заметку
    """
    user_result = await db.execute(select(User).where(User.id == user_id))
    _ensure_user_exists(user_id, user_result)

    ov_result = await db.execute(
        select(UserSynastryOverride).where(UserSynastryOverride.user_id == user_id)
    )
    override = ov_result.scalar_one_or_none()

    if not override:
        override = UserSynastryOverride(
            user_id=user_id,
            synastry_enabled=False,
            free_synastries_granted=0,
        )
        db.add(override)

    if payload.synastry_enabled is not None:
        override.synastry_enabled = payload.synastry_enabled
    if payload.free_synastries_granted is not None:
        override.free_synastries_granted = max(0, payload.free_synastries_granted)
    if payload.admin_note is not None:
        override.admin_note = payload.admin_note or None

    await db.commit()
    await db.refresh(override)
    return override


# ── Synastry reports management ───────────────────────────────────────────────

@router.get(
    "/{user_id}/synastry/reports",
    response_model=list[AdminSynastryReportOut],
    summary="Список синастрий пользователя (админ)",
)
async def list_user_synastry_admin(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    user_result = await db.execute(select(User).where(User.id == user_id))
    _ensure_user_exists(user_id, user_result)

    stmt = (
        select(SynastryReport)
        .where(SynastryReport.user_id == user_id)
        .order_by(SynastryReport.created_at.desc())
    )
    result = await db.execute(stmt)
    reports = result.scalars().all()

    out = []
    for rep in reports:
        nd1 = (await db.execute(select(NatalData).where(NatalData.id == rep.natal_data_id_1))).scalar_one_or_none()
        nd2 = (await db.execute(select(NatalData).where(NatalData.id == rep.natal_data_id_2))).scalar_one_or_none()
        out.append(AdminSynastryReportOut(
            id=rep.id,
            natal_data_id_1=rep.natal_data_id_1,
            natal_data_id_2=rep.natal_data_id_2,
            person1_name=nd1.full_name if nd1 else None,
            person2_name=nd2.full_name if nd2 else None,
            status=rep.status,
            generation_count=rep.generation_count,
            pdf_ready=bool(rep.pdf_path and rep.status == "completed"),
            created_at=rep.created_at,
            updated_at=rep.updated_at,
        ))
    return out


@router.delete(
    "/{user_id}/synastry/reports/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить синастрию пользователя (админ)",
)
async def delete_user_synastry_admin(
    user_id: int,
    report_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    stmt = select(SynastryReport).where(
        SynastryReport.id == report_id,
        SynastryReport.user_id == user_id,
    )
    report = (await db.execute(stmt)).scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Синастрия не найдена.")
    await db.delete(report)
    await db.commit()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ensure_user_exists(user_id: int, result) -> None:
    """Проверяет, что пользователь существует (бросает 404 если нет)."""
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail=f"Пользователь #{user_id} не найден.")
