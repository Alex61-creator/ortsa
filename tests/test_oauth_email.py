"""Тесты обновления email при OAuth callback."""

import pytest
from sqlalchemy import select

from app.api.v1.auth import oauth_callback
from app.models.user import OAuthProvider, User


@pytest.mark.asyncio
async def test_oauth_callback_updates_email_when_provider_returns_new(db_session):
    user = User(
        email="old@example.com",
        external_id="go_1",
        oauth_provider=OAuthProvider.GOOGLE,
        privacy_policy_version="1.0",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    await oauth_callback(
        {"id": "go_1", "email": "new@example.com"},
        OAuthProvider.GOOGLE,
        db_session,
    )
    await db_session.refresh(user)
    assert user.email == "new@example.com"


@pytest.mark.asyncio
async def test_oauth_callback_does_not_replace_real_email_with_oauth_placeholder(
    db_session,
):
    user = User(
        email="real@example.com",
        external_id="go_2",
        oauth_provider=OAuthProvider.GOOGLE,
        privacy_policy_version="1.0",
    )
    db_session.add(user)
    await db_session.commit()

    await oauth_callback(
        {"id": "go_2", "email": "go_2@oauth.google.local"},
        OAuthProvider.GOOGLE,
        db_session,
    )
    await db_session.refresh(user)
    assert user.email == "real@example.com"


@pytest.mark.asyncio
async def test_oauth_callback_creates_user_with_placeholder_email(db_session):
    await oauth_callback(
        {"id": "new_sub", "email": "new_sub@oauth.yandex.local"},
        OAuthProvider.YANDEX,
        db_session,
    )
    res = await db_session.execute(
        select(User).where(
            User.external_id == "new_sub",
            User.oauth_provider == OAuthProvider.YANDEX,
        )
    )
    u = res.scalar_one()
    assert u.email == "new_sub@oauth.yandex.local"
