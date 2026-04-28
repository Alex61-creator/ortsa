"""Behavior tests for admin allowlist synchronization."""

import pytest
from sqlalchemy import select

from app.api.v1.auth import oauth_callback
from app.models.user import OAuthProvider, User
from app.services.admin_allowlist import sync_admin_allowlist_from_env


async def _create_user(
    db_session,
    *,
    provider: OAuthProvider,
    external_id: str,
    email: str | None,
    is_admin: bool = False,
) -> User:
    user = User(
        email=email,
        external_id=external_id,
        oauth_provider=provider,
        privacy_policy_version="1.0",
        is_admin=is_admin,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_google_allowlisted_email_grants_admin_rights(db_session, monkeypatch):
    """Happy path: allowlisted Google email grants admin access."""
    monkeypatch.setattr(
        "app.core.config.settings.ADMIN_GOOGLE_EMAILS",
        "admin@example.com",
    )
    user = await _create_user(
        db_session,
        provider=OAuthProvider.GOOGLE,
        external_id="g-1",
        email="admin@example.com",
    )

    await sync_admin_allowlist_from_env(db_session, user)
    await db_session.refresh(user)

    assert user.is_admin is True


@pytest.mark.asyncio
async def test_telegram_allowlisted_external_id_grants_admin_rights(db_session, monkeypatch):
    """Happy path: allowlisted Telegram external id grants admin access."""
    monkeypatch.setattr(
        "app.core.config.settings.ADMIN_TELEGRAM_USER_IDS",
        "123456",
    )
    user = await _create_user(
        db_session,
        provider=OAuthProvider.TELEGRAM,
        external_id="123456",
        email="tg@example.com",
    )

    await sync_admin_allowlist_from_env(db_session, user)
    await db_session.refresh(user)

    assert user.is_admin is True


@pytest.mark.asyncio
async def test_non_allowlisted_user_does_not_get_admin(db_session, monkeypatch):
    """Negative: users outside allowlist never get admin flag."""
    monkeypatch.setattr(
        "app.core.config.settings.ADMIN_GOOGLE_EMAILS",
        "admin@example.com",
    )
    user = await _create_user(
        db_session,
        provider=OAuthProvider.GOOGLE,
        external_id="g-2",
        email="user@example.com",
    )

    await sync_admin_allowlist_from_env(db_session, user)
    await db_session.refresh(user)

    assert user.is_admin is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "email_variant",
    [
        "admin@example.com",
        "ADMIN@EXAMPLE.COM",
        "  admin@example.com",
        "admin@example.com  ",
        "  ADMIN@EXAMPLE.COM  ",
    ],
)
async def test_allowlisted_google_email_normalization_invariant(
    db_session,
    monkeypatch,
    email_variant,
):
    """
    Property/invariant:
    formatting differences (case/leading/trailing spaces)
    must not affect allowlist decision for Google emails.
    """
    monkeypatch.setattr(
        "app.core.config.settings.ADMIN_GOOGLE_EMAILS",
        "admin@example.com",
    )
    user = await _create_user(
        db_session,
        provider=OAuthProvider.GOOGLE,
        external_id=f"g-{abs(hash(email_variant))}",
        email=email_variant,
    )

    await sync_admin_allowlist_from_env(db_session, user)
    await db_session.refresh(user)

    assert user.is_admin is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "provider",
    [OAuthProvider.APPLE, OAuthProvider.YANDEX, OAuthProvider.TELEGRAM],
)
async def test_admin_email_allowlist_applies_only_to_google_provider_invariant(
    db_session,
    monkeypatch,
    provider,
):
    """
    Property/invariant:
    Google email allowlist must not elevate users of other OAuth providers.
    """
    monkeypatch.setattr(
        "app.core.config.settings.ADMIN_GOOGLE_EMAILS",
        "admin@example.com",
    )
    user = await _create_user(
        db_session,
        provider=provider,
        external_id=f"{provider.value}-1",
        email="admin@example.com",
    )

    await sync_admin_allowlist_from_env(db_session, user)
    await db_session.refresh(user)

    assert user.is_admin is False


@pytest.mark.asyncio
async def test_oauth_callback_applies_allowlist_on_login_integration(db_session, monkeypatch):
    """Contract/integration: OAuth callback elevates admin when user matches allowlist."""
    monkeypatch.setattr(
        "app.core.config.settings.ADMIN_GOOGLE_EMAILS",
        "admin@example.com",
    )

    await oauth_callback(
        {"id": "google-sub-1", "email": "admin@example.com"},
        OAuthProvider.GOOGLE,
        db_session,
    )

    result = await db_session.execute(
        select(User).where(
            User.external_id == "google-sub-1",
            User.oauth_provider == OAuthProvider.GOOGLE,
        )
    )
    user = result.scalar_one()
    assert user.is_admin is True
