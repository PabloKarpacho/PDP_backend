import os
from uuid import uuid4

import psycopg2
import pytest
from sqlalchemy import create_engine
from sqlalchemy import inspect
from sqlalchemy.engine import make_url

from src.database_control.postgres.db import upgrade_database_head


def _require_admin_dsn() -> str:
    admin_dsn = os.getenv("ALEMBIC_INTEGRATION_ADMIN_DSN")
    if not admin_dsn:
        pytest.skip(
            "Set ALEMBIC_INTEGRATION_ADMIN_DSN to run the Alembic integration test."
        )
    return admin_dsn


def _replace_database_name(
    dsn: str, database_name: str, *, drivername: str | None = None
) -> str:
    url = make_url(dsn)
    if drivername is not None:
        url = url.set(drivername=drivername)
    return url.set(database=database_name).render_as_string(hide_password=False)


@pytest.mark.integration
def test_alembic_upgrade_head_on_empty_database() -> None:
    admin_dsn = _require_admin_dsn()
    admin_db_dsn = _replace_database_name(
        admin_dsn, "postgres", drivername="postgresql"
    )
    test_database_name = f"pdp_alembic_{uuid4().hex[:8]}"
    test_db_dsn = _replace_database_name(
        admin_dsn,
        test_database_name,
        drivername="postgresql+asyncpg",
    )

    admin_connection = psycopg2.connect(admin_db_dsn)
    admin_connection.autocommit = True

    try:
        with admin_connection.cursor() as cursor:
            cursor.execute(f'CREATE DATABASE "{test_database_name}"')

        upgrade_database_head(test_db_dsn)

        engine = create_engine(
            _replace_database_name(
                test_db_dsn, test_database_name, drivername="postgresql+psycopg2"
            )
        )
        try:
            inspector = inspect(engine)
            table_names = set(inspector.get_table_names())
        finally:
            engine.dispose()

        assert {
            "alembic_version",
            "users",
            "teachers_students",
            "homeworks",
            "lessons",
        } <= table_names
    finally:
        with admin_connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = %s
                  AND pid <> pg_backend_pid()
                """,
                (test_database_name,),
            )
            cursor.execute(f'DROP DATABASE IF EXISTS "{test_database_name}"')
        admin_connection.close()
