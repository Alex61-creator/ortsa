"""API для синастрии (совместность двух натальных карт)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.natal_data import NatalData
from app.models.synastry_report import SynastryReport, SynastryStatus
from app.models.user import User
from app.services.synastry_access import (
    check_bundle_regen_limit,
    check_pair_quota,
    check_regen_cooldown,
    compute_input_hash,
    next_regen_allowed,
    require_synastry_access,
)
from app.tasks.synastry_generation import generate_synastry_task

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class SynastryCreatePayload(BaseModel):
    natal_data_id_1: int = Field(..., description="Натальный профиль первого человека")
    natal_data_id_2: int = Field(..., description="Натальный профиль второго человека")
    locale: Optional[str] = Field(default="ru", pattern="^(ru|en)$")


class SynastryOut(BaseModel):
    id: int
    natal_data_id_1: int
    natal_data_id_2: int
    person1_name: Optional[str] = None
    person2_name: Optional[str] = None
    status: str
    locale: str
    generation_count: int
    last_generated_at: Optional[datetime] = None
    next_regen_allowed_at: Optional[datetime] = None
    pdf_ready: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SynastryQuotaOut(BaseModel):
    tariff_code: str
    pairs_used: int
    pairs_max: int
    has_access: bool


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_natal_data_for_user(
    natal_id: int,
    user_id: int,
    db: AsyncSession,
) -> NatalData:
    """Загружает натальный профиль и проверяет владельца."""
    stmt = select(NatalData).where(
        NatalData.id == natal_id,
        NatalData.user_id == user_id,
    )
    result = await db.execute(stmt)
    nd = result.scalar_one_or_none()
    if nd is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Натальный профиль #{natal_id} не найден.",
        )
    return nd


def _enrich_out(report: SynastryReport, nd1: NatalData | None, nd2: NatalData | None) -> SynastryOut:
    return SynastryOut(
        id=report.id,
        natal_data_id_1=report.natal_data_id_1,
        natal_data_id_2=report.natal_data_id_2,
        person1_name=nd1.full_name if nd1 else None,
        person2_name=nd2.full_name if nd2 else None,
        status=report.status,
        locale=report.locale,
        generation_count=report.generation_count,
        last_generated_at=report.last_generated_at,
        next_regen_allowed_at=report.next_regen_allowed_at,
        pdf_ready=bool(report.pdf_path and report.status == SynastryStatus.COMPLETED),
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/quota", response_model=SynastryQuotaOut)
async def get_synastry_quota(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Проверить доступ и лимиты синастрии для текущего пользователя."""
    from app.services.synastry_access import get_synastry_tariff_code
    from app.constants.tariffs import synastry_max_pairs, has_synastry_access
    from sqlalchemy import func

    tariff_code = await get_synastry_tariff_code(current_user.id, db)
    has_access = tariff_code is not None

    count_result = await db.execute(
        select(func.count()).where(SynastryReport.user_id == current_user.id)
    )
    pairs_used = count_result.scalar_one()
    pairs_max = synastry_max_pairs(tariff_code) if tariff_code else 0

    return SynastryQuotaOut(
        tariff_code=tariff_code or "",
        pairs_used=pairs_used,
        pairs_max=pairs_max,
        has_access=has_access,
    )


@router.get("", response_model=List[SynastryOut])
async def list_synastry_reports(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Список синастрий текущего пользователя."""
    stmt = (
        select(SynastryReport)
        .where(SynastryReport.user_id == current_user.id)
        .order_by(SynastryReport.created_at.desc())
    )
    result = await db.execute(stmt)
    reports = result.scalars().all()

    out = []
    for rep in reports:
        # Загружаем имена
        nd1_stmt = select(NatalData).where(NatalData.id == rep.natal_data_id_1)
        nd2_stmt = select(NatalData).where(NatalData.id == rep.natal_data_id_2)
        nd1 = (await db.execute(nd1_stmt)).scalar_one_or_none()
        nd2 = (await db.execute(nd2_stmt)).scalar_one_or_none()
        out.append(_enrich_out(rep, nd1, nd2))
    return out


@router.post("", response_model=SynastryOut, status_code=status.HTTP_201_CREATED)
async def create_synastry(
    payload: SynastryCreatePayload,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Создать новую синастрию.
    Запускает Celery-задачу генерации.
    """
    tariff_code = await require_synastry_access(current_user.id, db)

    if payload.natal_data_id_1 == payload.natal_data_id_2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Оба профиля должны быть разными людьми.",
        )

    nd1 = await _get_natal_data_for_user(payload.natal_data_id_1, current_user.id, db)
    nd2 = await _get_natal_data_for_user(payload.natal_data_id_2, current_user.id, db)

    # Нормализуем порядок: id_1 < id_2
    id1, id2 = sorted([nd1.id, nd2.id])
    nd1, nd2 = (nd1, nd2) if nd1.id == id1 else (nd2, nd1)

    # Проверяем, не существует ли уже такая пара
    existing_stmt = select(SynastryReport).where(
        SynastryReport.user_id == current_user.id,
        SynastryReport.natal_data_id_1 == id1,
        SynastryReport.natal_data_id_2 == id2,
    )
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Синастрия для этой пары уже существует. Используйте /regenerate для обновления.",
        )

    # Проверяем квоту
    await check_pair_quota(current_user.id, tariff_code, db)

    locale = payload.locale or "ru"

    report = SynastryReport(
        user_id=current_user.id,
        natal_data_id_1=id1,
        natal_data_id_2=id2,
        status=SynastryStatus.PENDING,
        locale=locale,
        generation_count=0,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    # Запускаем задачу
    generate_synastry_task.delay(report.id, tariff_code)

    return _enrich_out(report, nd1, nd2)


@router.get("/{synastry_id}", response_model=SynastryOut)
async def get_synastry(
    synastry_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить статус и данные синастрии."""
    stmt = select(SynastryReport).where(
        SynastryReport.id == synastry_id,
        SynastryReport.user_id == current_user.id,
    )
    report = (await db.execute(stmt)).scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Синастрия не найдена.")

    nd1_stmt = select(NatalData).where(NatalData.id == report.natal_data_id_1)
    nd2_stmt = select(NatalData).where(NatalData.id == report.natal_data_id_2)
    nd1 = (await db.execute(nd1_stmt)).scalar_one_or_none()
    nd2 = (await db.execute(nd2_stmt)).scalar_one_or_none()
    return _enrich_out(report, nd1, nd2)


@router.post("/{synastry_id}/regenerate", response_model=SynastryOut)
async def regenerate_synastry(
    synastry_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Запросить регенерацию синастрии.

    Anti-abuse checks:
    1. Данные не изменились → возвращаем статус completed, без новой генерации
    2. Cooldown не истёк → HTTP 429 с Retry-After
    3. Bundle лимит → HTTP 429 при исчерпании
    """
    tariff_code = await require_synastry_access(current_user.id, db)

    stmt = select(SynastryReport).where(
        SynastryReport.id == synastry_id,
        SynastryReport.user_id == current_user.id,
    )
    report = (await db.execute(stmt)).scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Синастрия не найдена.")

    if report.status == SynastryStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Генерация уже выполняется. Пожалуйста, подождите.",
        )

    # Загружаем данные пар
    nd1_stmt = select(NatalData).where(NatalData.id == report.natal_data_id_1)
    nd2_stmt = select(NatalData).where(NatalData.id == report.natal_data_id_2)
    nd1 = (await db.execute(nd1_stmt)).scalar_one_or_none()
    nd2 = (await db.execute(nd2_stmt)).scalar_one_or_none()

    if not nd1 or not nd2:
        raise HTTPException(status_code=404, detail="Натальные данные не найдены.")

    # ── Anti-abuse ─────────────────────────────────────────────────────────

    # 1. Hash dedup — данные не изменились?
    current_hash = compute_input_hash(nd1, nd2)
    if report.input_hash == current_hash and report.pdf_path:
        # Возвращаем текущий статус — нет смысла регенерировать
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Данные партнёров не изменились. "
                "Отредактируйте дату, время или место рождения, чтобы получить новый отчёт."
            ),
        )

    # 2. Cooldown
    await check_regen_cooldown(report, tariff_code)

    # 3. Bundle лимит генераций
    check_bundle_regen_limit(report, tariff_code)

    # ── Запуск генерации ───────────────────────────────────────────────────
    report.status = SynastryStatus.PENDING
    await db.commit()
    await db.refresh(report)

    generate_synastry_task.delay(report.id, tariff_code)

    return _enrich_out(report, nd1, nd2)


@router.get("/{synastry_id}/download")
async def download_synastry_pdf(
    synastry_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Скачать PDF-отчёт синастрии."""
    stmt = select(SynastryReport).where(
        SynastryReport.id == synastry_id,
        SynastryReport.user_id == current_user.id,
        SynastryReport.status == SynastryStatus.COMPLETED,
    )
    report = (await db.execute(stmt)).scalar_one_or_none()
    if not report or not report.pdf_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF ещё не готов или синастрия не найдена.",
        )

    pdf_path = Path(report.pdf_path)
    if not pdf_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл PDF не найден на сервере.",
        )

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=f"synastry_{synastry_id}.pdf",
    )


@router.delete("/{synastry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_synastry(
    synastry_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Удалить синастрию (освобождает слот квоты)."""
    stmt = select(SynastryReport).where(
        SynastryReport.id == synastry_id,
        SynastryReport.user_id == current_user.id,
    )
    report = (await db.execute(stmt)).scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Синастрия не найдена.")

    await db.delete(report)
    await db.commit()
