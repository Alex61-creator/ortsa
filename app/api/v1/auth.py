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
from app.services.admin_allowlist import sync_admin_allowlist_from_env
from app.services.oauth_state import consume_state, create_state
from app.utils.email_policy import is_placeholder_account_email
from app.schemas.auth import TokenResponse, TwaAuthRequest

router = APIRouter()


@router.post(
    "/twa",
    response_model=TokenResponse,
    summary="Вход через Telegram Mini App",
    description=(
        "Принимает `initData` из `Telegram.WebApp`, проверяет HMAC, создаёт или находит "
        "пользователя и возвращает JWT (`Bearer`)."
    ),
)
@limiter.limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def twa_auth(
    request: Request,
    body: TwaAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    return await authenticate_twa(body.initData, db)


def _user_payload(external_id: str, email: Optional[str], provider: OAuthProvider) -> dict:
    safe_email = email or f"{external_id}@oauth.{provider.value}.local"
    return {"id": external_id, "email": safe_email}


async def oauth_callback(
    user_info: dict,
    provider: OAuthProvider,
    db: AsyncSession,
    *,
    redirect_base: str | None = None,
):
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
    await sync_admin_allowlist_from_env(db, user)
    token = create_access_token({"sub": str(user.id), "tv": user.token_version})
    base = (redirect_base or settings.public_app_base_url).rstrip("/")
    return RedirectResponse(f"{base}/auth/callback?token={token}")


@router.get(
    "/google/authorize",
    summary="OAuth Google: редирект на провайдера",
    description="Начало OAuth2: редирект на страницу согласия Google.",
)
@limiter.limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def google_authorize(request: Request):
    redirect_uri = str(request.url_for("google_callback"))
    state = await create_state(OAuthProvider.GOOGLE)
    url = await google_oauth_client.get_authorization_url(redirect_uri, state=state)
    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)


@router.get(
    "/google/callback",
    summary="OAuth Google: callback",
    description="Обмен code на токен, создание пользователя, редирект на фронт с JWT в query.",
)
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


@router.get(
    "/google/authorize-admin",
    summary="OAuth Google для админ-SPA: редирект на провайдера",
    description="Редирект после входа на ADMIN_APP_ORIGIN (или PUBLIC_APP_URL).",
)
@limiter.limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def google_authorize_admin(request: Request):
    redirect_uri = str(request.url_for("google_callback_admin"))
    state = await create_state(OAuthProvider.GOOGLE, flow="admin")
    url = await google_oauth_client.get_authorization_url(redirect_uri, state=state)
    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)


@router.get(
    "/google/callback-admin",
    name="google_callback_admin",
    summary="OAuth Google: callback для админки",
    description="Как /google/callback, но редирект с JWT на origin админ-SPA.",
)
@limiter.limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def google_callback_admin(
    request: Request,
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    if not await consume_state(state, OAuthProvider.GOOGLE, flow="admin"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state",
        )
    redirect_uri = str(request.url_for("google_callback_admin"))
    token = await google_oauth_client.get_access_token(code, redirect_uri)
    ext_id, mail = await google_oauth_client.get_id_email(token["access_token"])
    user_info = _user_payload(ext_id, mail, OAuthProvider.GOOGLE)
    return await oauth_callback(
        user_info,
        OAuthProvider.GOOGLE,
        db,
        redirect_base=settings.admin_app_base_url,
    )


@router.get(
    "/yandex/authorize",
    summary="OAuth Yandex: редирект на провайдера",
)
@limiter.limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def yandex_authorize(request: Request):
    redirect_uri = str(request.url_for("yandex_callback"))
    state = await create_state(OAuthProvider.YANDEX)
    url = await yandex_oauth_client.get_authorization_url(redirect_uri, state=state)
    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)


@router.get(
    "/yandex/callback",
    summary="OAuth Yandex: callback",
    description="Обмен code на токен, создание пользователя, редирект на фронт с JWT в query.",
)
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


@router.get(
    "/apple/authorize",
    summary="OAuth Apple: редирект на провайдера",
)
@limiter.limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def apple_authorize(request: Request):
    redirect_uri = str(request.url_for("apple_callback"))
    state = await create_state(OAuthProvider.APPLE)
    url = await apple_oauth_client.get_authorization_url(redirect_uri, state=state)
    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)


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


@router.get(
    "/apple/callback",
    name="apple_callback",
    summary="OAuth Apple: callback (GET)",
    description="Редирект с code/state (response_mode query).",
)
@limiter.limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def apple_callback(
    request: Request,
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    return await _apple_oauth_callback(request, code, state, db)


@router.post(
    "/apple/callback",
    summary="OAuth Apple: callback (POST form_post)",
    description="Тот же callback, что GET; Apple может прислать ответ как form_post.",
)
@limiter.limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def apple_callback_form_post(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    code = form.get("code")
    state = form.get("state")
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing code or state",
        )
    return await _apple_oauth_callback(request, str(code), str(state), db)
