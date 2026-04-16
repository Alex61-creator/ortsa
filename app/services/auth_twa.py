import hmac
import hashlib
import json
from urllib.parse import parse_qs, unquote
from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import HTTPException, status
import structlog

from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import User, OAuthProvider
from app.services.admin_allowlist import sync_admin_allowlist_from_env
from app.services.analytics import derive_source_channel, record_analytics_event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = structlog.get_logger(__name__)

class TWAAuthService:
    def __init__(self, bot_token: str):
        self.bot_token = bot_token

    def validate_init_data(self, init_data: str) -> Dict[str, Any]:
        parsed = parse_qs(init_data)
        received_hash = parsed.pop("hash", [None])[0]
        if not received_hash:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing hash")

        auth_date_str = parsed.get("auth_date", [None])[0]
        if not auth_date_str:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing auth_date")
        auth_date = int(auth_date_str)
        now = int(datetime.now(timezone.utc).timestamp())
        max_age = settings.TWA_AUTH_MAX_AGE_SECONDS
        if abs(now - auth_date) > max_age:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Request too old")

        # https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app
        # secret_key = HMAC_SHA256(key="WebAppData", data=bot_token)
        sorted_keys = sorted(parsed.keys())
        data_check_string = "\n".join(
            f"{k}={unquote(parsed[k][0])}" for k in sorted_keys
        )

        secret_key = hmac.new(b"WebAppData", self.bot_token.encode(), hashlib.sha256).digest()
        computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        if computed_hash != received_hash:
            logger.warning("Invalid TWA initData hash")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid hash")

        user_data = json.loads(parsed["user"][0])
        return user_data

    async def get_or_create_user(
        self,
        db: AsyncSession,
        telegram_user_data: Dict[str, Any],
        *,
        utm_source: str | None = None,
        utm_medium: str | None = None,
        utm_campaign: str | None = None,
        source_channel: str | None = None,
        platform: str | None = "telegram",
        geo: str | None = None,
    ) -> User:
        telegram_id = str(telegram_user_data["id"])
        stmt = select(User).where(
            User.external_id == telegram_id,
            User.oauth_provider == OAuthProvider.TELEGRAM
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            email = f"tg_{telegram_id}@telegram.local"
            user = User(
                email=email,
                external_id=telegram_id,
                oauth_provider=OAuthProvider.TELEGRAM,
                privacy_policy_version="1.0",
                utm_source=utm_source,
                utm_medium=utm_medium,
                utm_campaign=utm_campaign,
                source_channel=source_channel or derive_source_channel(utm_source, "telegram"),
                signup_platform=platform,
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
            logger.info("New Telegram user created", user_id=user.id, telegram_id=telegram_id)

        return user

    def create_jwt_for_user(self, user: User) -> str:
        return create_access_token(
            {"sub": str(user.id), "email": user.email, "tv": user.token_version}
        )

async def authenticate_twa(
    init_data: str,
    db: AsyncSession,
    *,
    utm_source: str | None = None,
    utm_medium: str | None = None,
    utm_campaign: str | None = None,
    source_channel: str | None = None,
    geo: str | None = None,
) -> Dict[str, str]:
    service = TWAAuthService(settings.TELEGRAM_BOT_TOKEN)
    user_data = service.validate_init_data(init_data)
    user = await service.get_or_create_user(
        db,
        user_data,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
        source_channel=source_channel,
        geo=geo,
    )
    await sync_admin_allowlist_from_env(db, user)
    token = service.create_jwt_for_user(user)
    return {"access_token": token, "token_type": "bearer"}