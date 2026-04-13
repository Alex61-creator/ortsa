#!/usr/bin/env bash
# Быстрая проверка: нет ли в индексе git файлов с очевидными секретами.
# Не замена аудиту; при сомнениях: git log --all -- .env
set -euo pipefail

cd "$(dirname "$0")/.."

bad=0
while IFS= read -r f; do
  case "$f" in
    .venv/*|.venv-*/*|node_modules/*|*/site-packages/*) continue ;;
  esac
  case "$f" in
    .env|.env.local|.env.production|*.pem|*.key|*id_rsa*|*id_ed25519*)
      echo "TRACKED (проверьте): $f"
      bad=1
      ;;
  esac
done < <(git ls-files)

if [[ "$bad" -eq 0 ]]; then
  echo "OK: в индексе нет типичных имён .env/.pem/.key (кроме ожидаемых шаблонов)."
fi
