"""
LLM Router — выбор активного провайдера и умный failover.

Логика:
1. Читает порядок провайдеров из app_settings (llm_fallback_order) с Redis-кешем 60 сек.
2. Для каждого провайдера проверяет: включён ли (app_settings) и не открыт ли circuit breaker.
3. Возвращает первый доступный провайдер.
4. При сетевой ошибке — фиксирует сбой в CB и пробует следующий.
5. При ошибке валидации — переходит к следующему без записи в CB.
"""
from __future__ import annotations

from typing import Any, Callable, Coroutine

import structlog

from app.core.cache import cache
from app.services.llm_client import LLMProvider

logger = structlog.get_logger(__name__)

_KEY_FALLBACK_ORDER = "llm_fallback_order"
_KEY_ENABLED_TMPL = "llm_provider_{provider}_enabled"
_CB_KEY_TMPL = "llm:cb:failures:{provider}"
_ROUTER_SETTINGS_CACHE_KEY = "llm:router:settings"
_ROUTER_SETTINGS_TTL = 60

_DEFAULT_ORDER = [LLMProvider.CLAUDE, LLMProvider.GROK, LLMProvider.DEEPSEEK]


async def _load_settings() -> dict[str, str]:
    cached = await cache.get(_ROUTER_SETTINGS_CACHE_KEY)
    if cached:
        return cached

    from app.db.session import AsyncSessionLocal
    from sqlalchemy import select
    from app.models.app_settings import AppSettings

    needed = [_KEY_FALLBACK_ORDER] + [_KEY_ENABLED_TMPL.format(provider=p.value) for p in LLMProvider]
    result: dict[str, str] = {}
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(AppSettings).where(AppSettings.key.in_(needed)))).scalars().all()
        for row in rows:
            result[row.key] = row.value

    await cache.set(_ROUTER_SETTINGS_CACHE_KEY, result, ttl=_ROUTER_SETTINGS_TTL)
    return result


def _build_chain(settings: dict[str, str]) -> list[LLMProvider]:
    raw = settings.get(_KEY_FALLBACK_ORDER, "")
    if not raw:
        return list(_DEFAULT_ORDER)
    chain: list[LLMProvider] = []
    for name in (n.strip() for n in raw.split(",") if n.strip()):
        try:
            chain.append(LLMProvider(name))
        except ValueError:
            logger.warning("Unknown provider in fallback_order", name=name)
    return chain or list(_DEFAULT_ORDER)


async def _enabled(provider: LLMProvider, settings: dict[str, str]) -> bool:
    return settings.get(_KEY_ENABLED_TMPL.format(provider=provider.value), "false").lower() == "true"


async def _cb_open(provider: LLMProvider, threshold: int) -> bool:
    val = await cache.redis.get(_CB_KEY_TMPL.format(provider=provider.value))
    return int(val or 0) >= threshold


async def record_provider_failure(provider: LLMProvider, window: int = 300, threshold: int = 10) -> None:
    key = _CB_KEY_TMPL.format(provider=provider.value)
    await cache.redis.incr(key)
    await cache.redis.expire(key, window)
    logger.warning("LLM provider failure recorded", provider=provider.value)


async def record_provider_success(provider: LLMProvider) -> None:
    await cache.redis.delete(_CB_KEY_TMPL.format(provider=provider.value))


async def invalidate_router_cache() -> None:
    await cache.redis.delete(_ROUTER_SETTINGS_CACHE_KEY)


LLMCallable = Callable[[LLMProvider], Coroutine[Any, Any, Any]]


async def call_with_fallback(
    fn: LLMCallable,
    *,
    validation_error_cls: type[Exception] | None = None,
) -> tuple[Any, LLMProvider]:
    """
    Вызвать fn(provider) с автоматическим failover.
    Возвращает (result, provider_used).
    """
    from app.core.config import settings as app_settings

    router_settings = await _load_settings()
    chain = _build_chain(router_settings)
    threshold = app_settings.LLM_CIRCUIT_BREAKER_THRESHOLD
    window = app_settings.LLM_CIRCUIT_BREAKER_WINDOW_SECONDS

    last_exc: Exception | None = None

    for provider in chain:
        if not await _enabled(provider, router_settings):
            logger.debug("LLM provider disabled", provider=provider.value)
            continue
        if await _cb_open(provider, threshold):
            logger.warning("LLM CB open, skipping", provider=provider.value)
            continue

        try:
            result = await fn(provider)
            await record_provider_success(provider)
            return result, provider
        except Exception as exc:  # noqa: BLE001
            if validation_error_cls and isinstance(exc, validation_error_cls):
                logger.warning("LLM validation failed, trying next", provider=provider.value, error=str(exc))
                last_exc = exc
                continue
            await record_provider_failure(provider, window, threshold)
            logger.error("LLM provider error, trying next", provider=provider.value, error=str(exc))
            last_exc = exc
            continue

    raise RuntimeError(f"All LLM providers failed. Last: {last_exc}") from last_exc
