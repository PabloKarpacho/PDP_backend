import os

from src.database_control.postgres.db import get_database_runtime_config


def build_sync_dsn_for_alembic(dsn: str) -> str:
    if dsn.startswith("postgresql+asyncpg://"):
        return dsn.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    return dsn


def resolve_alembic_database_url(default_url: str) -> str:
    database_url = os.getenv("ALEMBIC_DATABASE_URL")
    if database_url:
        return database_url

    project_dsn = os.getenv("POSTGRESQL_DSN")
    if project_dsn:
        return build_sync_dsn_for_alembic(project_dsn)

    runtime_dsn = get_database_runtime_config().sync_dsn
    if runtime_dsn:
        return runtime_dsn

    return default_url
