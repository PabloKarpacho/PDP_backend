FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV UVICORN_SSL_MODE=false
ENV UVICORN_SSL_CERTFILE=/opt/certs/backend/cert.pem
ENV UVICORN_SSL_KEYFILE=/opt/certs/backend/key.pem

WORKDIR /work

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends gcc curl && \
    apt-get upgrade -y && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock README.md ./

RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY scripts ./scripts
COPY certs /opt/certs

RUN chmod +x ./scripts/run-backend.sh

RUN useradd --create-home appuser && \
    mkdir -p /opt/certs/backend /opt/certs/keycloak && \
    chown -R appuser:appuser /work /opt/certs && \
    chmod 755 /opt/certs /opt/certs/backend /opt/certs/keycloak && \
    if [ -f /opt/certs/backend/cert.pem ]; then chmod 644 /opt/certs/backend/cert.pem; fi && \
    if [ -f /opt/certs/backend/key.pem ]; then chmod 600 /opt/certs/backend/key.pem; fi && \
    if [ -f /opt/certs/keycloak/cert.pem ]; then chmod 644 /opt/certs/keycloak/cert.pem; fi
USER appuser

EXPOSE 80

CMD ["./scripts/run-backend.sh"]
