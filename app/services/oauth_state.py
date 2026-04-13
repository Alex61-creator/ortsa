"""OAuth2 state (CSRF): одноразовый токен в Redis на цепочку authorize → callback."""

from __future__ import annotations

import secrets

from app.core.cache import cache
from app.models.user import OAuthProvider

_OAUTH_STATE_TTL = 600
_PREFIX = "oauth_state:"


async def create_state(provider: OAuthProvider, *, flow: str = "main") -> str:
    state = secrets.token_urlsafe(32)
    payload = f"{provider.value}:{flow}"
    await cache.set(f"{_PREFIX}{state}", payload, ttl=_OAUTH_STATE_TTL)
    return state


async def consume_state(state: str | None, expected: OAuthProvider, *, flow: str = "main") -> bool:
    if not state:
        return False
    key = f"{_PREFIX}{state}"
    stored = await cache.get(key)
    expected_payload = f"{expected.value}:{flow}"
    if stored != expected_payload:
        return False
    await cache.delete(key)
    return True
