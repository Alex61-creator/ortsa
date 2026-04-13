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

    async def get_or_create_user(self, db: AsyncSession, telegram_user_data: Dict[str, Any]) -> User:
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
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            logger.info("New Telegram user created", user_id=user.id, telegram_id=telegram_id)

        return user

    def create_jwt_for_user(self, user: User) -> str:
        return create_access_token(
            {"sub": str(user.id), "email": user.email, "tv": user.token_version}
        )

async def authenticate_twa(init_data: str, db: AsyncSession) -> Dict[str, str]:
    service = TWAAuthService(settings.TELEGRAM_BOT_TOKEN)
    user_data = service.validate_init_data(init_data)
    user = await service.get_or_create_user(db, user_data)
    await sync_admin_allowlist_from_env(db, user)
    token = service.create_jwt_for_user(user)
    return {"access_token": token, "token_type": "bearer"}