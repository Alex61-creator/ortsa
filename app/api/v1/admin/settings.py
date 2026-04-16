"""Глобальные настройки приложения — admin API."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user
from app.db.session import get_db
from app.models.app_settings import AppSettings
from app.models.user import User

router = APIRouter()


# Допустимые ключи настроек и их описания
KNOWN_SETTINGS: dict[str, str] = {
    "synastry_repeat_price": "Цена повторного / дополнительного отчёта синастрии (руб.)",
    "report_option_price_partnership": "Цена тумблера «Партнёрство» для report/bundle (руб.)",
    "report_option_price_children_parenting": "Цена тумблера «Дети и родительская роль» (руб.)",
    "report_option_price_career": "Цена тумблера «Карьера и реализация» (руб.)",
    "report_option_price_money_boundaries": "Цена тумблера «Деньги, границы, опора» (руб.)",
    "report_option_multi_discount_percent": "Скидка % на сумму тумблеров при выборе 2+ (0–100)",
}


class SettingOut(BaseModel):
    key: str
    value: str
    description: str | None
    updated_at: datetime


class SettingPatch(BaseModel):
    value: str


@router.get("/", response_model=list[SettingOut], summary="Настройки: список")
async def list_settings(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    result = await db.execute(select(AppSettings))
    rows = result.scalars().all()
    existing = {r.key: r for r in rows}

    # Добавляем дефолтные если отсутствуют в БД
    out = []
    for key, desc in KNOWN_SETTINGS.items():
        if key in existing:
            row = existing[key]
            out.append(SettingOut(
                key=row.key,
                value=row.value,
                description=row.description or desc,
                updated_at=row.updated_at,
            ))
        else:
            out.append(SettingOut(
                key=key,
                value="",
                description=desc,
                updated_at=datetime.utcnow(),
            ))
    return out


@router.patch("/{key}", response_model=SettingOut, summary="Настройки: обновить")
async def update_setting(
    key: str,
    payload: SettingPatch,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    if key not in KNOWN_SETTINGS:
        raise HTTPException(status_code=404, detail=f"Настройка '{key}' не найдена.")

    result = await db.execute(select(AppSettings).where(AppSettings.key == key))
    row = result.scalar_one_or_none()

    if row:
        row.value = payload.value
        row.updated_at = datetime.utcnow()
    else:
        row = AppSettings(
            key=key,
            value=payload.value,
            description=KNOWN_SETTINGS[key],
        )
        db.add(row)

    await db.commit()
    await db.refresh(row)
    return SettingOut(
        key=row.key,
        value=row.value,
        description=row.description,
        updated_at=row.updated_at,
    )
