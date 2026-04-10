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

2. Сгенерируйте self-signed сертификаты для backend и Keycloak:

Backend сертификат для локального HTTPS на `https://localhost`:

```bash
mkdir -p certs/backend certs/keycloak

openssl req -x509 -nodes -newkey rsa:2048 -sha256 -days 365 \
  -keyout certs/backend/key.pem \
  -out certs/backend/cert.pem \
  -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
```

Keycloak сертификат для внутреннего compose hostname `pdp-keycloak` и локального доступа с хоста:

```bash
openssl req -x509 -nodes -newkey rsa:2048 -sha256 -days 365 \
  -keyout certs/keycloak/key.pem \
  -out certs/keycloak/cert.pem \
  -subj "/CN=pdp-keycloak" \
  -addext "subjectAltName=DNS:pdp-keycloak,DNS:localhost,IP:127.0.0.1"
```

Если Keycloak должен открываться по внешнему IP или доменному имени, добавьте их в `subjectAltName`.

3. Запустите проект:

```bash
docker compose up -d --build
```

4. Примените миграции командой:

```bash
uv run python -m alembic upgrade head
```

5. Проверьте, что контейнеры поднялись:

```bash
docker compose ps
```

Backend использует свои сертификаты из `certs/backend`.
Keycloak использует отдельные сертификаты из `certs/keycloak`.
Backend проверяет TLS Keycloak через `KEYCLOAK_CA_BUNDLE`, который по умолчанию указывает на `./certs/keycloak/cert.pem` для локального запуска и переопределяется в контейнере на `/opt/certs/keycloak/cert.pem`.

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
