"""
Служебные эндпоинты под префиксом API (`/api/v1/system/...`).
Дублируют по смыслу `/health` и `/health/ready` у корня приложения — удобно для прокси,
которые маршрутизируют только `/api/*`.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.health_checks import assert_dependencies_ready
from app.db.session import get_db
from app.schemas.common import ReadyResponse, StatusOk

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get(
    "/health",
    response_model=StatusOk,
    summary="Liveness (только API-префикс)",
    description="Процесс отвечает. Без проверки БД и Redis.",
)
async def api_health() -> StatusOk:
    return StatusOk()


@router.get(
    "/ready",
    response_model=ReadyResponse,
    summary="Readiness (БД, Redis; опционально Celery)",
    description="PostgreSQL и Redis доступны; при HEALTH_CHECK_CELERY — проверка воркеров Celery. 503 при сбое.",
)
async def api_ready(db: AsyncSession = Depends(get_db)) -> ReadyResponse:
    try:
        body = await assert_dependencies_ready(db)
        return ReadyResponse(**body)
    except Exception as exc:
        logger.warning("api_readiness_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unavailable",
        ) from exc
