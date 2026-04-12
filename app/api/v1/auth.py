from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User, OAuthProvider
from app.services.oauth import apple_oauth_client, google_oauth_client, yandex_oauth_client
from app.services.auth_twa import authenticate_twa
from app.services.oauth_state import consume_state, create_state
from app.utils.email_policy import is_placeholder_account_email

router = APIRouter()


@router.post("/twa")
@limiter.limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def twa_auth(request: Request, init_data: dict, db: AsyncSession = Depends(get_db)):
    return await authenticate_twa(init_data["initData"], db)


def _user_payload(external_id: str, email: Optional[str], provider: OAuthProvider) -> dict:
    safe_email = email or f"{external_id}@oauth.{provider.value}.local"
    return {"id": external_id, "email": safe_email}


async def oauth_callback(user_info: dict, provider: OAuthProvider, db: AsyncSession):
    email = user_info["email"]
    external_id = user_info["id"]
    stmt = select(User).where(User.external_id == external_id, User.oauth_provider == provider)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            email=email,
            external_id=external_id,
            oauth_provider=provider,
            privacy_policy_version="1.0",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        if (
            email
            and not is_placeholder_account_email(email)
            and email != user.email
        ):
            user.email = email
            await db.commit()
            await db.refresh(user)
    token = create_access_token({"sub": str(user.id), "tv": user.token_version})
    frontend_url = settings.public_app_base_url
    return RedirectResponse(f"{frontend_url}/auth/callback?token={token}")


@router.get("/google/authorize")
@limiter.limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def google_authorize(request: Request):
    redirect_uri = str(request.url_for("google_callback"))
    state = await create_state(OAuthProvider.GOOGLE)
    return await google_oauth_client.get_authorization_url(redirect_uri, state=state)


@router.get("/google/callback")
@limiter.limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def google_callback(
    request: Request,
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    if not await consume_state(state, OAuthProvider.GOOGLE):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state",
        )
    redirect_uri = str(request.url_for("google_callback"))
    token = await google_oauth_client.get_access_token(code, redirect_uri)
    ext_id, mail = await google_oauth_client.get_id_email(token["access_token"])
    user_info = _user_payload(ext_id, mail, OAuthProvider.GOOGLE)
    return await oauth_callback(user_info, OAuthProvider.GOOGLE, db)


@router.get("/yandex/authorize")
@limiter.limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def yandex_authorize(request: Request):
    redirect_uri = str(request.url_for("yandex_callback"))
    state = await create_state(OAuthProvider.YANDEX)
    return await yandex_oauth_client.get_authorization_url(redirect_uri, state=state)


@router.get("/yandex/callback")
@limiter.limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def yandex_callback(
    request: Request,
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    if not await consume_state(state, OAuthProvider.YANDEX):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state",
        )
    redirect_uri = str(request.url_for("yandex_callback"))
    token = await yandex_oauth_client.get_access_token(code, redirect_uri)
    ext_id, mail = await yandex_oauth_client.get_id_email(token["access_token"])
    user_info = _user_payload(ext_id, mail, OAuthProvider.YANDEX)
    return await oauth_callback(user_info, OAuthProvider.YANDEX, db)


@router.get("/apple/authorize")
@limiter.limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def apple_authorize(request: Request):
    redirect_uri = str(request.url_for("apple_callback"))
    state = await create_state(OAuthProvider.APPLE)
    return await apple_oauth_client.get_authorization_url(redirect_uri, state=state)


async def _apple_oauth_callback(
    request: Request,
    code: str,
    state: str,
    db: AsyncSession,
):
    if not await consume_state(state, OAuthProvider.APPLE):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state",
        )
    redirect_uri = str(request.url_for("apple_callback"))
    token = await apple_oauth_client.get_access_token(code, redirect_uri)
    ext_id, mail = await apple_oauth_client.get_id_email(token.get("id_token"))
    user_info = _user_payload(ext_id, mail, OAuthProvider.APPLE)
    return await oauth_callback(user_info, OAuthProvider.APPLE, db)


@router.get("/apple/callback", name="apple_callback")
@limiter.limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def apple_callback(
    request: Request,
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    return await _apple_oauth_callback(request, code, state, db)


@router.post("/apple/callback")
@limiter.limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def apple_callback_form_post(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Apple может прислать redirect URI с form_post (application/x-www-form-urlencoded)."""
    form = await request.form()
    code = form.get("code")
    state = form.get("state")
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing code or state",
        )
    return await _apple_oauth_callback(request, str(code), str(state), db)
