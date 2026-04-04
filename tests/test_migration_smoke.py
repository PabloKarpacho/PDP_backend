import os
from uuid import uuid4

from alembic import command
import psycopg2
import pytest
from sqlalchemy import create_engine
from sqlalchemy import inspect
from sqlalchemy.engine import make_url

from src.database_control.postgres.db import build_alembic_config
from src.database_control.postgres.db import upgrade_database_head


def _require_admin_dsn() -> str:
    admin_dsn = os.getenv("ALEMBIC_INTEGRATION_ADMIN_DSN")
    if not admin_dsn:
        pytest.skip(
            "Set ALEMBIC_INTEGRATION_ADMIN_DSN to run the migration smoke test."
        )
    return admin_dsn


def _replace_database_name(
    dsn: str,
    database_name: str,
    *,
    drivername: str | None = None,
) -> str:
    url = make_url(dsn)
    if drivername is not None:
        url = url.set(drivername=drivername)
    return url.set(database=database_name).render_as_string(hide_password=False)


@pytest.mark.integration
def test_alembic_upgrade_head_creates_expected_schema() -> None:
    admin_dsn = _require_admin_dsn()
    admin_db_dsn = _replace_database_name(
        admin_dsn,
        "postgres",
        drivername="postgresql",
    )
    test_database_name = f"pdp_schema_{uuid4().hex[:8]}"
    target_dsn = _replace_database_name(
        admin_dsn,
        test_database_name,
        drivername="postgresql+asyncpg",
    )

    admin_connection = psycopg2.connect(admin_db_dsn)
    admin_connection.autocommit = True

    try:
        with admin_connection.cursor() as cursor:
            cursor.execute(f'CREATE DATABASE "{test_database_name}"')

        upgrade_database_head(target_dsn)

        engine = create_engine(
            _replace_database_name(
                target_dsn,
                test_database_name,
                drivername="postgresql+psycopg2",
            )
        )
        try:
            inspector = inspect(engine)

            teachers_students_columns = {
                column["name"]: column["type"]
                for column in inspector.get_columns("teachers_students")
            }
            teacher_student_fks = inspector.get_foreign_keys("teachers_students")
            lesson_fks = inspector.get_foreign_keys("lessons")
            lesson_indexes = {
                index["name"] for index in inspector.get_indexes("lessons")
            }
            lesson_uniques = {
                unique["name"] for unique in inspector.get_unique_constraints("lessons")
            }
        finally:
            engine.dispose()

        assert str(teachers_students_columns["teacher_id"]) == "VARCHAR"
        assert str(teachers_students_columns["student_id"]) == "VARCHAR"
        assert {
            tuple(fk["constrained_columns"]): tuple(fk["referred_columns"])
            for fk in teacher_student_fks
        } == {
            ("teacher_id",): ("id",),
            ("student_id",): ("id",),
        }
        assert {
            tuple(fk["constrained_columns"]): tuple(fk["referred_columns"])
            for fk in lesson_fks
        } == {
            ("teacher_id",): ("id",),
            ("student_id",): ("id",),
            ("homework_id",): ("id",),
        }
        assert "ix_lessons_teacher_id_start_time" in lesson_indexes
        assert "ix_lessons_student_id_start_time" in lesson_indexes
        assert "uq_lessons_homework_id" in lesson_uniques
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


@pytest.mark.integration
def test_alembic_upgrade_head_handles_legacy_orphan_lesson_refs() -> None:
    admin_dsn = _require_admin_dsn()
    admin_db_dsn = _replace_database_name(
        admin_dsn,
        "postgres",
        drivername="postgresql",
    )
    test_database_name = f"pdp_legacy_{uuid4().hex[:8]}"
    target_dsn = _replace_database_name(
        admin_dsn,
        test_database_name,
        drivername="postgresql+asyncpg",
    )

    admin_connection = psycopg2.connect(admin_db_dsn)
    admin_connection.autocommit = True

    try:
        with admin_connection.cursor() as cursor:
            cursor.execute(f'CREATE DATABASE "{test_database_name}"')

        alembic_config = build_alembic_config(target_dsn)
        command.upgrade(alembic_config, "20260329_120000")

        engine = create_engine(
            _replace_database_name(
                target_dsn,
                test_database_name,
                drivername="postgresql+psycopg2",
            )
        )
        try:
            with engine.begin() as connection:
                connection.exec_driver_sql(
                    """
                    INSERT INTO users (id, name, surname, email, role)
                    VALUES ('teacher-1', 'Teacher', 'One', 'teacher-1@example.com', 'teacher')
                    """
                )
                connection.exec_driver_sql(
                    """
                    INSERT INTO lessons (
                        start_time,
                        end_time,
                        theme,
                        lesson_description,
                        teacher_id,
                        student_id,
                        status
                    ) VALUES (
                        TIMESTAMP WITH TIME ZONE '2026-04-04 10:00:00+00',
                        TIMESTAMP WITH TIME ZONE '2026-04-04 11:00:00+00',
                        'Legacy lesson',
                        'Imported before FK enforcement',
                        'teacher-1',
                        'string',
                        'active'
                    )
                    """
                )
        finally:
            engine.dispose()

        upgrade_database_head(target_dsn)

        engine = create_engine(
            _replace_database_name(
                target_dsn,
                test_database_name,
                drivername="postgresql+psycopg2",
            )
        )
        try:
            with engine.begin() as connection:
                placeholder_user = connection.exec_driver_sql(
                    "SELECT id, role FROM users WHERE id = 'string'"
                ).one()
                lesson_row = connection.exec_driver_sql(
                    "SELECT student_id FROM lessons WHERE theme = 'Legacy lesson'"
                ).one()
        finally:
            engine.dispose()

        assert placeholder_user == ("string", "legacy")
        assert lesson_row == ("string",)
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
