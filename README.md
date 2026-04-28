# Astro (AstroGen)

Сервис онлайн-натальной карты: **FastAPI** (PostgreSQL, Redis, Celery, ЮKassa, LLM, PDF), **пользовательское React SPA** (`frontend/`), **админ-SPA** (`frontend-admin/`).

## Документация

- Product flow, бизнес-логика и маршруты SPA: [`docs/PRODUCT_FLOW_AND_BUSINESS_LOGIC.md`](docs/PRODUCT_FLOW_AND_BUSINESS_LOGIC.md)
- Прод-ready, масштабирование и post-launch план: [`docs/PRODUCTION_READINESS_AND_GROWTH_PLAN.md`](docs/PRODUCTION_READINESS_AND_GROWTH_PLAN.md)
- URL для внешних интеграций (OAuth/ЮKassa/почта): [`docs/DEPLOY_URLS.md`](docs/DEPLOY_URLS.md)
- Аудит рисков (безопасность, эксплуатация): [`docs/CODE_REVIEW_RISK_ASSESSMENT_P0_P3.md`](docs/CODE_REVIEW_RISK_ASSESSMENT_P0_P3.md)
- Полноценная SEO-стратегия (цели, техника, контент, off-page, метрики): [`docs/SEO_STRATEGY_FULL.md`](docs/SEO_STRATEGY_FULL.md)

## Требования

- **Python 3.12.x** — поддерживаемая ветка для backend, pytest и Docker-образа (файл [`.python-version`](.python-version), `Dockerfile`, [CI](.github/workflows/tests.yml)). Устанавливайте зависимости из корня: `python3.12 -m pip install -r requirements.txt` (и при тестах `-r requirements-dev.txt`).
- **Python 3.13** в матрицу совместимости пока не входит: при прогоне `pytest` возможны ошибки импорта SQLAlchemy из‑за typing; для локальной разработки используйте **3.12** или запускайте тесты в Docker/CI.
- Docker / Docker Compose — для инфраструктуры

## Быстрый старт (Docker)

1. Скопируйте переменные окружения:

   ```bash
   cp .env.example .env
   ```

   Заполните секреты (Telegram, ЮKassa, SMTP, LLM и т.д.). Для фронтенда задайте **`PUBLIC_APP_URL`** (базовый URL SPA): в письмах о готовом отчёте ссылка ведёт на **`/reports/{order_id}`**; если переменная не задана, подставляется `YOOKASSA_RETURN_URL`. Для **canonical / sitemap / Open Graph** задайте **`SITE_URL`**. Таблица URL для ЮKassa и OAuth: [`docs/DEPLOY_URLS.md`](docs/DEPLOY_URLS.md). Секреты для прода генерируйте отдельно (не копируйте `.env.example`): `bash scripts/generate_production_secrets.sh`.

2. Запуск:

   ```bash
   docker compose up --build
   ```

3. API: `http://localhost:8000`, OpenAPI: `http://localhost:8000/api/v1/openapi.json`, health: `GET /health`. Публичный вход и заказ — **React SPA** и статический лендинг в `frontend/public/static/` (корень `/`, маршруты `/order/...`, `/dashboard/...`, `/reports/...`; см. `Caddyfile` и [`docs/PRODUCT_FLOW_AND_BUSINESS_LOGIC.md`](docs/PRODUCT_FLOW_AND_BUSINESS_LOGIC.md)).

4. Миграции (из корня репозитория, с установленными зависимостями):

   ```bash
   alembic upgrade head
   ```

**Продакшен (отдельный Compose):** [`docker-compose.prod.yml`](docker-compose.prod.yml) — образ приложения **без** монтирования `./app`; том только для `storage`. Сборка SPA в каталоги для Caddy: `cd frontend && npm run build:deploy` (→ `frontend-dist/`) и `cd ../frontend-admin && npm run build` (→ `frontend-admin/dist/`). Запуск: `docker compose -f docker-compose.prod.yml --env-file .env up -d`. Черновик Caddy с доменом (включая `admin.<домен>` для админ-SPA): [`deploy/Caddyfile.prod.example`](deploy/Caddyfile.prod.example). Резервное копирование БД и `storage`: [`scripts/backup_all.sh`](scripts/backup_all.sh) (см. [`docs/PRODUCTION_READINESS_AND_GROWTH_PLAN.md`](docs/PRODUCTION_READINESS_AND_GROWTH_PLAN.md)).

## Локальная разработка (без Docker)

```bash
python3.12 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
# или: poetry install  (python = ">=3.12,<3.13" в pyproject.toml)
```

Запуск приложения (корень репозитория в `PYTHONPATH`):

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Celery:

```bash
# default queue worker (легкие/прочие задачи по умолчанию)
celery -A app.tasks.worker.celery_app worker -Q default --loglevel=info --hostname=worker-default@%h

# io queue worker (cleanup/digest/subscription)
celery -A app.tasks.worker.celery_app worker -Q io --loglevel=info --hostname=worker-io@%h

# heavy queue worker (report/synastry generation)
celery -A app.tasks.worker.celery_app worker -Q heavy --loglevel=info --hostname=worker-heavy@%h

# beat — отдельным процессом
celery -A app.tasks.worker.celery_app beat --loglevel=info
```

Минимальный rollout по очередям:

1. Сначала деплой только `task_routes` при одном worker и проверка маршрутизации.
2. Затем поднимаем отдельный `heavy` worker.
3. После стабилизации — физически разделяем `io` и `default` воркеры.

## Пользовательское SPA (`frontend`)

```bash
cd frontend
cp .env.example .env   # при необходимости задайте переменные Vite
npm install
npm run dev            # http://localhost:5173; прокси /api → http://localhost:8000
```

Сборка для Caddy (каталог рядом с репозиторием): `npm run build:deploy` → `frontend-dist/` (см. раздел про `docker-compose.prod.yml` выше). Тесты UI: `npm run test`.

## Вспомогательные скрипты

Из корня репозитория:

```bash
PYTHONPATH=. python scripts/init_db.py
PYTHONPATH=. python scripts/create_admin.py
```

Продакшен (stack из `docker-compose.prod.yml` должен быть запущен; артефакты по умолчанию в `./backups/`):

```bash
./scripts/backup_postgres.sh    # pg_dump → backups/astro_pg_<timestamp>.dump.gz
./scripts/backup_storage.sh     # tar.gz тома storage
./scripts/backup_all.sh         # оба подряд
./scripts/verify_pg_backup.sh backups/astro_pg_<timestamp>.dump.gz
```

Расписание (cron), ротация старых файлов и учебное восстановление — в [`docs/PRODUCTION_READINESS_AND_GROWTH_PLAN.md`](docs/PRODUCTION_READINESS_AND_GROWTH_PLAN.md).

## Админ-панель (`frontend-admin`)

Отдельное SPA для операторов: дашборд и метрики, заказы (перезапуск отчёта, PDF/PNG, возврат), пользователи, тарифы, промпты LLM, feature flags, воронка, промокоды, задачи Celery и др. REST API: `/api/v1/admin/*`. Вход через Google: `/api/v1/auth/google/authorize-admin`. Переменные окружения (`ADMIN_APP_ORIGIN`, allowlist админов) и выкладка на поддомен — в [`docs/PRODUCTION_READINESS_AND_GROWTH_PLAN.md`](docs/PRODUCTION_READINESS_AND_GROWTH_PLAN.md).

```bash
cd frontend-admin
cp .env.example .env   # при необходимости: VITE_API_BASE_URL=http://localhost:8000
npm install
npm run dev            # http://localhost:5174; в vite прокси /api → localhost:8000
```

Продакшен: `npm run build` → статика в `frontend-admin/dist/`.

**Ручная проверка перед запуском:** вход под админом → дашборд → заказы (фильтры, drawer) → пользователи → тарифы. Не-админ после OAuth должен попасть на страницу отказа.

## Тесты

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

Redis в тестах подменяется на **fakeredis** (in-memory) в `tests/conftest.py` — отдельно поднимать Redis не нужно. Переменные для минимального прогона подставляются в `conftest.py`; при необходимости переопределите их или используйте свой `.env`.

Прогон в CI: workflow `.github/workflows/tests.yml` (GitHub Actions).

## Структура репозитория

Монорепозиторий: backend в `app/`, пользовательское и админское SPA, документация. Исчерпывающий список HTTP-роутов — в `app/api/v1/` и `app/api/v1/admin/` (подключение в `app/api/v1/__init__.py`).

```
.
├── app/                      # FastAPI: API, модели, сервисы, Celery, шаблоны PDF/email, middleware
├── frontend/                 # пользовательское React SPA; public/static — лендинг для «/»
├── frontend-admin/           # админ React SPA
├── docs/                     # продукт, деплой, аудит рисков
├── alembic/                  # env.py, script.py.mako, versions/ (миграции)
├── scripts/                  # init_db, create_admin, seed_tariffs, backup_*.sh, verify_pg_backup, …
├── deploy/                   # примеры Caddy для prod
├── tests/                    # pytest; Redis — fakeredis в conftest
├── .github/workflows/        # CI (pytest)
├── docker-compose.yml
├── docker-compose.prod.yml
├── Caddyfile
├── Dockerfile
├── alembic.ini
├── requirements.txt
├── requirements-dev.txt
└── pyproject.toml
```

### Описание ключевых каталогов

| Каталог | Содержание |
|---------|------------|
| **`app/api/v1/`** | Публичные роутеры: `auth`, `users`, `natal_data`, `tariffs`, `orders`, `reports`, `subscriptions`, `synastry`, `addons`, `geocode`, `webhooks`, `system`, `ops` и др. |
| **`app/api/v1/admin/`** | REST админки: дашборд, заказы, пользователи, тарифы, промпты LLM, флаги, метрики, воронка, промокоды, логи, задачи и т.д. |
| **`app/services/`** | Доменная логика: астрология, LLM, PDF, ЮKassa, почта, хранилище, промпты, синастрия, аналитика, возвраты и др. |
| **`app/tasks/`** | Celery: `worker.py` (в т.ч. beat), `report_generation`, `synastry_generation`, cleanup, уведомления |
| **`app/models/`**, **`app/schemas/`** | Модели SQLAlchemy и Pydantic-схемы (много файлов; ориентир — импорты в соответствующих роутерах) |
| **`app/admin/`** | SQLAdmin (`auth.py`, `views.py`) — обход основного admin-SPA |
| **`app/core/`** | `config`, `cache`, JWT, rate limit, feature flags, логирование |
| **`scripts/`** | Инициализация БД и админа, сиды тарифов, скрипты бэкапа и проверки дампов |

Дополнительно: **`app/middleware/`** (например `security_headers.py`), **`app/utils/`** (sanitize, IP, email policy и т.д.), **`app/templates/`** (email и PDF).

### Фронтенд и HTML-макеты

- **Продакшен:** пользовательская сборка **React SPA** → `frontend-dist/` через Caddy; лендинг на `/` может отдаваться из `frontend/public/static/` (см. `LandingPage` и `Caddyfile`). Backend — API, `robots.txt` / `sitemap.xml`, health.
- Каталог **`HTML макеты/`** (если есть) — визуальные референсы; актуальный UI — `frontend/src/`.

### SEO и языки

- Эндпоинты **`GET /robots.txt`** и **`GET /sitemap.xml`** собираются из `site_base_url` в конфиге (`SITE_URL` или, если не задан, `public_app_base_url`).
- В sitemap включены актуальные SPA-маршруты (`/order/tariff`, `/dashboard`) как публичные точки входа.
- Переключение языка в SPA клиентское; полноценная SEO-стратегия с отдельными индексируемыми локализованными URL — отдельная задача.

### Чеклист релиза (прод)

1. Заполнены секреты и URL: `SECRET_KEY`, `PUBLIC_APP_URL`, при необходимости **`SITE_URL`**, PostgreSQL, Redis, SMTP, `DEEPSEEK_API_KEY`, ЮKassa, `TELEGRAM_BOT_TOKEN`, OAuth.
2. Выполнены миграции: `alembic upgrade head`.
3. Запущены процессы: API (uvicorn/gunicorn), **Celery worker**, **Celery beat** (подписки и отчёты).
4. Проверка **`GET /health/ready`** (PostgreSQL и Redis).
5. За reverse proxy: доверенные заголовки для IP клиента (важно для вебхуков ЮKassa), список **`BACKEND_CORS_ORIGINS`**.
6. Для продакшена: **`SENTRY_DSN`** (ошибки API и необработанные исключения), при необходимости верификация сайта в поисковиках (мета через `.env`), отправка sitemap в кабинеты Google / Яндекс.
7. Контрольный тестовый платёж в ЮKassa (тестовый магазин) и обработка вебхука.

### Прокси, IP и вебхуки ЮKassa

- **OAuth и HTTPS:** в консолях Google / Яндекс указывайте redirect URI как **`https://ваш-домен/...`** ([`docs/DEPLOY_URLS.md`](docs/DEPLOY_URLS.md)). Uvicorn подставляет схему из **`X-Forwarded-Proto`**, если IP прокси входит в **`FORWARDED_ALLOW_IPS`** (в `docker-compose.yml` / `docker-compose.prod.yml` для `fastapi` задано по умолчанию для частных Docker-сетей). Иначе в `redirect_uri` останется `http://` и обмен кода с провайдером может не совпасть с зарегистрированным URI.
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

- **`POST /api/v1/orders/`** поддерживает заголовок **`Idempotency-Key`**: повтор с тем же ключом и тем же телом возвращает тот же заказ/ответ; параллельные запросы блокируются; зависший `processing` снимается по TTL. Реализация: [`app/api/v1/orders.py`](app/api/v1/orders.py), модель `order_idempotency`. Вызов **ЮKassa** `Payment.create` дополнительно получает `idempotency_key` при создании оплаты ([`app/services/payment.py`](app/services/payment.py)).
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

- Превью и favicon задаются в сборке SPA (`frontend/`) и проксируются Caddy вместе с `frontend-dist`.

См. также [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Полезные заметки

- Точка входа ASGI: `app.main:app` (см. `Dockerfile` и `docker-compose.yml`).
- Том `./app` монтируется в контейнер как `/app/app` — весь код приложения должен лежать в каталоге `app/`.
- Шаблоны PDF: `app/templates/pdf/` (путь задаётся в `app/services/pdf.py`).
