import structlog
from datetime import date

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, RedirectResponse, Response
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.logging import setup_logging
from app.core.exceptions import setup_exception_handlers
from app.api.v1 import api_router
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import engine, AsyncSessionLocal
from app.admin import setup_admin
from app.core.cache import cache
from app.core.health_checks import assert_dependencies_ready
from app.api.deps import get_db
from app.schemas.common import ReadyResponse
from app.middleware.security_headers import SecurityHeadersMiddleware

setup_logging()
logger = structlog.get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.SENTRY_DSN:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            traces_sample_rate=0.1,
        )
    logger.info("Starting up", environment=settings.ENVIRONMENT)
    from app.services.tariff import TariffService
    async with AsyncSessionLocal() as db:
        await TariffService.get_all(db)
    yield
    logger.info("Shutting down")
    await engine.dispose()

_OPENAPI_TAGS = [
    {
        "name": "Авторизация",
        "description": "Вход через OAuth (Google, Yandex, Apple) и Telegram Web App, обмен кода на JWT, служебные ссылки для OAuth.",
    },
    {
        "name": "Натальные данные",
        "description": "Сохранение и просмотр введённых пользователем данных рождения и места — основа для расчёта карты.",
    },
    {
        "name": "Заказы",
        "description": "Создание заказа на расчёт, оплата через ЮKassa, список заказов и статусы, привязка к тарифу и натальным данным.",
    },
    {
        "name": "Тарифы",
        "description": "Публичный каталог тарифов (цены и описание из админки / БД).",
    },
    {
        "name": "Отчёты",
        "description": "Готовые PDF и связанные материалы по завершённым заказам.",
    },
    {
        "name": "Профиль и экспорт",
        "description": "Текущий пользователь (/me) и выгрузка персональных данных.",
    },
    {
        "name": "Вебхуки",
        "description": "Входящие уведомления от внешних сервисов (например, ЮKassa) для обновления статусов оплаты.",
    },
    {
        "name": "Служебное",
        "description": "Liveness/readiness: корень `/health`, `/health/ready` и дубли под префиксом API `/api/v1/system/health`, `/api/v1/system/ready` для прокси, маршрутизирующих только `/api/*`.",
    },
    {
        "name": "Геокодинг",
        "description": "Поиск координат и часового пояса по строке места (Nominatim).",
    },
    {
        "name": "Подписки",
        "description": "Astro Pro: статус подписки и отмена с конца периода.",
    },
    {
        "name": "Админка",
        "description": "Панель оператора: тарифы, заказы, отчёты, пользователи. Только JWT с is_admin.",
    },
    {
        "name": "Лендинг",
        "description": "Статические HTML/CSS/JS лендинга и пример отчёта.",
    },
]

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="""
## AstroGen — сервис генерации персональных натальных карт

REST API для клиентского приложения: авторизация, натальные данные, заказы, оплата и отчёты.

### Разделы документации
Каждый тег в Swagger соответствует группе эндпоинтов ниже; краткие пояснения — в описании тега.

### Авторизация в Swagger
Вставьте JWT вручную: **Authorize** → HTTP Bearer (токен выдаётся после TWA или OAuth, отдельного `/login` нет).

### Основной сценарий
- **Авторизация** — OAuth или Telegram Web App, получение Bearer-токена.
- **Натальные данные** — ввод даты, времени и места рождения; согласие с политикой при первом сохранении.
- **Тарифы** — актуальный каталог для экрана выбора.
- **Заказы** — выбор тарифа, оплата ЮKassa, список заказов и статус.
- **Отчёты** — скачивание PDF/PNG после готовности расчёта (`/api/v1/reports/...`).
- **Вебхуки** — ЮKassa обновляет статусы оплаты и запускает генерацию отчёта.
- **Служебное** — проверки здоровья и готовности (см. тег).
    """,
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    openapi_tags=_OPENAPI_TAGS,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_cors_origins = [str(origin).rstrip("/") for origin in settings.BACKEND_CORS_ORIGINS]
if settings.ADMIN_APP_ORIGIN:
    _ao = str(settings.ADMIN_APP_ORIGIN).rstrip("/")
    if _ao not in _cors_origins:
        _cors_origins.append(_ao)
if _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Client-Channel"],
    )

app.add_middleware(SecurityHeadersMiddleware)

setup_exception_handlers(app)
app.include_router(api_router, prefix=settings.API_V1_STR)
setup_admin(app)

@app.get("/robots.txt", tags=["Лендинг"], include_in_schema=False)
async def robots_txt():
    base = settings.site_base_url
    body = "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            "Disallow: /api/",
            "",
            f"Sitemap: {base}/sitemap.xml",
            "",
        ]
    )
    return PlainTextResponse(body, media_type="text/plain; charset=utf-8")


@app.get("/sitemap.xml", tags=["Лендинг"], include_in_schema=False)
async def sitemap_xml():
    base = settings.site_base_url
    today = date.today().isoformat()
    entries = [
        ("/", "1.0", "weekly"),
        ("/order/tariff", "0.9", "weekly"),
        ("/dashboard", "0.7", "weekly"),
    ]
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for loc_path, prio, chfreq in entries:
        loc = f"{base}{loc_path}" if loc_path != "/" else f"{base}/"
        lines.append("<url>")
        lines.append(f"<loc>{loc}</loc>")
        lines.append(f"<lastmod>{today}</lastmod>")
        lines.append(f"<changefreq>{chfreq}</changefreq>")
        lines.append(f"<priority>{prio}</priority>")
        lines.append("</url>")
    lines.append("</urlset>")
    return Response(
        content="\n".join(lines),
        media_type="application/xml; charset=utf-8",
    )


@app.get("/", tags=["Лендинг"], include_in_schema=False)
async def landing_index():
    return RedirectResponse(url="/order/tariff", status_code=307)


@app.get("/auth/callback", tags=["Лендинг"], include_in_schema=False)
async def oauth_callback_page():
    return RedirectResponse(url="/order/tariff", status_code=307)


@app.get("/cabinet", tags=["Лендинг"], include_in_schema=False)
async def cabinet_redirect():
    """Статический кабинет удалён; канонический ЛК — React SPA."""
    return RedirectResponse(url="/dashboard", status_code=307)


@app.get("/sample-report.html", tags=["Лендинг"], include_in_schema=False)
async def sample_report_page():
    return RedirectResponse(url="/order/tariff", status_code=307)


@app.get("/privacy", tags=["Лендинг"], include_in_schema=False)
async def privacy_page():
    return RedirectResponse(url="/order/tariff", status_code=307)


@app.get("/oferta", tags=["Лендинг"], include_in_schema=False)
async def oferta_page():
    return RedirectResponse(url="/order/tariff", status_code=307)

@app.get("/health", tags=["Служебное"], summary="Проверка работоспособности")
async def health_check():
    """Liveness: процесс отвечает (без проверки БД/Redis)."""
    return {"status": "ok"}


@app.get(
    "/health/ready",
    tags=["Служебное"],
    summary="Готовность (БД, Redis; опционально Celery)",
    response_model=ReadyResponse,
)
async def health_ready(db: AsyncSession = Depends(get_db)):
    """Readiness: PostgreSQL и Redis; при HEALTH_CHECK_CELERY — ping воркеров и длина очереди."""
    try:
        body = await assert_dependencies_ready(db)
        return ReadyResponse(**body)
    except Exception as exc:
        logger.warning("readiness_failed", error=str(exc))
        raise HTTPException(status_code=503, detail="Service unavailable") from exc