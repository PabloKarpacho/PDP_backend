FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /work

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends gcc curl && \
    apt-get upgrade -y && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock README.md ./

RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY scripts ./scripts

RUN chmod +x ./scripts/run-backend.sh

RUN useradd --create-home appuser && chown -R appuser:appuser /work
USER appuser

EXPOSE 8000

CMD ["./scripts/run-backend.sh"]
