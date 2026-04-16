# Project Master Operating Document

Версия: `v1.0`  
Дата: `2026-04-16`  
Статус: `Active / Master Source`

---

## 0. Назначение документа

Этот документ — единый операционный контур проекта.  
Он объединяет в одну логическую систему:

- текущий продуктовый и технический runtime;
- go-live критерии и production readiness;
- стратегию развития на 3-5 лет;
- миграцию астрологического ядра на `kerykeion` v5;
- запуск новых тарифов и add-on допродаж;
- состояние админки, feature gaps и remove candidates;
- UI/brand стандарты и deployment-интеграции;
- документационный backlog.

Цель: дать один понятный и полный взгляд на проект в формате:
- что уже сделано;
- что нужно сделать;
- как это сделать;
- к чему это приведет;
- как контролировать прогресс чекбоксами.

---

## 1. Источники и принцип консолидации

Master-документ основан на:

- `PRODUCT_FLOW_AND_BUSINESS_LOGIC.md`
- `PRODUCTION_READINESS_AND_GROWTH_PLAN.md`
- `PRODUCT_AND_ECONOMICS_STRATEGY_3_5_YEARS.md`
- `KERYKEION_V5_MIGRATION_PLAN.md`
- `ADMIN_PANEL_FUTURE.md`
- `FEATURE_GAPS_AND_DELETE_CANDIDATES.md`
- `DOCUMENTATION_BACKLOG_PLAN.md`
- `BRAND_BOOK_AND_UI_SYSTEM_ANTD_V5.md`
- `DEPLOY_URLS.md`

Принцип: не терять смысл и детализацию исходных документов, а выстроить их в единую управленческую и техническую логику.

---

## 2. Текущее состояние проекта (As-Is)

### 2.1 Стадия

Проект находится на стадии: **late MVP / pre-production hardening**.

### 2.2 Что уже реализовано

- [x] Пользовательская воронка `auth -> order -> payment -> report -> delivery`.
- [x] Async pipeline (Celery) для генерации отчетов.
- [x] Платежный контур и webhook.
- [x] Базовые health/readiness проверки.
- [x] Рабочие контуры натальных отчетов и синастрии на `kerykeion` v4.
- [x] Базовая админка для операционной поддержки (users, payments, health, logs, promos, flags).

### 2.3 Ключевые сущности

- `User`
- `NatalData`
- `Tariff`
- `Order`
- `Report`

Базовый поток статусов заказа:

`PENDING -> PAID -> PROCESSING -> COMPLETED/FAILED`

---

## 3. Целевая модель (To-Be)

### 3.1 Продуктовая цель

Переход от модели единичной покупки к модели:

- repeat revenue (повторные покупки);
- подписка;
- продуктовая лестница `Tripwire -> Core -> Upsell -> Subscription -> Premium`.

### 3.2 Техническая цель

Переход от legacy-интеграции `kerykeion` v4 к factory-подходу v5:

- `AstrologicalSubjectFactory`
- `ChartDataFactory`
- `ChartDrawer`
- `AspectsFactory`

### 3.3 Бизнес-цель

Рост по ключевым метрикам:

- `CR1` (Signup -> First Purchase),
- `AOV`,
- attach-rate add-on,
- retention (M1/M3/M6),
- `LTV/CAC`,
- contribution margin.

---

## 4. Единый чеклист: сделано / нужно сделать

## 4.1 Go-Live Gate (обязательно)

- [x] Исправлен `report_generation` + подтвержден e2e.
- [x] Исправлен webhook dedupe flow (lock + marker).
- [x] Введена идемпотентность `POST /orders` (через `Idempotency-Key`, запись в `order_idempotency` + strict `409` при повторе с другим payload + recovery протухшего `processing` lock).
- [x] Настроены базовые алерты по SLO/SLI.
- [x] Пройден smoke: auth -> order -> payment -> email -> report download.
- [x] Проверены секреты, TLS, callbacks, backup/restore (sec-doc-only: чеклист после деплоя + опора на существующие unit-тесты в `tests/test_webhooks.py`).

**Ожидаемый эффект:** предсказуемый прод-запуск без репутационных инцидентов на первых платящих пользователях.

## 4.2 Миграция на `kerykeion` v5

- [x] Обновлена зависимость до v5.
- [x] Заменены legacy API-классы на v5 factories.
- [x] Переведен `app/services/astrology.py` на новую архитектуру.
- [x] Выровнены контракты данных для PDF и LLM.
- [x] Пройден regression pack (golden PNG/SVG/PDF + Celery smoke).

**Ожидаемый эффект:** снижение техдолга, лучшая поддерживаемость, база для новых продуктов.

## 4.3 Новые тарифы и допродажи

- [ ] Добавлены `tariff.code`: `transit_month_pack`, `compatibility_deep_dive`, `return_pack`.
- [ ] Введена связка add-on с базовым заказом (`parent_order_id` или `order_addons`).
- [ ] Добавлены API ` /api/v1/addons/*`.
- [ ] Добавлены Celery задачи генерации add-on отчетов.
- [ ] Добавлены точки офферинга в UI + email/push.
- [ ] Настроены KPI и A/B тесты цен/офферов.

**Ожидаемый эффект:** рост AOV, повторной выручки и LTV.

## 4.4 Админка до production-ready

- [ ] Подключен контур prompts (router + routes + menu + smoke).
- [ ] Промокоды перенесены из cache в БД.
- [ ] Feature flags переведены в персистентную модель с аудитом.
- [ ] Воронка переведена на event-based аналитику (не эвристики).
- [ ] `/admin/tasks` подключен к live Celery состоянию.
- [ ] Углублены платежные фильтры и action-log.

**Ожидаемый эффект:** админка становится полноценным инструментом управляемого роста, а не только операционной панели.

## 4.5 Feature gaps и очистка

- [ ] Доведена prompts-фича до runtime.
- [ ] Решение по `app/tasks/scheduler.py` (удалить/оставить).
- [ ] Решение по `app/utils/landing_html.py` + связанным тестам.
- [ ] Решение по `HTML макеты/` (оставить/архивировать/удалить).
- [ ] Решение по legacy static `frontend/public/static/*`.
- [ ] Решение по roadmap-спекам в `app/` vs `docs/roadmap/`.

**Ожидаемый эффект:** снижение шума в кодовой базе и упрощение поддержки.

## 4.6 Документация и процесс

- [ ] `INCIDENT_RESPONSE_RUNBOOK.md`
- [ ] `RELEASE_AND_ROLLBACK.md`
- [ ] `TEST_STRATEGY.md`
- [ ] `ANALYTICS_EVENT_SCHEMA.md`
- [ ] `docs/adr/*`
- [ ] `SLO_SLI_ALERTBOOK.md`
- [ ] `SECURITY_BASELINE.md`
- [ ] `DB_MIGRATION_AND_RESTORE_RUNBOOK.md`
- [ ] `API_CHANGE_POLICY.md`
- [ ] `DELIVERY_STANDARDS.md`

**Ожидаемый эффект:** снижение операционных рисков и устойчивый delivery cadence.

---

## 5. Как внедрять элементы: единый формат

Для каждого элемента (фича/миграция/процесс) использовать одну карточку:

- [ ] **Элемент**
- [ ] **Что уже сделано**
- [ ] **Что нужно сделать**
- [ ] **Шаги внедрения**
- [ ] **Риски и mitigation**
- [ ] **Где показывается пользователю (если продуктовая фича)**
- [ ] **На каком этапе воронки активируется**
- [ ] **К чему приведет (метрики/экономика/качество)**
- [ ] **Владелец**
- [ ] **Срок**

---

## 6. Подробная структура внедрения новых add-on тарифов

## 6.1 Transit Month Pack

### Что это

30-дневный прогноз поверх базового natal-отчета.

### Для чего

Первый мост от разовой покупки к регулярному потреблению и подписке.

### Где и когда предлагать

- сразу после просмотра базового отчета;
- повторно через 3-7 дней в email/push;
- блок в `dashboard/reports` "Продолжить прогноз".

### Как внедрить

- добавить `tariff.code = transit_month_pack`;
- разрешать покупку только при `COMPLETED` базовом natal-заказе;
- запускать отдельную Celery-задачу генерации;
- выдавать отчет через текущий канал (dashboard + email).

### Рекомендуемая цена

`590 RUB` (tripwire, высокий attach-rate).

### К чему приведет

- рост attach-rate add-on,
- рост повторной выручки,
- подготовка к auto-renew модели.

## 6.2 Compatibility Deep Dive

### Что это

Расширенный парный пакет: score + composite + углубленная синастрия.

### Где предлагать

- после завершения синастрии;
- в карточке парного отчета;
- в триггерной цепочке post-report.

### Как внедрить

- `tariff.code = compatibility_deep_dive`;
- доступ только при `COMPLETED` синастрии;
- reuse текущего payment/webhook pipeline;
- отдельный генератор отчета.

### Рекомендуемая цена

`1,490 RUB`.

### К чему приведет

- рост среднего чека в relationship-сценарии,
- увеличение глубины продуктовой линейки.

## 6.3 Return Pack

### Что это

`Solar return` + 3 последовательных `Lunar return` отчета.

### Механика взаимодействия

- основной оффер через 24-72 часа после прочтения natal;
- pre-birthday оффер за 7 дней до дня рождения;
- reactivation оффер через 21-30 дней неактивности.

Каналы:

- in-app баннер/карточка;
- email-цепочка 2-3 касания;
- push/telegram напоминания.

### Как внедрить

- `tariff.code = return_pack`;
- доступ при завершенном базовом natal;
- отдельный планировщик генераций по циклу;
- единая выдача отчетов в личный кабинет.

### Рекомендуемая цена

`1,990 RUB`.

### К чему приведет

- рост retention,
- рост LTV,
- формирование подписочной привычки.

---

## 7. Как не нарушить основную логику при добавлении add-on

### Принципы совместимости

- базовый заказ не меняет свой lifecycle;
- add-on — отдельный, но связанный заказ;
- reuse текущих платежей, webhook, storage, email delivery.

### Техническая модель

- связка add-on с базовым: `parent_order_id` или `order_addons`;
- запрет дублей add-on на один базовый заказ (по правилам);
- ownership-check: только владелец базового заказа.

### Продуктовая модель

- офферы только по релевантным триггерам;
- ограничение окна оффера (например, 72 часа) там, где нужно;
- прозрачная ценность: "что получу, когда и зачем".

---

## 8. UI/Brand и каналная консистентность

Все новые модули и тарифные экраны обязаны соответствовать:

- `BRAND_BOOK_AND_UI_SYSTEM_ANTD_V5.md`;
- обязательным UX-состояниям (`loading/empty/error/success`);
- mobile-first и accessibility (`WCAG 2.1 AA`);
- единым паттернам CTA и микрокопирайтинга.

Ожидаемый эффект: выше доверие и конверсия за счет целостного опыта.

---

## 9. Deployment и внешние интеграции

Для новых тарифов/add-on использовать текущий боевой интеграционный контур:

- платежи и callback в ЮKassa;
- OAuth callback URL;
- TMA URL;
- health/readiness;
- корректные публичные ссылки в письмах.

Источник параметров: `DEPLOY_URLS.md`.

---

## 10. Метрики управления (обязательные)

### Продукт и монетизация

- `CR1`
- `AOV`
- add-on attach-rate
- repeat purchase rate
- subscription share
- retention D30/M1/M3

### Операционка

- webhook success rate
- paid->completed p95/p99
- celery queue length
- orders.failed %
- email dispatch latency

### Экономика

- contribution margin
- CAC payback
- LTV/CAC
- cost per order (LLM + infra + commissions)

---

## 11. Каденс управления

- **Еженедельно:** воронка, инциденты, эксперименты, stop/go.
- **Ежемесячно:** P&L, unit economics, пересмотр офферов/цен.
- **Ежеквартально:** апдейт roadmap и перераспределение ресурсов.

---

## 12. Master Backlog (универсальный шаблон чекбоксов)

Использовать для любого блока работ:

- [ ] Название инициативы
- [ ] Owner
- [ ] Deadline
- [ ] Done definition
- [ ] Что уже реализовано
- [ ] Что блокирует
- [ ] План внедрения (этапы)
- [ ] Риски/mitigation
- [ ] KPI результата
- [ ] Статус ревью (Product/Tech/Ops)

---

## 13. Финальная логика принятия решений

Порядок приоритизации в проекте:

1. Надежность ядра и go-live criteria.
2. Наблюдаемость и контроль экономики.
3. Рост конверсии и среднего чека.
4. Retention и повторная выручка.
5. Масштабирование каналов и продуктовой линейки.

Правило: не запускать крупные новые инициативы без ясного влияния на метрики `CR`, `AOV`, `Retention`, `Cost per order`, `LTV/CAC`.

---

## 14. Связанные документы

- `PRODUCT_FLOW_AND_BUSINESS_LOGIC.md`
- `PRODUCTION_READINESS_AND_GROWTH_PLAN.md`
- `PRODUCT_AND_ECONOMICS_STRATEGY_3_5_YEARS.md`
- `KERYKEION_V5_MIGRATION_PLAN.md`
- `ADMIN_PANEL_FUTURE.md`
- `FEATURE_GAPS_AND_DELETE_CANDIDATES.md`
- `DOCUMENTATION_BACKLOG_PLAN.md`
- `BRAND_BOOK_AND_UI_SYSTEM_ANTD_V5.md`
- `DEPLOY_URLS.md`
