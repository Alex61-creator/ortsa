from httpx_oauth.clients.google import GoogleOAuth2

from app.core.config import settings
from app.services.oauth_clients import AppleOAuth2, YandexOAuth2

# Скоупы по умолчанию в httpx-oauth совместимы с get_profile() (People API / email).
google_oauth_client = GoogleOAuth2(
    client_id=settings.OAUTH_GOOGLE_CLIENT_ID or "",
    client_secret=settings.OAUTH_GOOGLE_CLIENT_SECRET or "",
)

yandex_oauth_client = YandexOAuth2(
    client_id=settings.OAUTH_YANDEX_CLIENT_ID or "",
    client_secret=settings.OAUTH_YANDEX_CLIENT_SECRET or "",
)

apple_oauth_client = AppleOAuth2(
    client_id=settings.OAUTH_APPLE_CLIENT_ID or "",
    client_secret=settings.OAUTH_APPLE_CLIENT_SECRET or "",
    team_id=settings.OAUTH_APPLE_TEAM_ID,
    key_id=settings.OAUTH_APPLE_KEY_ID,
    private_key_path=settings.OAUTH_APPLE_PRIVATE_KEY_PATH,
)
