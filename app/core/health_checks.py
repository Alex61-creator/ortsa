"""Общие проверки для readiness (PostgreSQL + Redis + опционально Celery)."""

import asyncio
from typing import Any

import redis as redis_sync
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
from app.core.config import settings


def _celery_ping_sync() -> bool:
    """Отвечает ли хотя бы один воркер на inspect.ping (через брокер)."""
    from app.tasks.worker import celery_app

    insp = celery_app.control.inspect(timeout=2.0)
    if insp is None:
        return False
    ping = insp.ping()
    return bool(ping)


def _celery_default_queue_length_sync() -> int:
    """Длина списка очереди по умолчанию в Redis-брокере Celery (ключ `celery`)."""
    client = redis_sync.from_url(settings.CELERY_BROKER_URL, decode_responses=False)
    try:
        return int(client.llen("celery"))
    finally:
        client.close()


async def assert_dependencies_ready(db: AsyncSession) -> dict[str, Any]:
    """
    Проверяет БД и Redis. При HEALTH_CHECK_CELERY — ping воркеров и (опционально) порог очереди.

    Возвращает тело ответа для /health/ready. Бросает исключение при сбое — вызывающий код отдаёт 503.
    """
    await db.execute(text("SELECT 1"))
    await cache.redis.ping()

    out: dict[str, Any] = {"status": "ok"}

    if not settings.HEALTH_CHECK_CELERY:
        return out

    ping_ok, qlen = await asyncio.gather(
        asyncio.to_thread(_celery_ping_sync),
        asyncio.to_thread(_celery_default_queue_length_sync),
    )
    out["celery_workers_ok"] = ping_ok
    out["celery_queue_length"] = qlen

    if not ping_ok:
        raise RuntimeError("Celery workers did not respond to ping")

    if settings.CELERY_QUEUE_FAIL_READINESS and qlen > settings.CELERY_QUEUE_ALERT_LENGTH:
        raise RuntimeError(
            f"Celery queue length {qlen} exceeds threshold {settings.CELERY_QUEUE_ALERT_LENGTH}"
        )

    return out
