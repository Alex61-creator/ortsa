"""
Сервис контроля доступа к синастрии.

Логика доступа (упрощена — cooldown убран, т.к. регистрация платная):
1. get_synastry_tariff_code   — определяет активный тариф с синастрией
2. get_synastry_override      — проверяет per-user override от администратора
3. require_synastry_access    — возвращает тариф или бросает HTTP 403
4. check_generating_lock      — анти-DDoS: нельзя создать новую, пока идёт генерация
5. get_synastry_repeat_price  — читает цену доп. синастрии из app_settings

Тарифная модель:
- sub_monthly / sub_annual / pro  → безлимитные синастрии
- bundle                          → 1 бесплатная, далее за деньги
- free / report                   → нет доступа (только через admin override)
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.tariffs import (
    SYNASTRY_ACCESS_CODES,
    SYNASTRY_REPEAT_PRICE_DEFAULT,
    SYNASTRY_REPEAT_PRICE_KEY,
    is_synastry_unlimited,
    synastry_free_count,
)
from app.models.app_settings import AppSettings
from app.models.natal_data import NatalData
from app.models.order import Order, OrderStatus
from app.models.subscription import Subscription
from app.models.synastry_report import SynastryReport, SynastryStatus
from app.models.tariff import Tariff
from app.models.user_synastry_override import UserSynastryOverride


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


# ── Per-user override ─────────────────────────────────────────────────────────

async def get_synastry_override(user_id: int, db: AsyncSession) -> Optional[UserSynastryOverride]:
    """Возвращает override-запись для пользователя или None."""
    result = await db.execute(
        select(UserSynastryOverride).where(UserSynastryOverride.user_id == user_id)
    )
    return result.scalar_one_or_none()


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


# ── Цена повторной синастрии ──────────────────────────────────────────────────

async def get_synastry_repeat_price(db: AsyncSession) -> Decimal:
    """Читает цену дополнительной синастрии из app_settings."""
    result = await db.execute(
        select(AppSettings).where(AppSettings.key == SYNASTRY_REPEAT_PRICE_KEY)
    )
    row = result.scalar_one_or_none()
    if row:
        try:
            return Decimal(row.value)
        except Exception:
            pass
    return Decimal(SYNASTRY_REPEAT_PRICE_DEFAULT)


# ── Проверки доступа ──────────────────────────────────────────────────────────

async def require_synastry_access(user_id: int, db: AsyncSession) -> str:
    """
    Возвращает код тарифа или бросает HTTP 403.
    Учитывает per-user override от администратора.
    """
    # Проверяем per-user override
    override = await get_synastry_override(user_id, db)
    if override and override.synastry_enabled:
        # Возвращаем код виртуального "admin_override" тарифа
        return "admin_override"

    code = await get_synastry_tariff_code(user_id, db)
    if not code:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Синастрия доступна на тарифах: Набор 3, Astro Pro (месяц), Astro Pro (год). "
                "Вы также можете купить дополнительные синастрии отдельно."
            ),
        )
    return code


async def check_generating_lock(user_id: int, db: AsyncSession) -> None:
    """
    Анти-DDoS: запрещает создание новой синастрии, пока идёт генерация текущей.
    Бросает HTTP 409 при нарушении.
    """
    active_stmt = select(func.count()).where(
        SynastryReport.user_id == user_id,
        SynastryReport.status.in_([SynastryStatus.PENDING, SynastryStatus.PROCESSING]),
    )
    active_result = await db.execute(active_stmt)
    active_count = active_result.scalar_one()

    if active_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Дождитесь завершения текущей генерации синастрии, "
                "прежде чем создавать новую."
            ),
        )


async def get_purchased_synastry_credits(user_id: int, db: AsyncSession) -> int:
    """
    Считает кредиты синастрии, купленные через тариф synastry_addon.
    Каждый завершённый заказ с кодом synastry_addon = +1 синастрия.
    """
    stmt = (
        select(func.count())
        .select_from(Order)
        .join(Tariff, Tariff.id == Order.tariff_id)
        .where(
            Order.user_id == user_id,
            Order.status == OrderStatus.COMPLETED,
            Tariff.code == "synastry_addon",
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one()


async def get_synastry_quota_info(
    user_id: int,
    db: AsyncSession,
) -> dict:
    """
    Возвращает полную информацию о квоте синастрий для пользователя.

    Возвращаемый словарь:
    - tariff_code: str         — код тарифа (или "" если нет)
    - has_access: bool         — есть ли доступ
    - is_unlimited: bool       — безлимитный доступ (подписки)
    - synastries_created: int  — сколько синастрий создано
    - free_total: int          — бесплатных по тарифу (-1 = unlimited)
    - admin_extra_free: int    — дополнительные бесплатные от администратора
    - purchased_credits: int   — куплено через synastry_addon заказы
    - total_allowed: int       — free_total + admin_extra_free + purchased_credits
    - requires_payment: bool   — нужна оплата для следующей синастрии
    - repeat_price: str        — цена следующей синастрии ("190.00")
    - is_generating: bool      — идёт ли сейчас генерация
    """
    override = await get_synastry_override(user_id, db)
    override_enabled = bool(override and override.synastry_enabled)
    admin_extra_free = override.free_synastries_granted if override else 0

    tariff_code = await get_synastry_tariff_code(user_id, db)
    has_access = bool(tariff_code) or override_enabled

    effective_code = tariff_code or ("admin_override" if override_enabled else "")
    unlimited = is_synastry_unlimited(effective_code) or (override_enabled and not tariff_code)
    free_total = synastry_free_count(effective_code) if effective_code else 0

    # Купленные дополнительные кредиты (synastry_addon orders)
    purchased_credits = await get_purchased_synastry_credits(user_id, db)

    # Счётчик созданных синастрий
    count_result = await db.execute(
        select(func.count()).where(SynastryReport.user_id == user_id)
    )
    synastries_created = count_result.scalar_one()

    # Активная генерация
    gen_result = await db.execute(
        select(func.count()).where(
            SynastryReport.user_id == user_id,
            SynastryReport.status.in_([SynastryStatus.PENDING, SynastryStatus.PROCESSING]),
        )
    )
    is_generating = gen_result.scalar_one() > 0

    repeat_price = await get_synastry_repeat_price(db)

    # Для unlimited тарифов total_allowed = -1
    if unlimited:
        total_allowed = -1
        requires_payment = False
    else:
        total_allowed = free_total + admin_extra_free + purchased_credits
        requires_payment = has_access and (synastries_created >= total_allowed)

    return {
        "tariff_code": effective_code,
        "has_access": has_access,
        "is_unlimited": unlimited,
        "synastries_created": synastries_created,
        "free_total": free_total,
        "admin_extra_free": admin_extra_free,
        "purchased_credits": purchased_credits,
        "total_allowed": total_allowed,
        "requires_payment": requires_payment,
        "repeat_price": str(repeat_price),
        "is_generating": is_generating,
    }
