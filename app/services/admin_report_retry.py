"""Лимит перезапуска генерации отчёта из админки: 5 попыток на заказ за календарные сутки UTC."""

from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.core.cache import cache

_MAX_PER_DAY = 5


async def consume_admin_report_retry_slot(order_id: int) -> None:
    """
    Увеличивает счётчик на сегодня (UTC). Если после инкремента > лимита — откат счётчика и 429.
    """
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    key = f"admin:report_retry:{order_id}:{day}"
    n = await cache.incr(key)
    if n == 1:
        await cache.expire(key, 172800)
    if n > _MAX_PER_DAY:
        await cache.decr(key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Лимит {_MAX_PER_DAY} перезапусков отчёта по этому заказу за сутки (UTC) исчерпан",
        )
