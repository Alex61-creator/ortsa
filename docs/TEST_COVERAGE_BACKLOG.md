# Test Coverage Backlog (P0 -> P2)

Цель: довести проект до предсказуемого и достаточного покрытия тестами без "ложного" процента покрытия.

## 1) Definition of Done по покрытию

- Backend: `pytest --cov=app --cov-report=term-missing --cov-fail-under=90`
- Frontend (`frontend`): `vitest --coverage` c порогом branch coverage `>= 80%`
- Admin (`frontend-admin`): `vitest --coverage` c порогом branch coverage `>= 80%`
- E2E: обязательные smoke + платежный сценарий + регрессия админских действий
- Для money-critical и access-critical модулей: обязательные инвариантные тесты и негативные сценарии

## 2) P0 (критично, закрыть в первую очередь)

### 2.1 Backend API

- `app/api/v1/orders.py`
  - Идемпотентность `Idempotency-Key` (повтор с тем же body, конфликт при другом body, TTL unlock)
  - Негативные сценарии оплаты (провайдер недоступен, некорректные данные, race)
- `app/api/v1/webhooks.py`
  - Валидация подписи/IP/API verification
  - Повторные webhook-события (дедупликация, отсутствие двойных списаний/двойной генерации)
- `app/api/v1/subscriptions.py`
  - Продление/отмена/истечение, корректная реакция на просроченные статусы
- `app/api/v1/auth.py`
  - JWT edge cases, истекшие/некорректные токены, роли и доступ

### 2.2 Backend Services (деньги и доступ)

- `app/services/payment.py`
  - Идемпотентное создание платежа, корректные metadata, сбои провайдера
- `app/services/refund.py`
  - Частичный/полный refund, повторный refund, согласованность статусов заказа
- `app/services/yookassa_webhook.py`
  - Парсинг/валидация входящих событий, безопасная обработка неизвестных event type
- `app/services/oauth.py`, `app/services/oauth_state.py`, `app/services/apple_id_token.py`
  - Защита от replay/state mismatch, отказ при невалидных токенах
- `app/services/admin_allowlist.py`
  - Доступ только allowlist-пользователям, отказ по всем невалидным вариантам email

### 2.3 Celery / Background tasks

- `app/tasks/report_generation.py`
  - Успешная генерация, retry при временном сбое LLM/PDF, корректный финальный статус
- `app/tasks/synastry_generation.py`
  - Аналогично report generation, плюс edge cases входных данных
- `app/tasks/subscription_renewal.py`, `app/tasks/subscription_finalize.py`
  - Корректный lifecycle подписки при сбоях платежа и при успешном списании
- `app/tasks/worker.py`
  - Проверка маршрутизации очередей (`default/io/heavy`) и регистрации задач

### 2.4 Frontend (user SPA)

- `frontend/src/routes/AppRoutes.tsx`, `frontend/src/components/ProtectedRoute.tsx`
  - Редиректы неавторизованных, доступ авторизованных, fallback-роуты
- `frontend/src/pages/order/OrderTariffPage.tsx`
- `frontend/src/pages/order/OrderDataPage.tsx`
- `frontend/src/pages/order/OrderConfirmPage.tsx`
- `frontend/src/pages/order/OrderStatusPage.tsx`
  - Full happy path заказа + ошибки API + повторная отправка
- `frontend/src/api/orders.ts`, `frontend/src/api/reports.ts`, `frontend/src/api/subscriptions.ts`
  - 401/403/429/5xx, корректная нормализация ошибок

### 2.5 Frontend Admin

- `frontend-admin/src/components/ProtectedRoute.tsx`
- `frontend-admin/src/pages/LoginPage.tsx`
- `frontend-admin/src/pages/AuthCallbackPage.tsx`
- `frontend-admin/src/pages/AccessDeniedPage.tsx`
  - Полный auth flow и access denial
- `frontend-admin/src/api/orders.ts`, `frontend-admin/src/api/payments.ts`, `frontend-admin/src/api/tasks.ts`
  - Обработка ошибок и корректная сериализация query/filters
- `frontend-admin/src/utils/apiError.ts`
  - Единый формат пользовательских ошибок для UI

## 3) P1 (важно, после стабилизации P0)

### 3.1 Backend API и Services

- `app/api/v1/geocode.py`
  - Timeout, отказ внешнего геокодера, пустые результаты, нормализация ответа
- `app/api/v1/report_order_options.py`
  - Валидность комбинаций опций и pricing rules
- `app/api/v1/system.py`
  - Health/system info контракты и fallback-поведение
- `app/services/llm_router.py`, `app/services/llm_client.py`, `app/services/llm_validator.py`
  - Роутинг по tier, retry/backoff, корректный reject небезопасного/битого ответа
- `app/services/unisender.py`, `app/services/email.py`
  - Ошибки доставки, policy fallback, повторная отправка по правилам

### 3.2 Stores/hooks и клиентская логика

- `frontend/src/stores/orderWizardStore.ts`
- `frontend/src/stores/themeStore.ts`
- `frontend/src/hooks/useTwaEnvironment.ts`
- `frontend/src/hooks/useEffectiveThemeMode.ts`
  - Unit-тесты состояния, миграции состояния и browser/env edge cases
- `frontend-admin/src/stores/authStore.ts`
- `frontend-admin/src/stores/uiStore.ts`
  - Unit-тесты стора, hydration/persistence и сброс состояния

### 3.3 Admin Pages (где пока мало сценарных тестов)

- `frontend-admin/src/pages/OrdersPage.tsx`
  - Фильтры, пагинация, drawer details, retry report, refund action
- `frontend-admin/src/pages/PaymentsPage.tsx`
  - Поиск/фильтрация/ошибки API
- `frontend-admin/src/pages/TasksPage.tsx`
  - Перезапуск задач, обработка failed/retried состояний
- `frontend-admin/src/pages/FlagsPage.tsx`
  - Переключение feature flag + rollback сценарий

## 4) P2 (желательно, расширение надежности)

### 4.1 Дополнительные задачи и прогностические фичи

- `app/tasks/monthly_forecast.py`
- `app/tasks/weekly_digest.py`
- `app/tasks/monthly_digest.py`
- `app/tasks/forecast_scheduler.py`
- `app/tasks/annual_progressions.py`
- `app/tasks/addon_generation.py`
  - Планировщик, дедупликация, retry, корректность периодов и timezone-sensitive поведения

### 4.2 SEO / middleware / инфраструктурные контракты

- `app/api/v1/system.py` (дополнительно)
- `app/middleware/security_headers.py`
- `app/api/v1/ops.py`
  - CSP и security headers только где нужно, корректность `robots.txt`/`sitemap.xml`, readiness checks

### 4.3 Сквозные E2E (Playwright)

- User E2E:
  - OAuth login -> заказ -> webhook -> генерация отчета -> просмотр/скачивание
- Admin E2E:
  - Логин админа -> обработка заказа -> retry report -> проверка финального статуса
- Cross-role:
  - Не-админ после OAuth попадает на `AccessDenied`

## 5) Матрица типов тестов (чтобы не перекосить покрытие)

- Unit:
  - Чистая логика сервисов, stores, utils
- Integration:
  - API + БД + fakeredis + мок внешних интеграций
- Contract:
  - Форматы ответов API, webhook payload contracts
- E2E:
  - Критические пользовательские флоу и админские операции

## 6) План внедрения в CI

1. Добавить отчеты покрытия для backend/frontend/admin в CI.
2. Включить пороги как `warning` на первую итерацию, потом перевести в `fail`.
3. Зафиксировать набор обязательных E2E smoke.
4. Ввести правило: изменения в `app/services/payment.py`, `app/services/refund.py`, `app/api/v1/webhooks.py` без тестов не мержить.

## 7) Шаблон задачи на каждый новый тест

- Модуль: `<path>`
- Риск: `money/access/data-loss/ux`
- Сценарий: `happy/negative/race/retry`
- Что мокается: `<external deps>`
- Инварианты: `<что обязательно не должно ломаться>`
- Критерий готовности: `тест стабилен, детерминирован, проходит локально и в CI`
