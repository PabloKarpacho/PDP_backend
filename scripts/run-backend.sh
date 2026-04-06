#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

APP_MODULE="${APP_MODULE:-src.app:app}"
APP_HOST="${APP_HOST:-0.0.0.0}"
APP_PORT="${APP_PORT:-8000}"
APP_WORKERS="${APP_WORKERS:-1}"
PROJECT_VENV="${UV_PROJECT_ENVIRONMENT:-$PROJECT_ROOT/.venv}"

cd "$PROJECT_ROOT"

uvicorn_args=(
    "$APP_MODULE"
    --host "$APP_HOST"
    --port "$APP_PORT"
    --ssl-certfile="$PROJECT_ROOT/certs/cert.pem"
    --ssl-keyfile="$PROJECT_ROOT/certs/key.pem"
)

if [[ "$APP_WORKERS" =~ ^[0-9]+$ ]] && [ "$APP_WORKERS" -gt 1 ]; then
    uvicorn_args+=(--workers "$APP_WORKERS")
fi

if [ -x "$PROJECT_VENV/bin/python" ] && [ -x "$PROJECT_VENV/bin/uvicorn" ]; then
    exec "$PROJECT_VENV/bin/uvicorn" "${uvicorn_args[@]}"
fi

if command -v uv >/dev/null 2>&1; then
    uv sync --frozen --no-dev --no-install-project
    exec uv run --no-sync uvicorn "${uvicorn_args[@]}"
fi

exec uvicorn "${uvicorn_args[@]}"
