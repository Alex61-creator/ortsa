import os
import sys
from datetime import datetime
from decimal import Decimal
from types import ModuleType

import fakeredis.aioredis
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Минимальные переменные до импорта приложения (локальный запуск тестов без .env)
_defaults = {
    "YOOKASSA_WEBHOOK_VERIFY_IP": "false",
    "YOOKASSA_WEBHOOK_VERIFY_API": "false",
    "SECRET_KEY": "test-secret-key",
    "POSTGRES_SERVER": "localhost",
    "POSTGRES_USER": "test",
    "POSTGRES_PASSWORD": "test",
    "POSTGRES_DB": "test",
    "TELEGRAM_BOT_TOKEN": "000000:TEST",
    "YOOKASSA_SHOP_ID": "test",
    "YOOKASSA_SECRET_KEY": "test",
    "YOOKASSA_RETURN_URL": "http://localhost/success",
    "PUBLIC_APP_URL": "http://test",
    "DEEPSEEK_API_KEY": "test",
    "SMTP_HOST": "localhost",
    "SMTP_USER": "test",
    "SMTP_PASSWORD": "test",
    "SMTP_FROM": "test@example.com",
    "ADMIN_USERNAME": "admin",
    "ADMIN_PASSWORD": "admin",
    "ADMIN_EMAIL": "admin@example.com",
    "OAUTH_GOOGLE_CLIENT_ID": "test-google-client",
    "OAUTH_GOOGLE_CLIENT_SECRET": "test-google-secret",
    "OAUTH_YANDEX_CLIENT_ID": "test-yandex-client",
    "OAUTH_YANDEX_CLIENT_SECRET": "test-yandex-secret",
}
for _k, _v in _defaults.items():
    os.environ.setdefault(_k, _v)

from app.core.cache import cache

# In-memory Redis: тесты не требуют живой Redis (TariffService, вебхуки, clear_cache).
cache.redis = fakeredis.aioredis.FakeRedis(decode_responses=True)


def _stub_weasyprint_if_system_libs_missing() -> None:
    """WeasyPrint тянет GTK/Pango; на macOS без них импорт падает — заглушка только для прогона тестов."""
    try:
        import weasyprint  # noqa: F401
    except OSError:
        mod = ModuleType("weasyprint")

        class _HTML:
            def __init__(self, *args, **kwargs):
                pass

            def write_pdf(self, *args, **kwargs):
                pass

        class _CSS:
            def __init__(self, *args, **kwargs):
                pass

        mod.HTML = _HTML
        mod.CSS = _CSS
        sys.modules["weasyprint"] = mod


_stub_weasyprint_if_system_libs_missing()

from app.main import app
from app.api.deps import get_db
from app.core.security import create_access_token
from app.db.base import Base
from app.models.natal_data import NatalData
from app.models.tariff import Tariff
from app.models.user import OAuthProvider, User
from app.models.monthly_digest import MonthlyDigestLog  # noqa: F401 — регистрация метаданных

# Общая in-memory БД для всех соединений пула (иначе :memory: даёт пустую схему на новом connect).
TEST_DATABASE_URL = "sqlite+aiosqlite:///file:memdb1?mode=memory&cache=shared&uri=true"
engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False, "uri": True},
    poolclass=StaticPool,
)
TestingSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(autouse=True)
async def clear_cache():
    await cache.redis.flushdb()
    yield


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_session():
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture
async def test_user(db_session):
    user = User(
        email="test@example.com",
        external_id="123",
        oauth_provider=OAuthProvider.TELEGRAM,
        consent_given_at=datetime.utcnow(),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    token = create_access_token({"sub": str(test_user.id), "tv": test_user.token_version})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def seed_report_tariff_and_natal(test_user, db_session):
    """Тариф `report` (natal_full) и натальные данные — для POST /orders/ и лимитов."""
    tariff = Tariff(
        code="report",
        name="Отчёт",
        price=Decimal("100.00"),
        price_usd=Decimal("1.05"),
        features={"max_natal_profiles": 1},
        retention_days=30,
        llm_tier="natal_full",
    )
    db_session.add(tariff)
    await db_session.flush()
    natal = NatalData(
        user_id=test_user.id,
        full_name="Test User",
        birth_date=datetime(1990, 1, 1, 0, 0, 0),
        birth_time=datetime(1990, 1, 1, 12, 0, 0),
        birth_place="Moscow",
        lat=55.7558,
        lon=37.6173,
        timezone="Europe/Moscow",
        house_system="P",
    )
    db_session.add(natal)
    await db_session.commit()
    await db_session.refresh(natal)
    return {"tariff_code": "report", "natal_data_id": natal.id}
