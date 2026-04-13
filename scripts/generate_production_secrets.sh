#!/usr/bin/env bash
# Печатает случайные значения для прод-секретов. Сохраните вывод в менеджер секретов,
# не в репозиторий. Требуется openssl.
set -euo pipefail

rand_hex() { openssl rand -hex "$1"; }
rand_pw() {
  openssl rand -base64 32 | tr -d '\n' | tr '+/' '-_' | head -c "${1:-32}"
}

echo "# Скопируйте в безопасное хранилище (не в git):"
echo "SECRET_KEY=$(rand_hex 32)"
echo "POSTGRES_PASSWORD=$(rand_pw 32)"
echo "REDIS_PASSWORD=$(rand_pw 32)"
echo "ADMIN_PASSWORD=$(rand_pw 24)"
