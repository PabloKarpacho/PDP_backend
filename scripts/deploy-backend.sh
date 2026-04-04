#!/usr/bin/env bash

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/PDP_backend}"
BRANCH="${BRANCH:-main}"
BACKEND_SERVICE="${BACKEND_SERVICE:-pdp-backend}"

if [ ! -d "$APP_DIR/.git" ]; then
  echo "Repository not found in $APP_DIR"
  exit 1
fi

cd "$APP_DIR"

echo "==> Updating repository"
git fetch origin
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

if [ ! -f ".env" ]; then
  echo ".env not found in $APP_DIR"
  exit 1
fi

set -a
source ./.env
set +a

APP_PORT="${APP_PORT:-8000}"
READINESS_URL="http://localhost:${APP_PORT}/actuator/health/readiness"

echo "==> Building backend image"
docker compose build "$BACKEND_SERVICE"

echo "==> Starting dependencies"
docker compose up -d pdp-db pdp-minio pdp-keycloak

echo "==> Applying database migrations"
docker compose run --rm "$BACKEND_SERVICE" uv run python -m alembic upgrade head

echo "==> Starting backend"
docker compose up -d "$BACKEND_SERVICE"

echo "==> Waiting for readiness at $READINESS_URL"
for _ in $(seq 1 30); do
  if curl -fsS "$READINESS_URL" >/dev/null; then
    echo "Backend is ready"
    docker image prune -f
    exit 0
  fi
  sleep 2
done

echo "Backend failed readiness check: $READINESS_URL"
exit 1
