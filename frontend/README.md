# AstroGen — фронтенд

SPA на **React 18**, **Vite**, **TypeScript (strict)**, **React Router v6**, **Zustand**, **TanStack Query v5**, **Axios**, **Ant Design 5**, **Framer Motion**, **React Hook Form + Zod**, **i18next**, **react-helmet-async**. Поддержка **Telegram Mini App** через `@twa-dev/sdk` (и при необходимости расширений из `@telegram-apps/sdk-react`).

## Требования

- Node.js 20+
- Бэкенд FastAPI (см. корень репозитория) с префиксом `/api/v1`

## Установка и запуск

```bash
npm install
cp .env.example .env
npm run dev
```

По умолчанию Vite слушает порт **5173**. В `.env.development` задано `VITE_API_URL=/api/v1` — запросы проксируются на `http://localhost:8000` (см. `vite.config.ts`).

**Маркетинговый лендинг** живёт в репозитории в `static/` и в dev открывается через **FastAPI** (`http://127.0.0.1:8000/`). Это не Vite: на **5173** только SPA (заказ, кабинет). Для ссылок «на сайт» и якоря тарифов в dev задано **`VITE_LANDING_ORIGIN=http://127.0.0.1:8000`** (см. `.env.development`). В production на том же домене переменную можно не задавать — подставится текущий `window.location.origin`.

Добавьте origin фронта в **`BACKEND_CORS_ORIGINS`** бэкенда, например:

`http://localhost:5173`

## Сборка и деплой (Docker / Caddy)

```bash
npm run build
```

Артефакты в каталоге `dist/`. Для compose в корне репозитория используется каталог **`frontend-dist`**:

```bash
npm run build:deploy
```

Это выполнит сборку и скопирует `dist` в `../frontend-dist`. Caddy проксирует `/api/*` на FastAPI, отдаёт SPA с `try_files` **только** на путях приложения (`/order`, `/order/*`, `/dashboard/*`, `/reports/*`, `/auth/callback`, `/cabinet/orders/*`, `/assets/*`); всё остальное (включая **`/`** и `/static/*`) — на FastAPI с HTML-лендингом (см. `Caddyfile` в корне).

В **production** задайте `VITE_API_URL=/api/v1` (относительный путь к тому же origin), чтобы запросы шли на прокси Caddy.

## Переменные окружения

См. `.env.example`. Важно:

- **`VITE_API_URL`** — база API (`/api/v1` в prod на том же домене).
- **`VITE_LANDING_ORIGIN`** — базовый URL HTML-лендинга (в dev обычно `http://127.0.0.1:8000`); в prod при пустом значении используется тот же origin, что и у SPA.
- **`YOOKASSA_RETURN_URL`** на бэкенде должен указывать на **origin фронтенда** (тот же URL используется для OAuth callback: `/auth/callback?token=...`).

**Токены:** лендинг в `static/` сохраняет JWT в **`sessionStorage`** (`astrogen_jwt`), React SPA — в **`localStorage`** (persist Zustand, ключ `astrogen_auth_token`). Сессия при переходе между лендингом и SPA на одном домене может не совпадать до отдельной унификации.

**Telegram Mini App:** в BotFather укажите **Web App URL** `https://ВАШ-ДОМЕН/` — откроется статический лендинг; фоновый вход через `initData` выполняет [`static/js/auth-popup.js`](../static/js/auth-popup.js) (`trySilentTwaLogin`).

## Скрипты

| Команда            | Описание                                      |
| ------------------ | --------------------------------------------- |
| `npm run dev`      | Режим разработки (Vite)                       |
| `npm run build`    | Production-сборка                             |
| `npm run build:deploy` | Сборка + копирование в `../frontend-dist` |
| `npm run preview`  | Превью production-сборки                      |
| `npm run lint`     | ESLint                                        |
| `npm run test`     | Vitest                                        |

## Тесты

```bash
npm run test
```

## Структура `src/`

Соответствует ТЗ: `api/`, `components/`, `features/`, `hooks/`, `layouts/`, `lib/`, `pages/`, `routes/`, `stores/`, `styles/`, `types/`.
