#!/usr/bin/env bash
# Архив тома storage (PDF/PNG отчётов) через одноразовый контейнер fastapi с тем же томом.
# Требуется запущенный образ и volume astro_storage (после первого up).
#
# Переменные: COMPOSE_FILE, ENV_FILE, BACKUP_ROOT — как в backup_postgres.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT/docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-$ROOT/.env}"
BACKUP_ROOT="${BACKUP_ROOT:-$ROOT/backups}"
mkdir -p "$BACKUP_ROOT"

TS="$(date +%Y%m%d_%H%M%S)"
NAME="astro_storage_${TS}.tar.gz"
OUT="$BACKUP_ROOT/$NAME"

cd "$ROOT"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" run --rm --no-deps \
  -v "$BACKUP_ROOT:/backup" \
  -e "ARC_NAME=$NAME" \
  fastapi sh -c 'tar czf "/backup/${ARC_NAME}" -C /app/storage .'

echo "OK: $OUT"
