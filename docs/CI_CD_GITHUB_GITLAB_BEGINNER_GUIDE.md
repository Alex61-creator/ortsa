# CI/CD для новичка: как тестировать и выкатывать в прод через GitHub и GitLab

Версия: `v1.0`  
Дата обновления: `2026-04-22`

Этот документ объясняет "на пальцах", как безопасно выпускать новые фичи:

- писать код в отдельной ветке;
- автоматически проверять код (CI);
- выкатывать сначала на `staging`, потом на `production` (CD);
- быстро откатываться, если что-то сломалось.

---

## 1. Что означают основные термины

- `main` — главная ветка (условно стабильная версия).
- `feature/*` — рабочая ветка под конкретную задачу.
- `Pull Request` (GitHub) / `Merge Request` (GitLab) — запрос на слияние кода в `main`.
- `CI` — автоматические проверки (линтер, тесты, сборка).
- `CD` — автоматическая доставка/деплой.
- `staging` — тестовая среда, максимально похожая на прод.
- `production` (`prod`) — боевая среда с реальными пользователями.
- `rollback` — откат на предыдущую стабильную версию.

---

## 2. Общий процесс релиза (одинаково для GitHub и GitLab)

Используйте этот базовый цикл:

1. Создаёте ветку: `feature/название-фичи`.
2. Пишете код небольшими шагами.
3. Локально запускаете минимум:
   - `lint`
   - `tests`
   - `build`
4. Пушите ветку в удалённый репозиторий.
5. Создаёте PR/MR в `main`.
6. CI автоматически запускает проверки.
7. Если CI зелёный и ревью пройдено, делаете merge.
8. После merge:
   - деплой на `staging`;
   - ручная проверка (smoke-test);
   - затем деплой на `prod`.
9. После деплоя следите за логами/ошибками 15-30 минут.
10. Если есть проблема, делаете rollback.

---

## 3. Что должно быть настроено до первого прод-релиза

Минимальный обязательный набор:

1. Правило: запрет прямого пуша в `main`.
2. Обязательный PR/MR.
3. Обязательные зелёные CI checks перед merge.
4. Отдельные окружения `staging` и `production`.
5. Секреты в GitHub/GitLab Secrets/Variables (не в репозитории).
6. Понятный rollback-план (заранее, до релиза).

---

## 4. GitHub: пошаговая настройка

## 4.1. Что нажимать в интерфейсе GitHub

1. Откройте репозиторий -> `Settings` -> `Branches`.
2. Создайте branch protection rule для `main`:
   - `Require a pull request before merging`
   - `Require status checks to pass before merging`
   - `Require branches to be up to date before merging`
   - (опционально) `Require approvals`
3. Откройте `Settings` -> `Environments`:
   - создайте `staging`
   - создайте `production` и включите `Required reviewers` для ручного approve.
4. Откройте `Settings` -> `Secrets and variables` -> `Actions`:
   - добавьте все токены/пароли/API-ключи.

Пример имен секретов:

- `SSH_HOST_STAGING`
- `SSH_USER_STAGING`
- `SSH_KEY_STAGING`
- `SSH_HOST_PROD`
- `SSH_USER_PROD`
- `SSH_KEY_PROD`

---

## 4.2. Минимальная структура workflow-файлов

Создайте 3 файла:

- `.github/workflows/ci.yml`
- `.github/workflows/deploy-staging.yml`
- `.github/workflows/deploy-production.yml`

---

## 4.3. Пример `ci.yml` (проверки для PR)

```yaml
name: CI

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
      - run: npm ci
      - run: npm run lint
      - run: npm test
      - run: npm run build
```

Если у вас Python backend, добавьте отдельный job с `python`, `pip install`, `pytest`.

---

## 4.4. Пример `deploy-staging.yml` (авто после merge в main)

```yaml
name: Deploy Staging

on:
  push:
    branches: [main]

concurrency:
  group: deploy-staging
  cancel-in-progress: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.SSH_HOST_STAGING }}
          username: ${{ secrets.SSH_USER_STAGING }}
          key: ${{ secrets.SSH_KEY_STAGING }}
          script: |
            set -e
            cd /opt/app
            git fetch origin
            git checkout main
            git pull origin main
            docker compose -f docker-compose.prod.yml up -d --build
            docker image prune -f
```

---

## 4.5. Пример `deploy-production.yml` (ручной запуск)

```yaml
name: Deploy Production

on:
  workflow_dispatch:
    inputs:
      release_ref:
        description: "Tag or branch to deploy"
        required: true
        default: "main"

concurrency:
  group: deploy-production
  cancel-in-progress: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.inputs.release_ref }}
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.SSH_HOST_PROD }}
          username: ${{ secrets.SSH_USER_PROD }}
          key: ${{ secrets.SSH_KEY_PROD }}
          script: |
            set -e
            cd /opt/app
            git fetch origin
            git checkout main
            git pull origin main
            docker compose -f docker-compose.prod.yml up -d --build
            docker image prune -f
```

`environment: production` + required reviewers в настройках = "перед продом нужен ручной approve".

---

## 5. GitLab: пошаговая настройка

## 5.1. Что нажимать в интерфейсе GitLab

1. Откройте проект -> `Settings` -> `Repository` -> `Protected branches`.
2. Для `main`:
   - запретите прямые push;
   - разрешите merge только через Merge Request.
3. Откройте `Settings` -> `CI/CD` -> `Variables`:
   - добавьте секреты (Masked + Protected).
4. Откройте `Settings` -> `Merge requests`:
   - включите обязательные approvals (при необходимости).

---

## 5.2. Минимальный `.gitlab-ci.yml`

```yaml
stages:
  - test
  - deploy_staging
  - deploy_production

default:
  image: node:20

cache:
  key: ${CI_COMMIT_REF_SLUG}
  paths:
    - node_modules/

lint_test_build:
  stage: test
  script:
    - npm ci
    - npm run lint
    - npm test
    - npm run build
  only:
    - merge_requests
    - main

deploy_staging:
  stage: deploy_staging
  image: alpine:3.20
  before_script:
    - apk add --no-cache openssh-client
  script:
    - mkdir -p ~/.ssh
    - echo "$SSH_KEY_STAGING" | tr -d '\r' > ~/.ssh/id_rsa
    - chmod 600 ~/.ssh/id_rsa
    - ssh -o StrictHostKeyChecking=no $SSH_USER_STAGING@$SSH_HOST_STAGING "cd /opt/app && git pull origin main && docker compose -f docker-compose.prod.yml up -d --build"
  only:
    - main
  environment:
    name: staging

deploy_production:
  stage: deploy_production
  image: alpine:3.20
  before_script:
    - apk add --no-cache openssh-client
  script:
    - mkdir -p ~/.ssh
    - echo "$SSH_KEY_PROD" | tr -d '\r' > ~/.ssh/id_rsa
    - chmod 600 ~/.ssh/id_rsa
    - ssh -o StrictHostKeyChecking=no $SSH_USER_PROD@$SSH_HOST_PROD "cd /opt/app && git pull origin main && docker compose -f docker-compose.prod.yml up -d --build"
  only:
    - main
  when: manual
  environment:
    name: production
```

`when: manual` для production = ручное подтверждение перед деплоем.

---

## 6. Настройка staging и production на VPS

В простом варианте это два отдельных сервера.

Рекомендуемый минимум:

1. `staging VPS`:
   - отдельный домен/поддомен;
   - отдельная БД;
   - отдельные secrets;
   - тот же стек, что в prod.
2. `production VPS`:
   - только стабильный код;
   - доступ ограничен;
   - мониторинг и backup обязательны.

Важно:

- никогда не тестируйте фичи на прод-БД;
- staging должен быть максимально похож на prod.

---

## 7. Smoke-check после деплоя на staging

Минимальный ручной чеклист:

1. Приложение открывается.
2. Логин работает.
3. Основной пользовательский сценарий работает end-to-end.
4. API не возвращает массово 5xx.
5. Новая фича работает как ожидается.
6. Старый критичный функционал не сломан.

Если хотя бы один пункт красный -> в production не выкатываем.

---

## 8. Как делать rollback

Rollback должен быть прописан до релиза.

Варианты:

1. Деплой предыдущего git tag (`v1.2.2` вместо `v1.2.3`).
2. Деплой предыдущего Docker image.
3. Переключение трафика на предыдущую среду (blue/green).

Минимальная цель: откат за несколько минут.

---

## 9. Типичные ошибки новичка

1. Прямой push в `main`.
2. Merge при красном CI.
3. Отсутствие staging.
4. Хранение секретов в репозитории.
5. Деплой в прод без rollback-плана.
6. Слишком большой релиз (лучше маленькие и частые).

---

## 10. Минимальный "боевой" чеклист релиза

Перед merge:

- [ ] PR/MR создан.
- [ ] CI зелёный (`lint`, `tests`, `build`).
- [ ] Ревью завершено.

Перед production:

- [ ] Staging деплой выполнен.
- [ ] Smoke-check пройден.
- [ ] Секреты и env проверены.
- [ ] Rollback-план готов.

После production:

- [ ] Проверены логи и метрики.
- [ ] Проверены критичные пользовательские сценарии.
- [ ] Зафиксирована версия релиза и время выката.

---

## 11. Рекомендуемый стартовый план на 1 день

1. Запретить push в `main`.
2. Включить обязательные PR/MR.
3. Добавить CI с 3 шагами (`lint`, `tests`, `build`).
4. Поднять `staging` (даже на простом VPS).
5. Настроить ручной прод-деплой.
6. Написать короткий rollback-runbook в `docs`.

После этого у вас уже будет базовый, безопасный и повторяемый процесс релиза.

