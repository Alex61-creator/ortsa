#!/usr/bin/env bash
# Снимок PostgreSQL (pg_dump custom format, gzip) через docker compose exec.
# Требуется запущенный stack: docker compose -f docker-compose.prod.yml --env-file .env up -d
#
# Переменные (опционально):
#   COMPOSE_FILE — путь к compose (по умолчанию: docker-compose.prod.yml в корне репо)
#   ENV_FILE     — .env с POSTGRES_* (по умолчанию: .env)
#   BACKUP_ROOT  — каталог для файлов (по умолчанию: ./backups от корня репо)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT/docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-$ROOT/.env}"
BACKUP_ROOT="${BACKUP_ROOT:-$ROOT/backups}"
mkdir -p "$BACKUP_ROOT"

TS="$(date +%Y%m%d_%H%M%S)"
OUT="$BACKUP_ROOT/astro_pg_${TS}.dump.gz"

cd "$ROOT"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T postgres \
  sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' | gzip >"$OUT"

echo "OK: $OUT"
