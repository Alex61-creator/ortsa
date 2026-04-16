# Production Readiness and Growth Plan

Версия: `v1.1`  
Дата обновления: `2026-04-16`

Документ объединяет ранее раздельные материалы:

- `PRODUCTION_IMPLEMENTATION.md`
- `SCALABILITY_READINESS_REVIEW.md`
- `PROD_GAP_CLOSURE_AND_POST_LAUNCH_2_3_MONTH_PLAN.md`

Цель: единый источник для go-live решения, закрытия блокеров и плана на первые 2-3 месяца после запуска.

---

## 1. Текущая стадия

Стадия проекта: **late MVP / production hardening**.

Рабочий контур есть (auth -> order -> payment -> report -> delivery), критические разрывы по `report_generation` и webhook dedupe закрыты.

Статус по последнему hardening-циклу:
- `report_generation`: исправлен основной цикл и guard-checks, single/bundle стабилизированы.
- webhook dedupe: реализован lifecycle `processing -> processed/failed`, устранен риск "залипания".
- observability: в ops-метрики добавлены `paid->completed` latency p50/p95.
- тесты: полный прогон `pytest` проходит зелёным.

---

## 2. Go-Live Gate (обязательные условия)

Прод-запуск разрешен только при выполнении всех пунктов:

1. Исправлен `report_generation` + есть e2e-тест `paid -> webhook -> completed -> email sent`.
2. Исправлен webhook dedupe flow (processing lock + processed marker).
3. Введена идемпотентность `POST /orders` (или эквивалентная защита от дублей).
4. Включены базовые алерты (`/health/ready`, queue length, fail-rate, paid->completed latency).
5. Пройден smoke-сценарий на окружении запуска:
   - auth -> order -> payment -> email -> report download.
6. Настроены секреты, TLS, OAuth/ЮKassa callbacks и базовые backup/restore проверки.

Чеклист sec-doc-only после деплоя (и опора на существующие unit-тесты):
- `YOOKASSA_RETURN_URL` и endpoint вебхука настроены на `https://` и точно совпадают с тем, что указано в `DEPLOY_URLS.md`.
- включены/проверены `YOOKASSA_WEBHOOK_VERIFY_IP` (allowlist IP) и `YOOKASSA_WEBHOOK_VERIFY_API` (shared secret для webhook body).
- проверить, что вебхук отклоняет неверный IP/несовпадающий `api` (ожидается `400`) и что корректный запрос вызывает обработку (см. `tests/test_webhooks.py`).
- проверить идемпотентность webhook: один и тот же `webhook:{event}:{object_id}` обрабатывается ровно один раз (см. `tests/test_webhooks.py`).
- выполнить backup/restore drill по `DB_MIGRATION_AND_RESTORE_RUNBOOK.md` (dump + restore в staging) и зафиксировать успешное прохождение.

Контракт по `POST /orders` идемпотентности (production baseline):
- один и тот же `Idempotency-Key` + тот же payload -> возвращается тот же `order/payment` результат без повторного вызова YooKassa;
- один и тот же `Idempotency-Key` + другой payload -> `409 Conflict`;
- при активном `processing` lock -> `409 Conflict`;
- при протухшем `processing` lock (timeout) -> lock reclaim и повторная обработка запроса.
- для legacy-строк idempotency с пустым fingerprint strict payload-check ослаблен (совместимость), и это должно логироваться отдельным warning-сигналом.
- при успешном reclaim протухшего `processing` lock должен писаться отдельный structured log `Idempotency stale processing lock reclaimed` для ops-наблюдаемости.

---

## 3. Приоритеты до production

## P0 — блокеры

- Довести админ-контур prompts (backend router + routes/menu + smoke-test).
- Проверить канонические user links в письмах (`/reports/{id}`).

## P1 — операционная устойчивость

- Idempotency для создания заказа.
- Минимальный observability-контур: SLO и alerting policy.
- Проверенный release-runbook и регулярный DR drill.

## P2 — production hardening

- Разделение очередей Celery (`heavy`/`io`) — внедрено, в эксплуатации.
- Outbox pattern для email.
- Guardrails для LLM (circuit breaker + quota/budget controls).

### 3.1 Операционные команды Celery (текущий baseline)

- `heavy`: `celery -A app.tasks.worker.celery_app worker -Q heavy -n heavy@%h --concurrency=2`
- `io`: `celery -A app.tasks.worker.celery_app worker -Q io -n io@%h --concurrency=4`
- `default`: `celery -A app.tasks.worker.celery_app worker -Q default -n default@%h --concurrency=2`
- `beat`: отдельным процессом.

---

## 4. Целевые SLO на этапе 1000–2000 пользователей/месяц

- `Order create p95 < 700ms`
- `Webhook processing success > 99.9%`
- `Paid -> report completed p95 < 10 min`, `p99 < 20 min`
- `Email dispatch after completion p95 < 2 min`

Минимальные алерты:

- `celery_queue_length > 20` более 10 минут;
- `orders.failed > 3%` за час;
- `paid -> completed p95 > 20 min`;
- `webhook 4xx/5xx > 2%` за 15 минут.

---

## 5. Инфраструктурный baseline

Для текущего диапазона нагрузки (1000–2000 users/month):

- VPS: `4 vCPU / 8 GB RAM / NVMe 120+ GB`;
- `fastapi`: минимум 2 workers (или 2 реплики);
- `celery-worker`: стартово 3-4 concurrency (после проверки RAM/CPU);
- ежедневные backup БД + storage, минимум 1 restore drill в квартал.

---

## 6. План на первые 2-3 месяца после запуска

Условие входа в этап: появились первые платящие клиенты, выручка покрывает инфраструктуру и LLM генерацию.

## 6.1. Экономика и управление

- Еженедельно: funnel + инциденты + decisions.
- Ежемесячно: P&L, CAC, payback, contribution margin, LTV/CAC.
- Решения по фичам и каналам только через влияние на `CR`, `AOV`, `Retention`, `Cost per order`.

## 6.2. Продукт

- Минимальная продуктовая лестница: tripwire -> core -> upsell -> возврат пользователя.
- A/B гипотезы по onboarding, paywall, офферам и CTA (2-4/месяц).
- Усиление perceived value отчета: actionable формат + объяснимость выводов.

## 6.3. Техническая устойчивость

- Разделение Celery нагрузок и scale-runbook.
- Outbox email и статусы доставки.
- LLM fallback/guardrails для деградаций провайдера.

---

## 7. Что не делать на раннем post-launch этапе

- Не запускать много фич без аналитики эффекта.
- Не масштабировать paid channels без предсказуемого payback.
- Не уходить в крупные рефакторы до стабилизации метрик и SLA.

---

## 8. Связанные документы

- Стратегия продукта и экономики: [`PRODUCT_AND_ECONOMICS_STRATEGY_3_5_YEARS.md`](./PRODUCT_AND_ECONOMICS_STRATEGY_3_5_YEARS.md)
- Техдолг и remove-candidates: [`FEATURE_GAPS_AND_DELETE_CANDIDATES.md`](./FEATURE_GAPS_AND_DELETE_CANDIDATES.md)
- URL интеграций (ЮKassa/OAuth/Telegram): [`DEPLOY_URLS.md`](./DEPLOY_URLS.md)
- Архив объединенных документов: `docs/archive/2026-04-15/`
