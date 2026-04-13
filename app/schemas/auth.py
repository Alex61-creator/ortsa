from pydantic import BaseModel, Field


class TwaAuthRequest(BaseModel):
    """Тело запроса входа через Telegram Mini App (WebApp.initData)."""

    initData: str = Field(
        ...,
        min_length=1,
        description="Строка `Telegram.WebApp.initData` для проверки подписи бота.",
    )


class TokenResponse(BaseModel):
    """JWT для заголовка Authorization: Bearer <access_token>."""

    access_token: str
    token_type: str = Field(default="bearer", description="Тип токена (OAuth2 password flow style).")
