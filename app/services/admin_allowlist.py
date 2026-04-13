"""Синхронизация флага is_admin с allowlist из env (Google email, Telegram id)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import OAuthProvider, User


def _normalize_email(email: str) -> str:
    return email.strip().lower()


async def sync_admin_allowlist_from_env(db: AsyncSession, user: User) -> None:
    """Если пользователь в allowlist — выставить is_admin=True и закоммитить."""
    if user.is_admin:
        return
    if not _user_in_admin_allowlist(user):
        return
    user.is_admin = True
    await db.commit()
    await db.refresh(user)


def _user_in_admin_allowlist(user: User) -> bool:
    if user.oauth_provider == OAuthProvider.GOOGLE and user.email:
        if _normalize_email(user.email) in settings.admin_google_emails_set:
            return True
    if user.oauth_provider == OAuthProvider.TELEGRAM:
        if user.external_id in settings.admin_telegram_ids_set:
            return True
    return False
