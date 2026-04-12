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

Это выполнит сборку и скопирует `dist` в `../frontend-dist`. Caddy отдаёт статику с `try_files` и проксирует `/api/*` на FastAPI (см. `Caddyfile` в корне).

В **production** задайте `VITE_API_URL=/api/v1` (относительный путь к тому же origin), чтобы запросы шли на прокси Caddy.

## Переменные окружения

См. `.env.example`. Важно:

- **`VITE_API_URL`** — база API (`/api/v1` в prod на том же домене).
- **`YOOKASSA_RETURN_URL`** на бэкенде должен указывать на **origin фронтенда** (тот же URL используется для OAuth callback: `/auth/callback?token=...`).

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
