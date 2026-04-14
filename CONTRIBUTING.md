# Участие в разработке

## Python и зависимости backend

- Поддерживаемая версия: **Python 3.12.x** (см. [`.python-version`](.python-version), [`requirements.txt`](requirements.txt), [`Dockerfile`](Dockerfile), job `pytest` в [`.github/workflows/tests.yml`](.github/workflows/tests.yml)).
- Диапазон в [`pyproject.toml`](pyproject.toml): `>=3.12,<3.13` — **Python 3.13** пока не целевой для CI и может ломать импорт SQLAlchemy при `pytest`.
- Перед PR: `pip install -r requirements.txt -r requirements-dev.txt` и `pytest -q` на **3.12** (или доверьтесь CI).

## Прочее

- Пользовательский интерфейс в продакшене работает как **React SPA** из `frontend/` (`frontend-dist` через Caddy).
- Каталог `HTML макеты/` — референсы для дизайна; перенос выполняется в `frontend/src/`.
