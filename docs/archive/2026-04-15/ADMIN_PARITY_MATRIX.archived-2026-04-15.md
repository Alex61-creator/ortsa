# Матрица паритета админки (референс v2 -> реализация)

Источник референса: `HTML макеты/astrogen-admin-v2.html`.

Статусы:
- `implemented` - есть в `frontend-admin` и поддержано API.
- `frontend_gap` - API есть/частично есть, но экран/UX не соответствует.
- `backend_gap` - экран есть/планируется, но API не хватает.
- `full_gap` - отсутствуют и экран, и API.

| Reference block | Frontend screen | Backend endpoint | Status | Notes |
|---|---|---|---|---|
| Login (Google/Yandex, notice) | `LoginPage` | `GET /api/v1/auth/google/authorize-admin` | frontend_gap | Yandex кнопка disabled, визуал частично отличается |
| Shell (sidebar/topbar/theme/csv) | `AdminLayout` | n/a | frontend_gap | Меню/тема есть, CSV пока не реализован |
| Dashboard metrics | `DashboardPage` | `GET /api/v1/admin/dashboard/summary` | frontend_gap | Сетка есть, но часть блоков аналитики упрощена |
| Funnel panel | `FunnelPage` | `GET /api/v1/admin/funnel/summary` | frontend_gap | Базовая воронка без расширенных рекомендаций/фильтров |
| Users table/chips/sort | `UsersPage` | `GET /api/v1/admin/users/` | frontend_gap | Референсные chips/сортировки закрыты не полностью |
| User drawer tabs | `UsersPage` Drawer | `/api/v1/admin/support/*` | frontend_gap | Вкладки есть, часть как информационные placeholder |
| Payments panel | `PaymentsPage` | `GET /api/v1/admin/payments/` | frontend_gap | Функции есть, но таблица/действия проще референса |
| Orders panel + actions | `OrdersPage` | `GET /api/v1/admin/orders/*`, refund/retry | frontend_gap | Основные действия есть, но UX/детализация не 1:1 |
| Tariffs management + history | `TariffsPage` | `GET/PATCH /api/v1/admin/tariffs/*`, history | frontend_gap | История добавлена, нет полного UX edit-row из макета |
| Celery tasks | `TasksPage` | `GET /api/v1/admin/tasks/` | frontend_gap | Статусная панель есть, нет расширенных фильтров/операций |
| Promocodes | `PromosPage` | `/api/v1/admin/promos/*` | frontend_gap | CRUD-lite есть, не хватает полного набора полей/валидаторов |
| Feature flags | `FlagsPage` | `/api/v1/admin/flags/*` | frontend_gap | Toggle есть, нет add/edit/delete lifecycle |
| Health monitoring panel | `HealthPage` | `/api/v1/admin/health/` | frontend_gap | Карточки есть, нет блока последних ошибок/инцидентов |
| Action log panel | `ActionLogPage` | `/api/v1/admin/logs/` | frontend_gap | Базовый список+поиск, без типовых фильтров/меток |

## Definition of Done (модульный)

- UI соответствует референсу по структуре, ключевым отступам/типографике/состояниям.
- Все действия модуля имеют API-контракт и обработку ошибок.
- Есть минимальное покрытие: backend contract tests + frontend unit/integration + e2e smoke path.

## Baseline defects for 99% cycle

- P1: topbar CSV не реализован (кнопка с placeholder behavior).
- P1: несколько вкладок User Drawer не имеют полноценных операций.
- P1: e2e покрытие ограничено smoke-сценарием.
- P2: визуал таблиц/фильтров/chips не полностью совпадает с референсом.
- P2: в Funnel/Tasks/Health/Log отсутствуют расширенные элементы референсных экранов.
