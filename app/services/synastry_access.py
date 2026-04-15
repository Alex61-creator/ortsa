"""
Сервис контроля доступа к синастрии.

Логика анти-абьюза:
1. has_synastry_access — пользователь должен иметь активный тариф с синастрией
2. check_pair_quota    — не превышен лимит активных синастрий
3. check_regen_cooldown — не нарушен cooldown между регенерациями
4. input_hash_unchanged — данные не изменились → вернуть кэш
5. check_bundle_regen_limit — для bundle: не более 2 генераций
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.tariffs import (
    SYNASTRY_ACCESS_CODES,
    SYNASTRY_MAX_REGEN_BUNDLE,
    has_synastry_access,
    synastry_max_pairs,
    synastry_regen_cooldown_hours,
)
from app.models.natal_data import NatalData
from app.models.synastry_report import SynastryReport
from app.models.subscription import Subscription
from app.models.order import Order, OrderStatus
from app.models.tariff import Tariff


# ── Хэш входных данных ────────────────────────────────────────────────────────

def compute_input_hash(nd1: NatalData, nd2: NatalData) -> str:
    """MD5 двух натальных профилей — используется для dedup."""
    data = {
        "p1": {
            "id": nd1.id,
            "birth_date": nd1.birth_date.isoformat(),
            "birth_time": nd1.birth_time.isoformat(),
            "lat": nd1.lat,
            "lon": nd1.lon,
            "tz": nd1.timezone,
            "house_system": nd1.house_system,
        },
        "p2": {
            "id": nd2.id,
            "birth_date": nd2.birth_date.isoformat(),
            "birth_time": nd2.birth_time.isoformat(),
            "lat": nd2.lat,
            "lon": nd2.lon,
            "tz": nd2.timezone,
            "house_system": nd2.house_system,
        },
    }
    raw = json.dumps(data, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()


# ── Определение активного тарифа ─────────────────────────────────────────────

async def get_synastry_tariff_code(user_id: int, db: AsyncSession) -> Optional[str]:
    """
    Возвращает код тарифа, дающего доступ к синастрии, или None.
    Проверяет: активная подписка → завершённый заказ на bundle/sub_*.
    """
    # 1. Активная подписка
    sub_stmt = (
        select(Subscription)
        .join(Tariff, Tariff.id == Subscription.tariff_id)
        .where(
            Subscription.user_id == user_id,
            Subscription.status == "active",
            Tariff.code.in_(SYNASTRY_ACCESS_CODES),
        )
        .limit(1)
    )
    sub_result = await db.execute(sub_stmt)
    sub = sub_result.scalar_one_or_none()
    if sub:
        tariff_stmt = select(Tariff).where(Tariff.id == sub.tariff_id)
        tariff_result = await db.execute(tariff_stmt)
        tariff = tariff_result.scalar_one_or_none()
        if tariff:
            return tariff.code

    # 2. Завершённый заказ (bundle — разовая покупка)
    order_stmt = (
        select(Order)
        .join(Tariff, Tariff.id == Order.tariff_id)
        .where(
            Order.user_id == user_id,
            Order.status == OrderStatus.COMPLETED,
            Tariff.code.in_(SYNASTRY_ACCESS_CODES),
        )
        .order_by(Order.created_at.desc())
        .limit(1)
    )
    order_result = await db.execute(order_stmt)
    order = order_result.scalar_one_or_none()
    if order:
        tariff_stmt = select(Tariff).where(Tariff.id == order.tariff_id)
        tariff_result = await db.execute(tariff_stmt)
        tariff = tariff_result.scalar_one_or_none()
        if tariff:
            return tariff.code

    return None


# ── Проверки доступа ──────────────────────────────────────────────────────────

async def require_synastry_access(user_id: int, db: AsyncSession) -> str:
    """
    Возвращает код тарифа или выбрасывает HTTP 403.
    """
    code = await get_synastry_tariff_code(user_id, db)
    if not code:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Синастрия доступна на тарифах: Набор 3, Astro Pro месяц, Astro Pro год.",
        )
    return code


async def check_pair_quota(user_id: int, tariff_code: str, db: AsyncSession) -> None:
    """
    Проверяет лимит активных синастрий.
    Выбрасывает HTTP 429 при превышении.
    """
    max_pairs = synastry_max_pairs(tariff_code)
    if max_pairs == 0:
        raise HTTPException(status_code=403, detail="Синастрия недоступна для вашего тарифа.")

    count_stmt = select(func.count()).where(
        SynastryReport.user_id == user_id,
    )
    count_result = await db.execute(count_stmt)
    count = count_result.scalar_one()

    if count >= max_pairs:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Лимит синастрий для вашего тарифа: {max_pairs}. "
                "Удалите одну из существующих, чтобы создать новую."
            ),
        )


async def check_regen_cooldown(report: SynastryReport, tariff_code: str) -> None:
    """
    Проверяет cooldown для регенерации.
    Выбрасывает HTTP 429 с деталями ожидания.
    """
    if report.next_regen_allowed_at is None:
        return

    now = datetime.now(timezone.utc)
    # Нормализуем timezone
    nra = report.next_regen_allowed_at
    if nra.tzinfo is None:
        nra = nra.replace(tzinfo=timezone.utc)

    if now < nra:
        wait_seconds = int((nra - now).total_seconds())
        wait_hours = max(1, wait_seconds // 3600)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Следующая регенерация будет доступна через ~{wait_hours} ч. "
                f"(через {wait_seconds} сек.)"
            ),
            headers={"Retry-After": str(wait_seconds)},
        )


def check_bundle_regen_limit(report: SynastryReport, tariff_code: str) -> None:
    """
    Для bundle: ограничение на общее число генераций.
    """
    if tariff_code != "bundle":
        return
    if report.generation_count >= SYNASTRY_MAX_REGEN_BUNDLE:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"На тарифе «Набор 3» допустимо не более {SYNASTRY_MAX_REGEN_BUNDLE} "
                "генераций синастрии для одной пары."
            ),
        )


def next_regen_allowed(tariff_code: str) -> datetime:
    """Вычисляет время следующей допустимой регенерации."""
    hours = synastry_regen_cooldown_hours(tariff_code)
    return datetime.now(timezone.utc) + timedelta(hours=hours)
