#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

APP_MODULE="${APP_MODULE:-src.app:app}"
APP_HOST="${APP_HOST:-0.0.0.0}"
APP_PORT="${APP_PORT:-8000}"
APP_WORKERS="${APP_WORKERS:-1}"
PROJECT_VENV="${UV_PROJECT_ENVIRONMENT:-$PROJECT_ROOT/.venv}"
UVICORN_SSL_MODE="${UVICORN_SSL_MODE:-auto}"
UVICORN_SSL_CERTFILE="${UVICORN_SSL_CERTFILE:-/opt/certs/cert.pem}"
UVICORN_SSL_KEYFILE="${UVICORN_SSL_KEYFILE:-/opt/certs/key.pem}"

cd "$PROJECT_ROOT"

uvicorn_args=(
    "$APP_MODULE"
    --host "$APP_HOST"
    --port "$APP_PORT"
)


configure_ssl() {
    case "$UVICORN_SSL_MODE" in
        false)
            echo "Uvicorn SSL disabled explicitly."
            return 0
            ;;
        true)
            if [[ ! -r "$UVICORN_SSL_CERTFILE" ]]; then
                echo "Configured SSL certificate is not readable: $UVICORN_SSL_CERTFILE" >&2
                return 1
            fi
            if [[ ! -r "$UVICORN_SSL_KEYFILE" ]]; then
                echo "Configured SSL private key is not readable: $UVICORN_SSL_KEYFILE" >&2
                return 1
            fi
            uvicorn_args+=(
                --ssl-certfile="$UVICORN_SSL_CERTFILE"
                --ssl-keyfile="$UVICORN_SSL_KEYFILE"
            )
            echo "Uvicorn SSL enabled."
            return 0
            ;;
        auto)
            if [[ -r "$UVICORN_SSL_CERTFILE" && -r "$UVICORN_SSL_KEYFILE" ]]; then
                uvicorn_args+=(
                    --ssl-certfile="$UVICORN_SSL_CERTFILE"
                    --ssl-keyfile="$UVICORN_SSL_KEYFILE"
                )
                echo "Uvicorn SSL enabled automatically."
                return 0
            fi
            echo "Uvicorn SSL skipped: certificate or key is missing or unreadable."
            return 0
            ;;
        *)
            echo "Invalid UVICORN_SSL_MODE: $UVICORN_SSL_MODE (expected: auto, true, false)" >&2
            return 1
            ;;
    esac
}


configure_ssl

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
