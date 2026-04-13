#!/usr/bin/env bash
# Проверка целостности custom-format дампа: pg_restore -l (список объектов).
# Стек с postgres должен быть запущен (нужен бинарник pg_restore той же major-версии в контейнере).
#
#   ./scripts/verify_pg_backup.sh backups/astro_pg_20260101_030000.dump.gz
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT/docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-$ROOT/.env}"
DUMP="${1:?usage: $0 path/to/astro_pg_*.dump.gz}"

cd "$ROOT"
gunzip -c "$DUMP" | docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -iT postgres \
  pg_restore -l - >/dev/null
echo "OK: pg_restore -l succeeded for $DUMP"
