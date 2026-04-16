# Аналитика в админке (указатель)

Дата: `2026-04-16`  
Статус: **чеклист внедрения §5 закрыт** (снимок на 2026-04-16). Полные таблицы метрик (§2–4), интерактивные чекбоксы §5 и раздел «следующие шаги» v1 перенесены в архив как зафиксированная справка по закрытому этапу.

**Архивный снимок v1.0:** [archive/2026-04-16/ADMIN_ANALYTICS_AND_METRICS.v1-reference.archived-2026-04-16.md](archive/2026-04-16/ADMIN_ANALYTICS_AND_METRICS.v1-reference.archived-2026-04-16.md)

---

## Источники истины в коде

- События: `app/models/analytics_event.py`, запись — `app/services/analytics.py`, схема имён — `docs/ANALYTICS_EVENT_SCHEMA.md`.
- Growth / воронка / когорты: `app/services/event_based_metrics.py`, `app/api/v1/admin/metrics.py`, упрощённая воронка — `app/api/v1/admin/funnel.py`.
- Дашборд: `app/api/v1/admin/dashboard.py`, `app/services/order_ops_metrics.py`.
- Серверный CSV: `app/api/v1/admin/export.py`.
- Заказы / платежи / пользователи: `app/api/v1/admin/orders.py`, `payments.py`, `users.py`.
- Промокоды (CRUD): `app/api/v1/admin/promos.py`, UI — `frontend-admin/src/pages/PromosPage.tsx`; агрегаты — `/promo-analytics`.
- Тумблеры отчёта: `orders.report_option_flags`, цены — `app_settings` (`app/services/report_option_pricing.py`); UI — `/report-options`.

Экспорт CSV: шапка админки (`frontend-admin/src/layouts/AdminLayout.tsx`), `frontend-admin/src/utils/exportTableCsv.ts`; сервер — `GET /api/v1/admin/export/*.csv`.

---

## Актуальные ограничения (вне закрытого чеклиста)

- **Active subscriptions over time:** без отдельной таблицы исторических снимков — только текущий active и месячные ряды по новым/выручке; детали в архиве §4.2.
- **Единый Pro-dashboard** в админке не делался; глубина по пользователю — через экраны пользователей и `/subscriptions`.
- **`/funnel`:** упрощённые шаги относительно event-based воронки в `/admin/metrics/funnel`.

---

## Связанные документы

- `ANALYTICS_EVENT_SCHEMA.md`
- `PROJECT_MASTER_OPERATING_DOCUMENT.md`
- `ADMIN_PANEL_FUTURE.md`
