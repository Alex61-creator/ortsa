# Product Flow and Business Logic

Версия: `v1.0`  
Дата обновления: `2026-04-16`

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
- в ops-метриках добавлены `paid->completed` latency p50/p95.

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
- `/orders/*` — создание/чтение заказа, retry payment.
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

## 7. Актуальные разрывы до production-stable

- Довести prompts-контур админки до полного runtime-подключения.
- Завершить идемпотентность `POST /orders` (создание заказа без дублей).
- Доформализовать incident/release runbook и DR-процедуры.

Подробный план закрытия:

- [`PRODUCTION_READINESS_AND_GROWTH_PLAN.md`](./PRODUCTION_READINESS_AND_GROWTH_PLAN.md)

---

## 8. Связанные документы

- Продукт и экономика 3-5 лет: [`PRODUCT_AND_ECONOMICS_STRATEGY_3_5_YEARS.md`](./PRODUCT_AND_ECONOMICS_STRATEGY_3_5_YEARS.md)
- Прод-ready и post-launch план: [`PRODUCTION_READINESS_AND_GROWTH_PLAN.md`](./PRODUCTION_READINESS_AND_GROWTH_PLAN.md)
- Интеграционные URL: [`DEPLOY_URLS.md`](./DEPLOY_URLS.md)
