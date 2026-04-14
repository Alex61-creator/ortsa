from typing import List, Optional

from pydantic import AnyHttpUrl, EmailStr, Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

# Корень репозитория: .../app/core/config.py -> три уровня вверх (не путать с пакетом `app/`)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _normalize_admin_email(raw: str) -> str:
    return raw.strip().lower()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    PROJECT_NAME: str = "AstroGen"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = Field(
        default_factory=list,
        description="Разрешённые origins для CORS (браузерный лендинг / Mini App на другом порту). Пример: http://127.0.0.1:8000",
    )
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000

    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: Optional[PostgresDsn] = None

    @field_validator("DATABASE_URL", mode="before")
    def assemble_db_connection(cls, v: Optional[str], info) -> str:
        if isinstance(v, str):
            return v
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=info.data.get("POSTGRES_USER"),
            password=info.data.get("POSTGRES_PASSWORD"),
            host=info.data.get("POSTGRES_SERVER"),
            path=info.data.get("POSTGRES_DB"),
        )

    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    STORAGE_DIR: Path = Path("/app/storage")
    STORAGE_RETENTION_DAYS: int = 90

    # Nominatim: обязательный User-Agent с контактом (политика использования)
    NOMINATIM_USER_AGENT: str = "AstroGen/1.0 (contact: support@astrogen.ru)"

    OAUTH_GOOGLE_CLIENT_ID: Optional[str] = None
    OAUTH_GOOGLE_CLIENT_SECRET: Optional[str] = None
    OAUTH_YANDEX_CLIENT_ID: Optional[str] = None
    OAUTH_YANDEX_CLIENT_SECRET: Optional[str] = None
    OAUTH_APPLE_CLIENT_ID: Optional[str] = None
    OAUTH_APPLE_CLIENT_SECRET: Optional[str] = None
    OAUTH_APPLE_TEAM_ID: Optional[str] = None
    OAUTH_APPLE_KEY_ID: Optional[str] = None
    OAUTH_APPLE_PRIVATE_KEY_PATH: Optional[Path] = None

    TELEGRAM_BOT_TOKEN: str

    YOOKASSA_SHOP_ID: str
    YOOKASSA_SECRET_KEY: str
    YOOKASSA_RETURN_URL: str
    # Публичный URL SPA (письма «отчёт готов», ссылки в кабинет). Если не задан — fallback на YOOKASSA_RETURN_URL.
    PUBLIC_APP_URL: Optional[str] = None
    # Канонический origin для SEO (canonical, sitemap, OG). Если не задан — как public_app_base_url.
    SITE_URL: Optional[str] = None
    # Верификация в кабинетах поисковиков (содержимое content=, не секреты в коде — только из .env)
    GOOGLE_SITE_VERIFICATION: Optional[str] = None
    YANDEX_VERIFICATION: Optional[str] = None
    BING_SITE_VERIFICATION: Optional[str] = None
    # Уведомления: по документации ЮKassa — IP-лист + сверка объекта через API (не HMAC заголовка).
    YOOKASSA_WEBHOOK_VERIFY_IP: bool = True
    YOOKASSA_WEBHOOK_VERIFY_API: bool = True

    # Telegram Web App: допустимый возраст initData (сек.), см. core.telegram.org/bots/webapps
    TWA_AUTH_MAX_AGE_SECONDS: int = 86400

    SENTRY_DSN: Optional[str] = None

    DEEPSEEK_API_KEY: str
    LLM_MODEL: str = "deepseek-chat"
    # Таймаут HTTP к api.deepseek.com (сек.); меньше soft limit Celery-таска
    LLM_HTTP_TIMEOUT_SECONDS: float = 300.0
    LLM_MAX_TOKENS: int = 4096
    LLM_MAX_TOKENS_FREE: int = 2048
    LLM_MAX_TOKENS_FULL: int = 4096
    LLM_MAX_TOKENS_PRO: int = 6144
    LLM_TEMPERATURE: float = 0.2
    LLM_TOP_P: float = 0.9

    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: EmailStr = "noreply@astrogen.ru"
    SMTP_TLS: bool = True

    # Unisender Transactional Email (основной провайдер для доставки отчётов)
    UNISENDER_API_KEY: str = ""

    ADMIN_USERNAME: str
    ADMIN_PASSWORD: str
    ADMIN_EMAIL: EmailStr

    # SPA админки (отдельный поддомен): OAuth redirect и CORS
    ADMIN_APP_ORIGIN: Optional[AnyHttpUrl] = None
    # Через запятую: email Google и числовые id Telegram (как строки), совпадение → is_admin при входе
    ADMIN_GOOGLE_EMAILS: str = ""
    ADMIN_TELEGRAM_USER_IDS: str = ""

    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_AUTH_PER_MINUTE: int = 5
    RATE_LIMIT_ORDERS_PER_MINUTE: int = 10

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # Пул SQLAlchemy (подберите под Uvicorn workers + Celery; сумма < max_connections PostgreSQL)
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    # Readiness: проверка Celery (ping воркеров + длина очереди в Redis). В dev без воркера — false.
    HEALTH_CHECK_CELERY: bool = False
    # Порог длины очереди default `celery` в Redis; при превышении — 503 если CELERY_QUEUE_FAIL_READINESS
    CELERY_QUEUE_ALERT_LENGTH: int = 50
    CELERY_QUEUE_FAIL_READINESS: bool = False

    @property
    def public_app_base_url(self) -> str:
        base = self.PUBLIC_APP_URL or self.YOOKASSA_RETURN_URL
        return str(base).rstrip("/")

    @property
    def site_base_url(self) -> str:
        """Базовый URL сайта для canonical, sitemap, JSON-LD (без завершающего /)."""
        if self.SITE_URL:
            return str(self.SITE_URL).rstrip("/")
        return self.public_app_base_url

    @property
    def admin_app_base_url(self) -> str:
        """Origin админ-SPA для OAuth redirect (без завершающего /)."""
        if self.ADMIN_APP_ORIGIN:
            return str(self.ADMIN_APP_ORIGIN).rstrip("/")
        return self.public_app_base_url

    @property
    def admin_google_emails_set(self) -> set[str]:
        return {_normalize_admin_email(e) for e in self.ADMIN_GOOGLE_EMAILS.split(",") if e.strip()}

    @property
    def admin_telegram_ids_set(self) -> set[str]:
        return {e.strip() for e in self.ADMIN_TELEGRAM_USER_IDS.split(",") if e.strip()}


settings = Settings()