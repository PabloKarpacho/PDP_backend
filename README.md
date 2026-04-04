# PDP Backend

[![codecov](https://codecov.io/gh/PabloKarpacho/PDP_backend/graph/badge.svg?token=O2mbV4lXaV)](https://codecov.io/gh/PabloKarpacho/PDP_backend)

Короткая инструкция по локальному запуску проекта через Docker Compose.

## Что поднимается

- `pdp-backend` — FastAPI backend
- `pdp-db` — PostgreSQL
- `pdp-pgadmin` — pgAdmin
- `pdp-minio` — MinIO
- `pdp-keycloak` — Keycloak

## Требования

- Docker
- Docker Compose Plugin (`docker compose`)

## Локальный запуск

1. Подготовьте переменные окружения:

```bash
cp env.example .env
```

Если `.env` уже есть, проверьте в нём порты и доступы.

2. Запустите проект:

```bash
docker compose up -d --build
```

3. Примените миграции командой:

```bash
uv run python -m alembic upgrade head
```

4. Проверьте, что контейнеры поднялись:

```bash
docker compose ps
```

## Миграции Alembic

Применить все миграции:

```bash
uv run python -m alembic upgrade head
```

Проверить текущую ревизию:

```bash
uv run python -m alembic current
```

Создать новую миграцию:

```bash
uv run python -m alembic revision -m "your migration name"
```

Если нужно сгенерировать миграцию по изменениям моделей:

```bash
uv run python -m alembic revision --autogenerate -m "describe changes"
```

CI автоматически запускает:

```bash
uv run python -m alembic upgrade head
```

Production и локальный запуск должны использовать этот шаг явно до проверки функциональности или вывода сервиса в трафик.

## Полезные URL

- Backend: `http://localhost:8000`
- Keycloak: `http://localhost:8080`
- pgAdmin: `http://localhost:8081`
- MinIO API: `http://localhost:9000`
- MinIO Console: `http://localhost:7001`

## Полезные команды

Логи:

```bash
docker compose logs -f
```

Остановка:

```bash
docker compose down
```

Остановка с удалением volume-данных:

```bash
docker compose down -v
```

Установка pre-commit хуков:

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

Хуки используют `ruff check --fix` и `ruff format`

## Примечание

При старте Keycloak импортирует realm из `realm-export.json`.
