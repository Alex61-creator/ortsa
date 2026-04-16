"""Управление шаблонами системных промптов LLM (админ-панель)."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user
from app.constants.tariffs import CODE_TO_LLM_TIER, LlmTier, resolve_llm_tier
from app.db.session import get_db
from app.models.prompt_template import LlmPromptTemplate
from app.models.user import User
from app.services.llm import LLMService
from app.services.admin_logs import append_admin_log

router = APIRouter()

# Все поддерживаемые коды тарифов (без deprecated 'pro')
VALID_TARIFF_CODES = ["free", "report", "bundle", "sub_monthly", "sub_annual"]
VALID_LOCALES = ["ru", "en"]


class PromptTemplateOut(BaseModel):
    tariff_code: str
    locale: str
    system_prompt: str
    is_custom: bool  # True = сохранён в БД, False = захардкожен по умолчанию
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None

    class Config:
        from_attributes = True


class PromptTemplateUpdate(BaseModel):
    system_prompt: str


def _default_prompt(tariff_code: str, locale: str) -> str:
    """Возвращает захардкоженный промпт по умолчанию для данного тарифа и локали."""
    svc = LLMService.__new__(LLMService)  # без __init__ (не нужен клиент)
    tier = resolve_llm_tier(tariff_code, None)
    return svc.build_system_prompt(tier, locale)


@router.get(
    "/",
    response_model=list[PromptTemplateOut],
    summary="Список всех шаблонов промптов",
)
async def list_prompts(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
) -> list[PromptTemplateOut]:
    """Возвращает состояние промптов для всех тарифов × локалей.
    Если запись в БД отсутствует — возвращает значение по умолчанию с is_custom=False.
    """
    stmt = select(LlmPromptTemplate)
    result = await db.execute(stmt)
    stored: dict[tuple[str, str], LlmPromptTemplate] = {
        (r.tariff_code, r.locale): r for r in result.scalars().all()
    }

    out: list[PromptTemplateOut] = []
    for code in VALID_TARIFF_CODES:
        for locale in VALID_LOCALES:
            key = (code, locale)
            if key in stored:
                rec = stored[key]
                out.append(PromptTemplateOut(
                    tariff_code=code,
                    locale=locale,
                    system_prompt=rec.system_prompt,
                    is_custom=True,
                    updated_at=rec.updated_at,
                    updated_by=rec.updated_by,
                ))
            else:
                out.append(PromptTemplateOut(
                    tariff_code=code,
                    locale=locale,
                    system_prompt=_default_prompt(code, locale),
                    is_custom=False,
                ))
    return out


@router.get(
    "/{tariff_code}/{locale}",
    response_model=PromptTemplateOut,
    summary="Получить промпт для тарифа/локали",
)
async def get_prompt(
    tariff_code: str,
    locale: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
) -> PromptTemplateOut:
    if tariff_code not in VALID_TARIFF_CODES:
        raise HTTPException(status_code=404, detail=f"Unknown tariff code: {tariff_code}")
    if locale not in VALID_LOCALES:
        raise HTTPException(status_code=400, detail=f"Unsupported locale: {locale}")

    stmt = select(LlmPromptTemplate).where(
        LlmPromptTemplate.tariff_code == tariff_code,
        LlmPromptTemplate.locale == locale,
    )
    result = await db.execute(stmt)
    rec = result.scalar_one_or_none()
    if rec:
        return PromptTemplateOut(
            tariff_code=tariff_code,
            locale=locale,
            system_prompt=rec.system_prompt,
            is_custom=True,
            updated_at=rec.updated_at,
            updated_by=rec.updated_by,
        )
    return PromptTemplateOut(
        tariff_code=tariff_code,
        locale=locale,
        system_prompt=_default_prompt(tariff_code, locale),
        is_custom=False,
    )


@router.put(
    "/{tariff_code}/{locale}",
    response_model=PromptTemplateOut,
    summary="Сохранить / обновить промпт",
)
async def upsert_prompt(
    tariff_code: str,
    locale: str,
    body: PromptTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_admin_user),
) -> PromptTemplateOut:
    if tariff_code not in VALID_TARIFF_CODES:
        raise HTTPException(status_code=404, detail=f"Unknown tariff code: {tariff_code}")
    if locale not in VALID_LOCALES:
        raise HTTPException(status_code=400, detail=f"Unsupported locale: {locale}")
    if not body.system_prompt.strip():
        raise HTTPException(status_code=400, detail="system_prompt cannot be empty")

    stmt = select(LlmPromptTemplate).where(
        LlmPromptTemplate.tariff_code == tariff_code,
        LlmPromptTemplate.locale == locale,
    )
    result = await db.execute(stmt)
    rec = result.scalar_one_or_none()
    actor_label = actor.email or f"user:{actor.id}"

    if rec:
        rec.system_prompt = body.system_prompt
        rec.updated_at = datetime.now(timezone.utc)
        rec.updated_by = actor_label
    else:
        rec = LlmPromptTemplate(
            tariff_code=tariff_code,
            locale=locale,
            system_prompt=body.system_prompt,
            updated_at=datetime.now(timezone.utc),
            updated_by=actor_label,
        )
        db.add(rec)

    await db.commit()
    await db.refresh(rec)

    await append_admin_log(
        db,
        actor_label,
        "prompt_update",
        f"{tariff_code}/{locale}",
    )

    return PromptTemplateOut(
        tariff_code=tariff_code,
        locale=locale,
        system_prompt=rec.system_prompt,
        is_custom=True,
        updated_at=rec.updated_at,
        updated_by=rec.updated_by,
    )


@router.delete(
    "/{tariff_code}/{locale}",
    summary="Сбросить промпт к умолчанию",
    status_code=204,
)
async def reset_prompt(
    tariff_code: str,
    locale: str,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_admin_user),
) -> None:
    if tariff_code not in VALID_TARIFF_CODES:
        raise HTTPException(status_code=404, detail=f"Unknown tariff code: {tariff_code}")
    if locale not in VALID_LOCALES:
        raise HTTPException(status_code=400, detail=f"Unsupported locale: {locale}")

    stmt = select(LlmPromptTemplate).where(
        LlmPromptTemplate.tariff_code == tariff_code,
        LlmPromptTemplate.locale == locale,
    )
    result = await db.execute(stmt)
    rec = result.scalar_one_or_none()
    if rec:
        await db.delete(rec)
        await db.commit()
        await append_admin_log(
            db,
            actor.email or f"user:{actor.id}",
            "prompt_reset",
            f"{tariff_code}/{locale}",
        )
