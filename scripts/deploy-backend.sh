#!/usr/bin/env bash

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/PDP_backend}"
BRANCH="${BRANCH:-main}"
BACKEND_SERVICE="${BACKEND_SERVICE:-pdp-backend}"
READINESS_ATTEMPTS="${READINESS_ATTEMPTS:-30}"
READINESS_INTERVAL_SECONDS="${READINESS_INTERVAL_SECONDS:-2}"
READINESS_TIMEOUT_SECONDS="${READINESS_TIMEOUT_SECONDS:-5}"


wait_for_readiness() {
  local attempt

  for attempt in $(seq 1 "$READINESS_ATTEMPTS"); do
    if curl \
      --fail \
      --silent \
      --show-error \
      --connect-timeout "$READINESS_TIMEOUT_SECONDS" \
      --max-time "$READINESS_TIMEOUT_SECONDS" \
      "$READINESS_URL" >/dev/null 2>&1; then
      echo "Backend is ready"
      return 0
    fi

    if [ "$attempt" -lt "$READINESS_ATTEMPTS" ]; then
      echo "Readiness probe failed (attempt ${attempt}/${READINESS_ATTEMPTS}), retrying in ${READINESS_INTERVAL_SECONDS}s"
      sleep "$READINESS_INTERVAL_SECONDS"
      continue
    fi

    echo "Readiness probe failed (attempt ${attempt}/${READINESS_ATTEMPTS})"
  done

  return 1
}


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
if wait_for_readiness; then
  docker image prune -f
  exit 0
fi

print_backend_diagnostics
echo "Backend failed readiness check: $READINESS_URL"
exit 1
