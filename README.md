# PDP Backend

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

3. Проверьте, что контейнеры поднялись:

```bash
docker compose ps
```

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

## Примечание

При старте Keycloak импортирует realm из `realm-export.json`.
