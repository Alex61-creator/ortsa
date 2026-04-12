import pytest

from app.models.user import OAuthProvider
from app.services.oauth_state import consume_state, create_state


@pytest.mark.asyncio
async def test_oauth_state_roundtrip():
    st = await create_state(OAuthProvider.GOOGLE)
    assert len(st) > 20
    assert await consume_state(st, OAuthProvider.GOOGLE) is True
    assert await consume_state(st, OAuthProvider.GOOGLE) is False


@pytest.mark.asyncio
async def test_oauth_state_wrong_provider():
    st = await create_state(OAuthProvider.GOOGLE)
    assert await consume_state(st, OAuthProvider.YANDEX) is False
