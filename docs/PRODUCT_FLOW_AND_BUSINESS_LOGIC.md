# Product Flow and Business Logic

Версия: `v1.1`  
Дата обновления: `2026-04-22`

Документ объединяет:

- `BUSINESS_LOGIC.md`
- `CLIENT_PIPELINE_AND_STAGE.md`
- `ROUTING_MAP.md`

Цель: единая картина пользовательского пути, API-логики и маршрутизации SPA.

---

## 1. Стадия и рамка

Стадия: **late MVP / pre-production hardening**.

Текущее состояние:

- клиентская воронка и платежный контур реализованы;
- есть async pipeline (Celery) и доставка отчета;
- `report_generation` приведен к целостному пайплайну `chart -> llm -> pdf` для single/bundle;
- webhook dedupe переведен на устойчивый lifecycle `processing/processed/failed`;
- в ops-метриках добавлены `paid->completed` latency p50/p95;
- создание заказа `POST /orders` поддерживает идемпотентность по заголовку `Idempotency-Key` (см. `app/api/v1/orders.py`, модель `OrderIdempotency`);
- системные промпты LLM: админка (`/api/v1/admin/prompts/*`) пишет в БД, кэш инвалидируется при save/reset, пайплайн генерации подхватывает шаблон из `PromptTemplateService` (`app/tasks/report_generation.py`).

---

## 2. Ключевые сущности

- `User`: OAuth/Telegram авторизация, JWT, роль админа через allowlist.
- `NatalData`: профиль рождения (дата, время, место, координаты, timezone, locale).
- `Tariff`: код, цена, llm-tier, политики отчета/подписки.
- `Order`: статусный жизненный цикл заказа.
- `Report`: PDF + артефакты, статус генерации.

Базовый статусный поток заказа:

`PENDING -> PAID -> PROCESSING -> COMPLETED/FAILED`

---

## 3. End-to-end клиентский путь

1. Пользователь открывает `/`.
2. Авторизуется через OAuth/TWA.
3. Выбирает тариф на `/order/tariff`.
4. Вводит натальные данные на `/order/data` (+ геокод).
5. Подтверждает заказ на `/order/confirm`.
6. Оплачивает (для платных) через ЮKassa.
7. Вебхук переводит заказ в `PAID` и запускает Celery.
8. Генерация: chart -> LLM -> PDF -> storage.
9. Email доставка + просмотр/скачивание на `/reports/:orderId`.

---

## 4. Роутинг SPA (каноника)

Публичный:

- `/` — лендинг.

Защищенные:

- `/dashboard/*`
- `/order/*`
- `/reports/:orderId`

Поддерживаемые редиректы:

- `/cabinet` -> `/dashboard`
- `/cabinet/orders/:orderId` -> `/reports/:orderId`
- временные публичные заглушки (`/privacy`, `/oferta`, `/sample-report.html`) редиректят на `/`

---

## 5. Канонические API области (`/api/v1`)

- `/auth/*` — OAuth/TWA.
- `/natal-data/*` — профили рождения.
- `/orders/*` — создание заказа (опционально `Idempotency-Key`), чтение, retry payment.
- `/tariffs/*` — публичный каталог.
- `/webhooks/yookassa` — платежные уведомления.
- `/reports/{order_id}/download|chart` — выдача артефактов.
- `/subscriptions/*` — подписка.
- `/admin/*` — административный контур.
- `/system/*` + корневые `/health`, `/health/ready` — liveness/readiness.

---

## 6. Основные правила и ограничения

- Доступ к заказам/отчетам только для владельца.
- Для некоторых пользовательских сценариев обязателен `report_delivery_email`.
- Без JWT защищенные роуты не доступны.
- Для генерации отчета обязательны валидные натальные данные и валидный статус заказа.

---

## 7. Критичные контуры и оставшиеся разрывы до production-stable

**Уже реализовано в продуктовом контуре (раньше ошибочно числилось в «разрывах»):**

- **Идемпотентность `POST /orders`:** клиент может передавать `Idempotency-Key`; сервер ведёт запись в `order_idempotency`, различает повтор с тем же телом запроса, блокирует параллельное создание, по TTL снимает «зависший» `processing`, привязывает к ЮKassa и ответу заказа. Реализация: `app/api/v1/orders.py`, `app/models/order_idempotency.py`.
- **Промпты админки и runtime:** CRUD шаблонов `LlmPromptTemplate` через `/api/v1/admin/prompts/…`, после сохранения или сброса вызывается `PromptTemplateService.invalidate`; генерация отчёта подставляет системный промпт из БД при наличии записи, иначе — дефолт из `LLMService.build_system_prompt`. Реализация: `app/api/v1/admin/prompts.py`, `app/services/prompt_templates.py`, `app/tasks/report_generation.py`.

**По-прежнему процессные / вне кода приложения:**

- **Incident и release runbook, DR:** формализованные сценарии инцидентов, выката, отката и учебное восстановление из бэкапов — вести по [`PRODUCTION_READINESS_AND_GROWTH_PLAN.md`](./PRODUCTION_READINESS_AND_GROWTH_PLAN.md).

**Технический долг, влияющий на безопасность и эксплуатацию (не описание user flow, но важно до prod):**

- Отдельный аудит: [`CODE_REVIEW_RISK_ASSESSMENT_P0_P3.md`](./CODE_REVIEW_RISK_ASSESSMENT_P0_P3.md) (JWT в URL, хранение токена в SPA, периметр вебхуков, CSP и др.).

**Заметка по API админ-дашборда:** поле `analytics_stub` в `GET /api/v1/admin/dashboard/summary` исторически осталось в схеме ответа и сейчас всегда `false`; на бизнес-метрики заказов и сводки в ответе не влияет. При необходимости убрать из контракта или снова осмыслить отдельной задачей.

---

## 8. Связанные документы

- Продукт и экономика 3-5 лет: [`PRODUCT_AND_ECONOMICS_STRATEGY_3_5_YEARS.md`](./PRODUCT_AND_ECONOMICS_STRATEGY_3_5_YEARS.md)
- Прод-ready и post-launch план: [`PRODUCTION_READINESS_AND_GROWTH_PLAN.md`](./PRODUCTION_READINESS_AND_GROWTH_PLAN.md)
- Интеграционные URL: [`DEPLOY_URLS.md`](./DEPLOY_URLS.md)
- Аудит рисков (безопасность, эксплуатация): [`CODE_REVIEW_RISK_ASSESSMENT_P0_P3.md`](./CODE_REVIEW_RISK_ASSESSMENT_P0_P3.md)
