# Admin v2 Parity Checklist (99%)

Источник: `HTML макеты/astrogen-admin-v2.html`.

## Текущая реализация (baseline)

| Секция | Текущее состояние | Статус |
|---|---|---|
| Auth | Google OAuth, admin guard, logout | implemented |
| Shell | Sidebar/topbar/theme/csv, но без расширенных бейджей и unified states | partial |
| Dashboard | Есть operational блоки, analytics как заглушка | gap |
| Funnel | Базовые шаги/конверсии без детального drop-off и рекомендаций | partial |
| Users | Таблица + drawer tabs, но часть tabs/filters упрощены | partial |
| Payments | Поиск/статус/таблица, ограниченные действия | partial |
| Orders | Фильтры, drawer, retry/refund/download | implemented |
| Tasks | Базовый список без KPI/фильтров | partial |
| Tariffs | Редактирование + history, без inline UX parity | partial |
| Promos | Create + toggle + list, без полного набора полей | partial |
| Feature Flags | List + toggle | implemented |
| Health | Статусы сервисов, без блока последних инцидентов | partial |
| Action Log | Лента + поиск, без фильтра типа и визуальных меток | partial |

## Целевое покрытие 99%

| Секция | Definition of Done |
|---|---|
| Shell/UI system | Единые токены/компоненты, статусы, toasts, empty/error/loading states, parity в light/dark |
| Dashboard | KPI + analytics cards + графические блоки + system status + ROI/LLM блоки |
| Funnel | Период, шаги, drop-off блок, рекомендации |
| Users + Drawer | Продвинутые фильтры/chips/сортировки, fully interactive tabs, safety confirms |
| Payments/Tasks | Полный toolbar, status badges, действия из таблицы, error states |
| Tariffs/Promos/Flags | UX и поля управления как в макете, история/валидации/статусы |
| Health/Logs | Инциденты/ошибки, фильтры и типы действий, export-ready таблицы |
| API contracts | Единый префикс `/api/v1/admin/*`, согласованные ответы/ошибки |

## Приемочные сценарии

- Вход в админку и переход по всем экранам без визуальных артефактов.
- Все критичные действия (refund/block/delete/toggle/create/edit) имеют confirm + toast.
- На каждом экране есть предсказуемые loading, empty и error состояния.
- Все админ API вызовы идут через единый префикс и корректно обрабатывают 401/4xx/5xx.
