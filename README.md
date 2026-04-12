# Astro (AstroGen)

Backend сервиса онлайн-натальной карты: FastAPI, PostgreSQL, Redis, Celery, ЮKassa, LLM, PDF.

## Требования

- **Python 3.11+** (рекомендуется 3.11; сочетание SQLAlchemy 2.0.x и Python 3.13 может требовать более новой версии SQLAlchemy)
- Docker / Docker Compose — для инфраструктуры

## Быстрый старт (Docker)

1. Скопируйте переменные окружения:

   ```bash
   cp .env.example .env
   ```

   Заполните секреты (Telegram, ЮKassa, SMTP, LLM и т.д.). Для фронтенда задайте **`PUBLIC_APP_URL`** (базовый URL SPA, без завершения пути оплаты): в письмах о готовом отчёте и в OAuth используется `public_app_base_url` из конфига; если переменная не задана, подставляется `YOOKASSA_RETURN_URL`. Согласуйте с фронтом путь к заказу, например `/cabinet/orders/{id}`. Для **canonical / sitemap / Open Graph** задайте при необходимости **`SITE_URL`** (канонический origin); иначе для SEO используется тот же базовый URL, что и `public_app_base_url`.

2. Запуск:

   ```bash
   docker compose up --build
   ```

3. API: `http://localhost:8000`, OpenAPI: `http://localhost:8000/api/v1/openapi.json`, health: `GET /health`.

4. Миграции (из корня репозитория, с установленными зависимостями):

   ```bash
   alembic upgrade head
   ```

## Локальная разработка (без Docker)

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# или: poetry install
```

Запуск приложения (корень репозитория в `PYTHONPATH`):

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Celery:

```bash
celery -A app.tasks.worker.celery_app worker --loglevel=info
celery -A app.tasks.worker.celery_app beat --loglevel=info
```

## Вспомогательные скрипты

Из корня репозитория:

```bash
PYTHONPATH=. python scripts/init_db.py
PYTHONPATH=. python scripts/create_admin.py
```

## Тесты

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

Redis в тестах подменяется на **fakeredis** (in-memory) в `tests/conftest.py` — отдельно поднимать Redis не нужно. Переменные для минимального прогона подставляются в `conftest.py`; при необходимости переопределите их или используйте свой `.env`.

Прогон в CI: workflow `.github/workflows/tests.yml` (GitHub Actions).

## Структура репозитория

Корень проекта — это сам backend (каталога `backend/` нет). Ниже — фактическое дерево исходников.

```
.
├── .env.example
├── .gitignore
├── Caddyfile
├── Dockerfile
├── alembic.ini
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── .github/
│   └── workflows/
│       └── tests.yml
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/           # миграции Alembic (при необходимости добавьте revision)
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── admin/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   └── views.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── auth.py
│   │       ├── natal_data.py
│   │       ├── orders.py
│   │       ├── reports.py
│   │       ├── users.py
│   │       └── webhooks.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── cache.py
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   ├── feature_flags.py
│   │   ├── logging.py
│   │   ├── rate_limit.py
│   │   └── security.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── session.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── natal_data.py
│   │   ├── order.py
│   │   ├── report.py
│   │   ├── tariff.py
│   │   └── user.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── common.py
│   │   ├── llm.py
│   │   ├── natal.py
│   │   ├── order.py
│   │   ├── payment.py
│   │   └── user.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── astrology.py
│   │   ├── auth_twa.py
│   │   ├── email.py
│   │   ├── llm.py
│   │   ├── oauth.py
│   │   ├── oauth_clients.py   # Яндекс / Apple (httpx-oauth без встроенных клиентов)
│   │   ├── payment.py
│   │   ├── pdf.py
│   │   ├── refund.py
│   │   ├── storage.py
│   │   └── tariff.py
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── cleanup.py
│   │   ├── report_generation.py
│   │   ├── scheduler.py         # пояснение к Celery Beat (расписание в worker.py)
│   │   └── worker.py
│   ├── templates/
│   │   ├── email/
│   │   │   ├── refund_processed.html
│   │   │   └── report_ready.html
│   │   └── pdf/
│   │       └── report.html
│   └── utils/
│       ├── __init__.py
│       ├── hashing.py
│       ├── sanitize.py
│       ├── tz.py
│       └── validation.py
├── scripts/
│   ├── create_admin.py
│   └── init_db.py
└── tests/
    ├── conftest.py
    ├── test_api_auth.py
    ├── test_api_natal_data.py
    ├── test_api_orders.py
    ├── test_rate_limit.py
    ├── test_services.py
    └── test_webhooks.py
```

### Описание файлов

**Корень**

| Файл | Назначение |
|------|------------|
| `.env.example` | Шаблон переменных окружения для локального и Docker-запуска |
| `.gitignore` | Исключения для Git (venv, `.env`, кэши и т.д.) |
| `Caddyfile` | Конфиг reverse proxy Caddy (TLS, проксирование на бэкенд) |
| `Dockerfile` | Сборка образа приложения и запуск uvicorn |
| `alembic.ini` | Настройки Alembic (путь к миграциям, БД) |
| `docker-compose.yml` | Сервисы: API, Postgres, Redis, Celery и связанные контейнеры |
| `pyproject.toml` | Метаданные проекта, зависимости Poetry, опции pytest |
| `requirements.txt` | Зафиксированные версии пакетов для `pip install` |
| `requirements-dev.txt` | Зависимости для pytest и fakeredis (ставить вместе с `requirements.txt`) |
| `.github/workflows/tests.yml` | GitHub Actions: установка зависимостей и `pytest` |

**`alembic/`**

| Файл | Назначение |
|------|------------|
| `env.py` | Окружение миграций: подключение к БД, импорт моделей, `run_migrations` |
| `script.py.mako` | Шаблон генерируемых файлов ревизий |
| `versions/` | Файлы миграций схемы БД (revision up/down) |

**`app/`**

| Файл | Назначение |
|------|------------|
| `__init__.py` | Пакет приложения |
| `main.py` | FastAPI: middleware (CORS, security headers), роутеры, lifespan, `GET /health` |

**`app/admin/`** — SQLAdmin: `auth.py` (вход в админку), `views.py` (модели и экраны), `__init__.py`.

**`app/api/`** — `deps.py` (зависимости FastAPI: БД, пользователь); **`v1/`**: `auth.py` (OAuth, TWA), `natal_data.py` (натальные данные), `orders.py` (заказы), `reports.py` (PDF-отчёты), `users.py` (пользователь), `webhooks.py` (вебхуки, например ЮKassa); `__init__.py` в пакетах.

**`app/middleware/`** — `security_headers.py` (CSP и заголовки для HTML).

**`app/core/`** — `cache.py` (Redis), `config.py` (Settings), `exceptions.py` (ошибки API), `feature_flags.py`, `logging.py` (structlog), `rate_limit.py` (slowapi), `security.py` (JWT, пароли).

**`app/db/`** — `base.py` (declarative Base), `session.py` (async engine, сессии, `get_db`).

**`app/models/`** — SQLAlchemy-модели: `user`, `natal_data`, `order`, `report`, `tariff`.

**`app/schemas/`** — Pydantic-схемы API: `common`, `natal`, `order`, `payment`, `user`, `llm`.

**`app/services/`** — бизнес-логика: `astrology` (расчёты), `auth_twa` (Telegram Web App), `email`, `llm`, `oauth` / `oauth_clients` (Яндекс, Apple), `apple_id_token` (проверка Apple `id_token` по JWKS), `payment` (ЮKassa), `pdf`, `refund`, `storage` (файлы отчётов), `tariff` (тарифы и кеш).

**`app/tasks/`** — Celery: `worker.py` (приложение и beat), `report_generation.py`, `cleanup.py`, `scheduler.py` (пояснения к расписанию).

**`app/templates/`** — `email/*.html` (письма: отчёт готов, возврат), `pdf/report.html` (шаблон PDF).

**`app/utils/`** — `hashing`, `sanitize`, `tz`, `validation`, `email_policy` (плейсхолдер-email для чеков), `landing_html` (подстановки SEO в статический HTML).

**`scripts/`** — `init_db.py` (инициализация БД), `create_admin.py` (учётка администратора).

**`tests/`** — `conftest.py` (фикстуры, SQLite in-memory, подмена Redis через fakeredis); `test_api_*`, `test_services`, `test_rate_limit`, `test_webhooks`.

### Фронтенд и HTML-макеты

- **Продакшен:** отдаётся только содержимое каталога **`static/`** (HTML/CSS/JS); роуты в `app/main.py` (`/`, `/cabinet`, юридические страницы и т.д.).
- Каталог **`HTML макеты/`** (если присутствует в репозитории) — визуальные референсы и черновики; актуальная вёрстка для пользователей — в **`static/`**. Переносите изменения из макетов в `static/` осознанным PR.

### SEO и языки

- Эндпоинты **`GET /robots.txt`** и **`GET /sitemap.xml`** собираются из `site_base_url` в конфиге (`SITE_URL` или, если не задан, `public_app_base_url`).
- В **`static/index.html`** используются плейсхолдеры `__SITE_BASE_URL__` и `__META_VERIFICATIONS__`; при отдаче страницы подставляются значения из `.env` (`GOOGLE_SITE_VERIFICATION`, `YANDEX_VERIFICATION`, `BING_SITE_VERIFICATION` — опционально).
- Переключение языка на лендинге через JS не создаёт отдельный индексируемый URL; полноценная английская версия для международного SEO (например статический `/en/` и `hreflang`) — отдельная задача.

### Чеклист релиза (прод)

1. Заполнены секреты и URL: `SECRET_KEY`, `PUBLIC_APP_URL`, при необходимости **`SITE_URL`**, PostgreSQL, Redis, SMTP, `DEEPSEEK_API_KEY`, ЮKassa, `TELEGRAM_BOT_TOKEN`, OAuth.
2. Выполнены миграции: `alembic upgrade head`.
3. Запущены процессы: API (uvicorn/gunicorn), **Celery worker**, **Celery beat** (подписки и отчёты).
4. Проверка **`GET /health/ready`** (PostgreSQL и Redis).
5. За reverse proxy: доверенные заголовки для IP клиента (важно для вебхуков ЮKassa), список **`BACKEND_CORS_ORIGINS`**.
6. При необходимости: **`SENTRY_DSN`**, верификация сайта в поисковиках (мета-теги через переменные в `.env`), отправка sitemap в кабинетах Google / Яндекс.
7. Контрольный тестовый платёж в ЮKassa (тестовый магазин) и обработка вебхука.
8. Включить **`SENTRY_DSN`** для продакшена (ошибки API и необработанные исключения).

### Прокси, IP и вебхуки ЮKassa

- ЮKassa шлёт уведомления с фиксированных IP; опционально включается проверка **`YOOKASSA_WEBHOOK_VERIFY_IP`**. Реальный IP клиента берётся из запроса ([`app/utils/client_ip.py`](app/utils/client_ip.py)): учитывайте **`X-Forwarded-For`** только если reverse proxy **один доверенный** и подставляет заголовок честно; иначе возможны ложные отказы 401 на `/api/v1/webhooks/yookassa`.
- Для проверки соответствия события API используется **`YOOKASSA_WEBHOOK_VERIFY_API`**.

### Таймауты и внешние API

- **Геокодинг** ([`app/api/v1/geocode.py`](app/api/v1/geocode.py)): Nominatim, таймаут HTTP **20 с**.
- **LLM** ([`app/services/llm.py`](app/services/llm.py)): DeepSeek через OpenAI-клиент; при **429/5xx** срабатывает **tenacity** (до 3 попыток, экспоненциальная задержка). Итоговые ошибки попадают в лог и в задаче отчёта заказ может перейти в `FAILED`.

### Celery: очередь и сбои

- Следите за длиной очереди Redis и за ошибками воркера. Задача отчёта: `generate_report_task` (ретраи встроены).
- После исправления причины сбоя отчёт можно **перезапустить вручную** (повторный `delay(order_id)` из shell/admin при согласовании с продуктом) или повторным сценарием оплаты — в зависимости от политики поддержки.
- Отдельная очередь «dead letter» в коде не обязательна на старте; при росте нагрузки вынесите failed tasks в мониторинг.

### API: идемпотентность и типовые ответы

- **`POST /api/v1/orders/`** каждый раз создаёт **новый** заказ. Идемпотентность на стороне клиента (кнопка «Оплатить» один раз, свой ключ в UI) или будущий серверный dedup — отдельная задача. Вызов **ЮKassa** `Payment.create` использует **idempotency_key** = `str(order_id)` ([`app/services/payment.py`](app/services/payment.py)).
- Версия API: префикс **`/api/v1`**. Ломающие изменения — только со сменой версии (`/api/v2`) или согласованием клиентов.

Типовые поля **`detail`** (строка или список при 422):

| Ситуация | Пример `detail` |
|----------|-----------------|
| Нет JWT | `Not authenticated` |
| Нет согласия с политикой | `User consent required` |
| Нет email для чека/отчёта (Telegram и т.п.) | `Укажите report_delivery_email: для аккаунта без реальной почты нужен email для отчёта и чека.` |
| Провайдер оплаты недоступен | `Payment provider unavailable...` |

### Безопасность: CSP и заголовки

- Для ответов **`Content-Type: text/html`** приложение выставляет **Content-Security-Policy** (см. [`app/middleware/security_headers.py`](app/middleware/security_headers.py)) и `X-Content-Type-Options`, `Referrer-Policy`. JSON API тело политики не дублирует строгим CSP.
- Дополнительно можно настроить заголовки на reverse proxy ([`Caddyfile`](Caddyfile)).

### OG-картинка и favicon

- Превью для соцсетей: **`static/images/og-default.png`** (1200×630). Пересборка: `pip install -r requirements-dev.txt` и `python scripts/generate_og_default.py`.
- Иконка сайта: **`static/favicon.svg`**, подключена в `static/index.html`.

См. также [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Полезные заметки

- Точка входа ASGI: `app.main:app` (см. `Dockerfile` и `docker-compose.yml`).
- Том `./app` монтируется в контейнер как `/app/app` — весь код приложения должен лежать в каталоге `app/`.
- Шаблоны PDF: `app/templates/pdf/` (путь задаётся в `app/services/pdf.py`).
