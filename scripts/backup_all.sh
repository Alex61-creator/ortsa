#!/usr/bin/env bash
# PostgreSQL + storage подряд. Переменные окружения — см. backup_postgres.sh.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
"$DIR/backup_postgres.sh"
"$DIR/backup_storage.sh"
