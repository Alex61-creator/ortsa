from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User

# В Swagger «Authorize» — укажите схему Bearer и вставьте JWT (TWA / Google / Yandex / Apple).
http_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
) -> Optional[User]:
    if not credentials:
        return None
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        token_tv = int(payload.get("tv", 0))
    except JWTError:
        return None
    except (TypeError, ValueError):
        return None

    stmt = select(User).where(User.id == int(user_id))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        return None
    if user.token_version != token_tv:
        return None
    return user


async def get_current_active_user(
    current_user: Optional[User] = Depends(get_current_user),
) -> User:
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user


def _permission_value(user: User, permission_attr: str) -> bool | None:
    # Column can be NULL for legacy admins; treat it as "not configured".
    return getattr(user, permission_attr, None)


async def require_admin_permission(
    permission_attr: str,
    current_user: User,
    db: AsyncSession,
) -> User:
    # Read current permission value directly from DB to avoid any stale/unsafely loaded attributes.
    allowed = await db.scalar(select(getattr(User, permission_attr)).where(User.id == current_user.id))
    # Backward compatible behavior:
    # - None => legacy admin => allow
    # - True => allow
    # - False => deny
    deny_values = {False, 0, "0", "false", "False", "FALSE"}
    # SQLite sometimes returns Boolean columns as 0/1 (or as truthy strings on some backends).
    if allowed is not None and (allowed in deny_values or allowed is False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return current_user


async def get_current_admin_user_can_refund(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await require_admin_permission("can_refund", current_user=current_user, db=db)


async def get_current_admin_user_can_retry_report(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await require_admin_permission("can_retry_report", current_user=current_user, db=db)


async def get_current_admin_user_can_resend_report_email(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await require_admin_permission("can_resend_report_email", current_user=current_user, db=db)


async def get_current_admin_user_can_manual_override(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await require_admin_permission("can_manual_override", current_user=current_user, db=db)
