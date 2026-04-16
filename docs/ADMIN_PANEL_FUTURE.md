# Админ-панель: фактический статус и дальнейший backlog

Последняя верификация: `2026-04-15`

Документ обновлён под текущее состояние репозитория: часть разделов, ранее помеченных как "future", уже имеет UI и API, но часть из них реализована на заглушках или упрощённых данных.

## Что уже есть в коде

- Экран и API воронки: `frontend-admin/src/pages/FunnelPage.tsx`, `GET /api/v1/admin/funnel/summary`.
- Экран и API платежей: `frontend-admin/src/pages/PaymentsPage.tsx`, `GET /api/v1/admin/payments`.
- Экран и API задач: `frontend-admin/src/pages/TasksPage.tsx`, `GET /api/v1/admin/tasks`.
- Экран и API промокодов: `frontend-admin/src/pages/PromosPage.tsx`, `GET/POST/PATCH /api/v1/admin/promos`.
- Экран и API feature flags: `frontend-admin/src/pages/FlagsPage.tsx`, `GET/PATCH /api/v1/admin/flags`.
- Экран мониторинга и логов действий: `HealthPage`, `ActionLogPage`, API `/api/v1/admin/health`, `/api/v1/admin/logs`.
- Экран управления LLM-промптами: `frontend-admin/src/pages/PromptsPage.tsx`, API `/api/v1/admin/prompts`, маршрут `/prompts` и пункт меню включены.
- Growth & Economics (v1): `frontend-admin/src/pages/GrowthEconomicsPage.tsx`, API `/api/v1/admin/metrics/*` (overview/funnel/cohorts/economics) и manual marketing spend `/api/v1/admin/metrics/spend`.

## Что остаётся до продового уровня

### 0) LLM Prompts: production-контур

- Готово: подключен `prompts`-router, включены маршрут `/prompts` и пункт меню, smoke `list -> edit -> reset` проведён.

### 1) Промокоды (из in-memory/cache в БД)

- Готово (v1): промокоды и применения персистятся в БД (`promocodes`, `promocode_redemptions`), CRUD и audit доступны в админке, применение работает через `POST /api/v1/orders/`.
- Остаётся: проверить, что все клиентские checkout-потоки передают `promo_code` корректно, и добавить экспорт/retention контракта для redemption-логов.

### 2) Feature flags (из кеша в управляемую конфигурацию)

- Частично готово: флаги и изменения персистятся в БД с аудитом; API админки и meta для UI работают.
- Остаётся: перевести runtime-резолвер (где именно флаг применяется) на DB-backed / read-through режим без зависимости только от `feature:*` кеш-ключей.

### 3) Воронка и аналитика (event-based foundation -> витрины)

- Growth & Economics (v1) доступен: метрики считаются из агрегатов пользователей/заказов + manual marketing spend, с атрибуцией через `utm_*` пользователя и fallback `source_channel`.
- Остаётся (для event-based строгости):
  - доделать недостающие события (`addon_attached`, `refund_completed`, `acquisition_cost_recorded`);
  - перевести админ-витрины воронки/retention на расчёты строго по `analytics_events`, а не по упрощённым агрегатам.

### 4) Задачи/Celery (операционная observability)

- Готово (v1): `/api/v1/admin/tasks` теперь берёт snapshot через `celery inspect` и деградирует при недоступности Celery/Redis.

### 5) Платежи и action log (операционная глубина)

- Готово (v1): расширены фильтры платежей (provider/tariff/payment_id/email/date range), action log переведён в DB-backed storage.
- Остаётся: SLA/retention contract и полноценный export timeline (в UI пока без экспорта).

## Как трактовать "готовность админки" сейчас

- Для операционной поддержки заказов, пользователей и тарифов текущая админка пригодна.
- Для финансового аудита и управляемой продуктовой аналитики (строго event-based, retention из когорт по событиям) требуется следующий цикл доработок.
