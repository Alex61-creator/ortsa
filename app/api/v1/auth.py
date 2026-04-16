from typing import Optional
from urllib.parse import urlparse, urlunparse
from datetime import datetime

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
from app.services.analytics import derive_source_channel, record_analytics_event
from app.utils.email_policy import is_placeholder_account_email
from app.schemas.auth import TokenResponse, TwaAuthRequest

router = APIRouter()


def _oauth_redirect_uri(request: Request, route_name: str) -> str:
    """Callback URL для провайдера: схема и host из PUBLIC_APP_URL (или SITE через fallback в settings), путь из маршрута."""
    callback = urlparse(str(request.url_for(route_name)))
    base = urlparse(settings.public_app_base_url)
    return urlunparse((base.scheme, base.netloc, callback.path, "", "", ""))


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
    return await authenticate_twa(
        body.initData,
        db,
        utm_source=request.query_params.get("utm_source"),
        utm_medium=request.query_params.get("utm_medium"),
        utm_campaign=request.query_params.get("utm_campaign"),
        source_channel=request.headers.get("X-Client-Channel"),
        geo=request.headers.get("X-Client-Geo"),
    )


def _user_payload(external_id: str, email: Optional[str], provider: OAuthProvider) -> dict:
    safe_email = email or f"{external_id}@oauth.{provider.value}.local"
    return {"id": external_id, "email": safe_email}


async def oauth_callback(
    request_or_user_info: Request | dict,
    user_info_or_provider: dict | OAuthProvider,
    provider_or_db: OAuthProvider | AsyncSession,
    db: AsyncSession | None = None,
    *,
    redirect_base: str | None = None,
):
    # Backward compatible parameter mapping:
    # - production/routers call: (request, user_info, provider, db)
    # - tests call: (user_info, provider, db)
    if db is None:
        request: Request | None = None
        user_info: dict = request_or_user_info  # type: ignore[assignment]
        provider: OAuthProvider = user_info_or_provider  # type: ignore[assignment]
        db = provider_or_db  # type: ignore[assignment]
    else:
        request = request_or_user_info  # type: ignore[assignment]
        user_info = user_info_or_provider  # type: ignore[assignment]
        provider = provider_or_db  # type: ignore[assignment]

    email = user_info["email"]
    external_id = user_info["id"]
    stmt = select(User).where(User.external_id == external_id, User.oauth_provider == provider)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        if request is not None:
            source = request.query_params.get("utm_source")
            medium = request.query_params.get("utm_medium")
            campaign = request.query_params.get("utm_campaign")
            channel = request.headers.get("X-Client-Channel")
            geo = request.headers.get("X-Client-Geo")
        else:
            source = None
            medium = None
            campaign = None
            channel = None
            geo = None
        user = User(
            email=email,
            external_id=external_id,
            oauth_provider=provider,
            privacy_policy_version="1.0",
            utm_source=source,
            utm_medium=medium,
            utm_campaign=campaign,
            source_channel=derive_source_channel(source, channel),
            signup_platform="web",
            signup_geo=geo,
            acquisition_at=datetime.utcnow(),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        signup_event = await record_analytics_event(
            db,
            event_name="signup_completed",
            user_id=user.id,
            source_channel=user.source_channel,
            utm_source=user.utm_source,
            utm_medium=user.utm_medium,
            utm_campaign=user.utm_campaign,
            platform=user.signup_platform,
            geo=user.signup_geo,
            dedupe_key=f"signup:user:{user.id}",
        )

        # Cohort anchor for event-driven retention/heatmaps.
        await record_analytics_event(
            db,
            event_name="cohort_month_started",
            user_id=user.id,
            source_channel=user.source_channel,
            utm_source=user.utm_source,
            utm_medium=user.utm_medium,
            utm_campaign=user.utm_campaign,
            platform=user.signup_platform,
            geo=user.signup_geo,
            correlation_id=None,
            dedupe_key=f"cohort_month_started:{user.id}",
            event_time=signup_event.event_time,
        )
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
    redirect_uri = _oauth_redirect_uri(request, "google_callback")
    state = await create_state(OAuthProvider.GOOGLE)
    url = await google_oauth_client.get_authorization_url(redirect_uri, state=state)
    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)


@router.get(
    "/google/callback",
    name="google_callback",
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
    redirect_uri = _oauth_redirect_uri(request, "google_callback")
    token = await google_oauth_client.get_access_token(code, redirect_uri)
    ext_id, mail = await google_oauth_client.get_id_email(token["access_token"])
    user_info = _user_payload(ext_id, mail, OAuthProvider.GOOGLE)
    return await oauth_callback(request, user_info, OAuthProvider.GOOGLE, db)


@router.get(
    "/google/authorize-admin",
    summary="OAuth Google для админ-SPA: редирект на провайдера",
    description="Редирект после входа на ADMIN_APP_ORIGIN (или PUBLIC_APP_URL).",
)
@limiter.limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def google_authorize_admin(request: Request):
    redirect_uri = _oauth_redirect_uri(request, "google_callback_admin")
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
    redirect_uri = _oauth_redirect_uri(request, "google_callback_admin")
    token = await google_oauth_client.get_access_token(code, redirect_uri)
    ext_id, mail = await google_oauth_client.get_id_email(token["access_token"])
    user_info = _user_payload(ext_id, mail, OAuthProvider.GOOGLE)
    return await oauth_callback(
        request,
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
    redirect_uri = _oauth_redirect_uri(request, "yandex_callback")
    state = await create_state(OAuthProvider.YANDEX)
    url = await yandex_oauth_client.get_authorization_url(redirect_uri, state=state)
    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)


@router.get(
    "/yandex/callback",
    name="yandex_callback",
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
    redirect_uri = _oauth_redirect_uri(request, "yandex_callback")
    token = await yandex_oauth_client.get_access_token(code, redirect_uri)
    ext_id, mail = await yandex_oauth_client.get_id_email(token["access_token"])
    user_info = _user_payload(ext_id, mail, OAuthProvider.YANDEX)
    return await oauth_callback(request, user_info, OAuthProvider.YANDEX, db)


@router.get(
    "/apple/authorize",
    summary="OAuth Apple: редирект на провайдера",
)
@limiter.limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def apple_authorize(request: Request):
    redirect_uri = _oauth_redirect_uri(request, "apple_callback")
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
    redirect_uri = _oauth_redirect_uri(request, "apple_callback")
    token = await apple_oauth_client.get_access_token(code, redirect_uri)
    ext_id, mail = await apple_oauth_client.get_id_email(token.get("id_token"))
    user_info = _user_payload(ext_id, mail, OAuthProvider.APPLE)
    return await oauth_callback(request, user_info, OAuthProvider.APPLE, db)


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
