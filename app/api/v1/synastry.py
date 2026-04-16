"""API для синастрии (совместность двух натальных карт)."""

from __future__ import annotations

import structlog
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.natal_data import NatalData
from app.models.order import Order, OrderStatus
from app.models.synastry_report import SynastryReport, SynastryStatus
from app.models.tariff import Tariff
from app.models.user import User
from app.services.payment import YookassaPaymentService
from app.services.storage import StorageService
from app.services.synastry_access import (
    check_generating_lock,
    compute_input_hash,
    get_synastry_quota_info,
    require_synastry_access,
)
from app.constants.tariffs import REPORT_RETENTION_DAYS_BY_CODE
from app.tasks.synastry_generation import generate_synastry_task

logger = structlog.get_logger(__name__)

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
    pdf_ready: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SynastryQuotaOut(BaseModel):
    tariff_code: str
    has_access: bool
    is_unlimited: bool
    synastries_created: int
    free_total: int          # -1 = безлимитно, 0 = нет, N = количество
    admin_extra_free: int    # дополнительные от администратора
    purchased_credits: int   # куплено через synastry_addon
    total_allowed: int       # free_total + admin_extra_free + purchased_credits (-1 = unlimited)
    requires_payment: bool   # нужна оплата для следующей синастрии
    repeat_price: str        # цена дополнительной синастрии (строка "190.00")
    is_generating: bool      # идёт ли сейчас генерация


class SynastryPurchaseOut(BaseModel):
    order_id: int
    payment_url: str


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
    info = await get_synastry_quota_info(current_user.id, db)
    return SynastryQuotaOut(**info)


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
        nd1_stmt = select(NatalData).where(NatalData.id == rep.natal_data_id_1)
        nd2_stmt = select(NatalData).where(NatalData.id == rep.natal_data_id_2)
        nd1 = (await db.execute(nd1_stmt)).scalar_one_or_none()
        nd2 = (await db.execute(nd2_stmt)).scalar_one_or_none()
        out.append(_enrich_out(rep, nd1, nd2))
    return out


@router.post("/purchase", response_model=SynastryPurchaseOut)
async def purchase_synastry(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Оплатить дополнительную синастрию (190 ₽) через ЮKassa.

    Доступно пользователям с тарифом bundle, исчерпавшим бесплатные синастрии.
    Возвращает ссылку на оплату. После успешной оплаты webhook отмечает заказ
    как COMPLETED, и кредит автоматически учитывается в quota.
    """
    # Проверяем наличие доступа (без него покупка бессмысленна)
    await require_synastry_access(current_user.id, db)

    # Загружаем тариф synastry_addon
    tariff_result = await db.execute(
        select(Tariff).where(Tariff.code == "synastry_addon")
    )
    tariff = tariff_result.scalar_one_or_none()
    if not tariff:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Тариф synastry_addon не найден. Обратитесь в поддержку.",
        )

    # Создаём заказ
    order = Order(
        user_id=current_user.id,
        natal_data_id=None,
        tariff_id=tariff.id,
        status=OrderStatus.PENDING,
        amount=tariff.price,
        report_delivery_email=current_user.email,
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    # Инициируем оплату
    payment_service = YookassaPaymentService()
    try:
        payment = await payment_service.create_payment(
            order_id=order.id,
            amount=order.amount,
            description="Дополнительная синастрия — AstroGen",
            user_email=current_user.email,
            metadata={"order_id": str(order.id)},
        )
    except Exception as exc:
        logger.exception(
            "YooKassa create_payment failed for synastry purchase",
            order_id=order.id,
            user_id=current_user.id,
            error=str(exc),
        )
        order.status = OrderStatus.FAILED_TO_INIT_PAYMENT
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Не удалось инициировать платёж. Попробуйте ещё раз.",
        )

    payment_url = payment.get("confirmation_url", "")
    if not payment_url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Платёжный сервис не вернул ссылку на оплату.",
        )

    return SynastryPurchaseOut(order_id=order.id, payment_url=payment_url)


@router.post("", response_model=SynastryOut, status_code=status.HTTP_201_CREATED)
async def create_synastry(
    payload: SynastryCreatePayload,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Создать новую синастрию.
    Запускает Celery-задачу генерации.

    Блокирует создание, если уже идёт генерация другой синастрии (анти-DDoS).
    Блокирует создание, если нужна оплата (bundle + лимит исчерпан).
    """
    tariff_code = await require_synastry_access(current_user.id, db)

    # Проверяем квоту: если нужна оплата — отказываем с HTTP 402
    quota = await get_synastry_quota_info(current_user.id, db)
    if quota["requires_payment"]:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "message": (
                    "Бесплатные синастрии по вашему тарифу исчерпаны. "
                    "Оплатите дополнительную синастрию, чтобы продолжить."
                ),
                "repeat_price": quota["repeat_price"],
            },
        )

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

    # Анти-DDoS: блокируем, пока идёт генерация
    await check_generating_lock(current_user.id, db)

    locale = payload.locale or "ru"

    report = SynastryReport(
        user_id=current_user.id,
        natal_data_id_1=id1,
        natal_data_id_2=id2,
        status=SynastryStatus.PENDING,
        locale=locale,
        generation_count=0,
        retention_days=REPORT_RETENTION_DAYS_BY_CODE.get(tariff_code, 30),
        expires_at=datetime.now(timezone.utc) + timedelta(days=REPORT_RETENTION_DAYS_BY_CODE.get(tariff_code, 30)),
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

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

    Единственная защита: данные не изменились (hash-dedup) и анти-DDoS блокировка.
    Cooldown убран — регистрация платная, ограничений по времени нет.
    """
    tariff_code = await require_synastry_access(current_user.id, db)

    stmt = select(SynastryReport).where(
        SynastryReport.id == synastry_id,
        SynastryReport.user_id == current_user.id,
    )
    report = (await db.execute(stmt)).scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Синастрия не найдена.")

    if report.status in (SynastryStatus.PROCESSING, SynastryStatus.PENDING):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Генерация уже выполняется. Пожалуйста, подождите.",
        )

    nd1_stmt = select(NatalData).where(NatalData.id == report.natal_data_id_1)
    nd2_stmt = select(NatalData).where(NatalData.id == report.natal_data_id_2)
    nd1 = (await db.execute(nd1_stmt)).scalar_one_or_none()
    nd2 = (await db.execute(nd2_stmt)).scalar_one_or_none()

    if not nd1 or not nd2:
        raise HTTPException(status_code=404, detail="Натальные данные не найдены.")

    # Hash-dedup: данные не изменились
    current_hash = compute_input_hash(nd1, nd2)
    if report.input_hash == current_hash and report.pdf_path:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Данные партнёров не изменились. "
                "Отредактируйте дату, время или место рождения, чтобы получить новый отчёт."
            ),
        )

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

    storage = StorageService()
    pdf_path = storage.resolve_path(report.pdf_path)
    if not pdf_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл PDF не найден на сервере.",
        )
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
    """Удалить синастрию."""
    stmt = select(SynastryReport).where(
        SynastryReport.id == synastry_id,
        SynastryReport.user_id == current_user.id,
    )
    report = (await db.execute(stmt)).scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Синастрия не найдена.")

    await db.delete(report)
    await db.commit()
