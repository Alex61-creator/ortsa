# URL для регистрации внешних сервисов (прод)

Последняя верификация: `2026-04-15`

Заполните после выбора **боевого домена** и HTTPS. Значения подставляются в `.env` (не коммитить).

| Сервис | Куда вставить | Пример шаблона |
|--------|----------------|----------------|
| **Публичный сайт / SPA** | `PUBLIC_APP_URL`, `SITE_URL`, `YOOKASSA_RETURN_URL` | `https://ВАШ-ДОМЕН` |
| **ЮKassa — return URL** (успех оплаты) | ЛК ЮKassa → настройки магазина | Должен **точно совпадать** с `YOOKASSA_RETURN_URL` в `.env` (см. `.env.example`; путь на фронте должен существовать в роутере) |
| **ЮKassa — HTTP-уведомления (вебхук)** | ЛК ЮKassa | `https://ВАШ-ДОМЕН/api/v1/webhooks/yookassa` |
| **Google OAuth — redirect (сайт)** | Google Cloud Console → OAuth | `https://ВАШ-ДОМЕН/api/v1/auth/google/callback` |
| **Google OAuth — redirect (админка)** | Google Cloud Console → OAuth | `https://ВАШ-ДОМЕН/api/v1/auth/google/callback-admin` |
| **Яндекс OAuth — redirect** | Яндекс OAuth → Redirect URI | `https://ВАШ-ДОМЕН/api/v1/auth/yandex/callback` (в консоли — **точное** совпадение со схемой и путём) |
| **Админ-SPA** | `ADMIN_APP_ORIGIN`, CORS | `https://admin.ВАШ-ДОМЕН` (рекомендуемый вариант; шаблоны `Caddyfile` и `deploy/Caddyfile.prod.example` уже включают `admin.<домен>`, `X-Robots-Tag: noindex` и `robots.txt` с `Disallow: /`) |
| **Telegram Mini App** | BotFather → Web App URL | **`https://ВАШ-ДОМЕН/`** (корень React SPA); авторизация через `POST /api/v1/auth/twa` по `initData`. |

**Почта ([Unisender](https://www.unisender.com/)):** SMTP-параметры и DKIM задаются в кабинете Unisender; в DNS домена отправки — записи SPF/DKIM/DMARC по инструкции провайдера (см. `PRODUCTION_READINESS_AND_GROWTH_PLAN.md`).

**Проверка после деплоя:** HTTP→HTTPS, `GET /health`, `GET /health/ready`, тестовый платёж ЮKassa → вебхук → письмо с отчётом → ссылка в письме открывает `/reports/:id`.

Чеклист sec-doc-only по TLS/секретам/callbacks/backup-restore:
- проверить, что `YOOKASSA_RETURN_URL` и webhook endpoint настроены на `https://` и совпадают с тем, что указано в `.env` и `DEPLOY_URLS.md`;
- проверить, что включены `YOOKASSA_WEBHOOK_VERIFY_IP` и `YOOKASSA_WEBHOOK_VERIFY_API` и что обработчик webhooks отклоняет неверный IP/подпись (см. `tests/test_webhooks.py`);
- выполнить DR drill “dump -> restore в staging” по `DB_MIGRATION_AND_RESTORE_RUNBOOK.md` и зафиксировать результат.

### OAuth: почему должен быть `https://`, а не `http://`

- **Google:** для публичных клиентов в проде разрешённые redirect URI обычно задаются как **HTTPS**; для локальной разработки допускается `http://localhost` (см. [Using OAuth 2.0 for Web Server Applications](https://developers.google.com/identity/protocols/oauth2/web-server#urivalidation)).
- **Яндекс:** в настройках приложения указывается полный Callback URL; для боевого сайта это **HTTPS** на вашем домене ([документация Яндекс OAuth](https://yandex.ru/dev/id/doc/ru/codes/code-url)).
- **Как формируется URL в приложении:** `redirect_uri` для Google / Яндекс / Apple собирается как **`PUBLIC_APP_URL`** (без завершающего `/`) + путь `/api/v1/auth/.../callback` (см. `app/api/v1/auth.py`). Задайте **`PUBLIC_APP_URL=https://ваш-домен`** в `.env` на проде — тогда в запросе к провайдеру всегда будет **`https://`**, независимо от того, видит ли Uvicorn прокси как `http`. Дополнительно для корректных ссылок в письмах и вебхуков по-прежнему полезны **`FORWARDED_ALLOW_IPS`** и заголовки Caddy.
