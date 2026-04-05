#!/usr/bin/env bash

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/PDP_backend}"
BRANCH="${BRANCH:-main}"
BACKEND_SERVICE="${BACKEND_SERVICE:-pdp-backend}"
print_backend_diagnostics() {
  echo "==> Backend container status"
  docker compose ps "$BACKEND_SERVICE" || true

  echo "==> Recent backend logs"
  docker compose logs --tail=50 "$BACKEND_SERVICE" || true
}

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

echo "==> Building backend image"
docker compose build "$BACKEND_SERVICE"

echo "==> Starting dependencies"
docker compose up -d pdp-db pdp-minio pdp-keycloak

echo "==> Applying database migrations"
docker compose run --rm "$BACKEND_SERVICE" uv run python -m alembic upgrade head

echo "==> Removing previous backend container"
docker compose rm -fsv "$BACKEND_SERVICE" || true

echo "==> Starting backend"
if docker compose up -d --force-recreate "$BACKEND_SERVICE"; then
  docker image prune -f
  exit 0
fi

print_backend_diagnostics
echo "Backend container failed to start"
exit 1
