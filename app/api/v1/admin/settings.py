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


# ── LLM провайдеры ────────────────────────────────────────────────────────────

_LLM_PROVIDER_KEYS = ["claude", "grok", "deepseek"]
_LLM_ENABLED_KEY = "llm_provider_{provider}_enabled"
_LLM_FALLBACK_ORDER_KEY = "llm_fallback_order"


async def _upsert_setting(db: AsyncSession, key: str, value: str, description: str = "") -> None:
    result = await db.execute(select(AppSettings).where(AppSettings.key == key))
    row = result.scalar_one_or_none()
    if row:
        row.value = value
        row.updated_at = datetime.utcnow()
    else:
        db.add(AppSettings(key=key, value=value, description=description))


@router.get(
    "/llm-providers",
    response_model=None,
    summary="LLM: список провайдеров и статус",
)
async def list_llm_providers(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    from app.schemas.admin_extra import LlmProviderConfig, LlmProvidersOut

    keys_needed = [_LLM_ENABLED_KEY.format(provider=p) for p in _LLM_PROVIDER_KEYS] + [_LLM_FALLBACK_ORDER_KEY]
    result = await db.execute(select(AppSettings).where(AppSettings.key.in_(keys_needed)))
    rows = {r.key: r.value for r in result.scalars().all()}

    raw_order = rows.get(_LLM_FALLBACK_ORDER_KEY, ",".join(_LLM_PROVIDER_KEYS))
    fallback_order = [p.strip() for p in raw_order.split(",") if p.strip()]

    providers = []
    for idx, p in enumerate(fallback_order):
        enabled_key = _LLM_ENABLED_KEY.format(provider=p)
        enabled = rows.get(enabled_key, "false").lower() == "true"
        providers.append(LlmProviderConfig(provider=p, enabled=enabled, order_index=idx))

    # Добавляем провайдеры не из fallback_order (если вдруг есть)
    in_order = {p.provider for p in providers}
    for p in _LLM_PROVIDER_KEYS:
        if p not in in_order:
            enabled_key = _LLM_ENABLED_KEY.format(provider=p)
            enabled = rows.get(enabled_key, "false").lower() == "true"
            providers.append(LlmProviderConfig(provider=p, enabled=enabled, order_index=len(providers)))

    return LlmProvidersOut(providers=providers, fallback_order=fallback_order)


class LlmProviderToggleInBody(BaseModel):
    enabled: bool


class LlmFallbackOrderInBody(BaseModel):
    order: list[str]


@router.put(
    "/llm-providers/{provider}/toggle",
    response_model=None,
    summary="LLM: вкл/выкл провайдер",
)
async def toggle_llm_provider(
    provider: str,
    payload: LlmProviderToggleInBody,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    from app.schemas.admin_extra import LlmProviderConfig

    if provider not in _LLM_PROVIDER_KEYS:
        raise HTTPException(status_code=404, detail=f"Провайдер '{provider}' не поддерживается.")

    key = _LLM_ENABLED_KEY.format(provider=provider)
    value = "true" if payload.enabled else "false"
    await _upsert_setting(db, key, value, f"Провайдер {provider} включён")
    await db.commit()

    from app.services.llm_router import invalidate_router_cache
    await invalidate_router_cache()

    return LlmProviderConfig(provider=provider, enabled=payload.enabled, order_index=0)


@router.put(
    "/llm-providers/order",
    response_model=None,
    summary="LLM: изменить порядок fallback",
)
async def set_llm_fallback_order(
    payload: LlmFallbackOrderInBody,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    unknown = [p for p in payload.order if p not in _LLM_PROVIDER_KEYS]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Неизвестные провайдеры: {unknown}")
    if not payload.order:
        raise HTTPException(status_code=400, detail="order не может быть пустым")

    value = ",".join(payload.order)
    await _upsert_setting(db, _LLM_FALLBACK_ORDER_KEY, value, "Порядок fallback LLM-провайдеров")
    await db.commit()

    from app.services.llm_router import invalidate_router_cache
    await invalidate_router_cache()

    return {"fallback_order": payload.order}
