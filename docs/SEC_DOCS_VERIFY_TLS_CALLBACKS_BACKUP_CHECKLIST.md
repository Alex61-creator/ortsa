# Sec-Docs Verification Checklist (TLS / Secrets / Callbacks / Backup-restore)

## Scope (sec-doc-only)
- Это runbook/doc-only проверка после деплоя.
- Авто-проверки: используются существующие unit/integration тесты в `tests/test_webhooks.py` (IP allowlist, `YOOKASSA_WEBHOOK_VERIFY_API` mismatch/ok, lifecycle dedupe).
- Не добавляем отдельный код для backup-restore/TLS — только фиксацию порядка действий и критериев done.

## 1) TLS / HTTPS
1. Убедиться, что боевой домен (PUBLIC_APP_URL / ADMIN_APP_ORIGIN / API base) отдает **HTTPS** (без 30x циклов).
2. Убедиться, что reverse-proxy (Caddy/Nginx) корректно проксирует TLS-терминацию на `uvicorn/gunicorn` без потери `X-Forwarded-*` (важно для корректного IP, если используется allowlist).

## 2) Секреты и окружение
1. Проверить, что в `.env` на prod заполнены:
   - `YOOKASSA_WEBHOOK_VERIFY_API` (shared secret для body verification),
   - `YOOKASSA_WEBHOOK_VERIFY_IP` (allowlist IP).
2. Проверить, что `SECRET_KEY` и JWT параметры корректны (для доступности ручных эндпоинтов `/health`, admin).

## 3) ЮKassa callbacks и возврат
1. Убедиться, что `YOOKASSA_RETURN_URL` **точно совпадает** с `YOOKASSA` return URL в кабинете магазина (включая протокол `https://` и путь на фронте).
2. Убедиться, что вебхук для ЮKassa настроен на:
   - `https://<ВАШ-ДОМЕН>/api/v1/webhooks/yookassa`
3. Проверить, что приложение корректно отвечает на вебхук:
   - корректный webhook -> 200 и запуск обработчика,
   - неверный IP -> rejection (см. текущую реализацию allowlist),
   - mismatch `YOOKASSA_WEBHOOK_VERIFY_API` -> 400.

## 4) Webhook dedupe (анти-дубликаты)
1. Проверить соответствие lifecycle:
   - обработка помечается как `processing`,
   - после успеха фиксируется `processed`,
   - при ошибке фиксируется `failed` на короткий TTL.
2. Убедиться, что логика не допускает повторной обработки одного и того же `webhook:{event}:{object_id}`.

## 5) Backup / Restore drill (DR)
1. Найти актуальный runbook: `DB_MIGRATION_AND_RESTORE_RUNBOOK.md`.
2. Выполнить процедуру “dump -> restore в staging” по runbook.
3. Criteria done:
   - restore staging поднялся,
   - доступны ключевые таблицы (`users`, `orders`, `reports`, `subscriptions`),
   - тестовый `/health/ready` проходит.

## Output (что считать завершенным)
- В проектном трекере (или в PR description) зафиксировать:
  - дату/время деплоя,
  - подтверждение выполнения checklist,
  - ссылки на тестовый webhook сценарий и результат restore drill.

