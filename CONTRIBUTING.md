# Участие в разработке

## Python и зависимости backend

- Поддерживаемая версия: **Python 3.12.x** (см. [`.python-version`](.python-version), [`requirements.txt`](requirements.txt), [`Dockerfile`](Dockerfile), job `pytest` в [`.github/workflows/tests.yml`](.github/workflows/tests.yml)).
- Диапазон в [`pyproject.toml`](pyproject.toml): `>=3.12,<3.13` — **Python 3.13** пока не целевой для CI и может ломать импорт SQLAlchemy при `pytest`.
- Перед PR: `pip install -r requirements.txt -r requirements-dev.txt` и `pytest -q` на **3.12** (или доверьтесь CI).

## Прочее

- **Лендинг и кабинет в продакшене** отдаются из каталога [`static/`](static/). Правки вносятся только туда; каталог `HTML макеты/` — референс, не источник для деплоя.
- Перенос вёрстки из макетов в `static/` — отдельным PR с проверкой `/`, `/dashboard` (SPA), OAuth callback.
