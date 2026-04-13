# URL для регистрации внешних сервисов (прод)

Заполните после выбора **боевого домена** и HTTPS. Значения подставляются в `.env` (не коммитить).

| Сервис | Куда вставить | Пример шаблона |
|--------|----------------|----------------|
| **Публичный сайт / SPA** | `PUBLIC_APP_URL`, `SITE_URL`, `YOOKASSA_RETURN_URL` | `https://ВАШ-ДОМЕН` |
| **ЮKassa — return URL** (успех оплаты) | ЛК ЮKassa → настройки магазина | Должен **точно совпадать** с `YOOKASSA_RETURN_URL` в `.env` (см. `.env.example`; путь на фронте должен существовать в роутере) |
| **ЮKassa — HTTP-уведомления (вебхук)** | ЛК ЮKassa | `https://ВАШ-ДОМЕН/api/v1/webhooks/yookassa` |
| **Google OAuth — redirect (сайт)** | Google Cloud Console → OAuth | `https://ВАШ-ДОМЕН/api/v1/auth/google/callback` |
| **Google OAuth — redirect (админка)** | Google Cloud Console → OAuth | `https://ВАШ-ДОМЕН/api/v1/auth/google/callback-admin` |
| **Админ-SPA** | `ADMIN_APP_ORIGIN`, CORS | `https://admin.ВАШ-ДОМЕН` (если выносите админку на поддомен) |
| **Telegram Mini App** | BotFather → Web App URL | **`https://ВАШ-ДОМЕН/`** (корень сайта) — открывается HTML-лендинг из `static/`; тихий вход через `POST /api/v1/auth/twa` по `initData` (см. `static/js/auth-popup.js`). Если указать только путь SPA без лендинга на `/`, пользователь не увидит маркетинговую главную при старте из бота. |

**Почта ([Unisender](https://www.unisender.com/)):** SMTP-параметры и DKIM задаются в кабинете Unisender; в DNS домена отправки — записи SPF/DKIM/DMARC по инструкции провайдера (см. `PRODUCTION_IMPLEMENTATION.md` §2.3.1).

**Проверка после деплоя:** HTTP→HTTPS, `GET /health`, `GET /health/ready`, тестовый платёж ЮKassa → вебхук → письмо с отчётом → ссылка в письме открывает `/reports/:id`.
