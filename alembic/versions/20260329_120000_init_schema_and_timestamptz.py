"""Initialize schema and store datetimes as timezone-aware values.

Revision ID: 20260329_120000
Revises:
Create Date: 2026-03-29 12:00:00
"""

from collections.abc import Iterable

from alembic import context, op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260329_120000"
down_revision = None
branch_labels = None
depends_on = None


DATETIME_COLUMNS: dict[str, tuple[str, ...]] = {
    "users": ("updated_at", "created_at"),
    "lessons": ("start_time", "end_time", "updated_at", "created_at"),
    "homeworks": ("deadline", "updated_at", "created_at"),
}


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _is_timezone_aware(
    inspector: sa.Inspector, table_name: str, column_name: str
) -> bool:
    for column in inspector.get_columns(table_name):
        if column["name"] == column_name:
            return bool(getattr(column["type"], "timezone", False))
    return False


def _create_users_table() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("surname", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )


def _create_teachers_students_table() -> None:
    op.create_table(
        "teachers_students",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("teacher_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def _create_homeworks_table() -> None:
    op.create_table(
        "homeworks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("files_urls", sa.JSON(), nullable=True),
        sa.Column("answer", sa.String(), nullable=True),
        sa.Column("sent_files", sa.JSON(), nullable=True),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def _create_lessons_table() -> None:
    op.create_table(
        "lessons",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("theme", sa.String(), nullable=True),
        sa.Column("lesson_description", sa.String(), nullable=True),
        sa.Column("teacher_id", sa.String(), nullable=False),
        sa.Column("student_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("homework_id", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["homework_id"], ["homeworks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def _create_baseline_schema() -> None:
    _create_users_table()
    _create_teachers_students_table()
    _create_homeworks_table()
    _create_lessons_table()


def _ensure_tables_exist(inspector: sa.Inspector) -> None:
    if not _table_exists(inspector, "users"):
        _create_users_table()

    if not _table_exists(inspector, "teachers_students"):
        _create_teachers_students_table()

    if not _table_exists(inspector, "homeworks"):
        _create_homeworks_table()

    if not _table_exists(inspector, "lessons"):
        _create_lessons_table()


def _convert_columns_to_timestamptz(
    inspector: sa.Inspector,
    table_name: str,
    column_names: Iterable[str],
) -> None:
    if not _table_exists(inspector, table_name):
        return

    existing_columns = _column_names(inspector, table_name)

    for column_name in column_names:
        if column_name not in existing_columns:
            continue

        if _is_timezone_aware(inspector, table_name, column_name):
            continue

        op.execute(
            sa.text(
                f"""
                ALTER TABLE "{table_name}"
                ALTER COLUMN "{column_name}"
                TYPE TIMESTAMP WITH TIME ZONE
                USING "{column_name}" AT TIME ZONE 'UTC'
                """
            )
        )


def upgrade() -> None:
    if context.is_offline_mode():
        _create_baseline_schema()
        return

    bind = op.get_bind()
    inspector = sa.inspect(bind)

    _ensure_tables_exist(inspector)

    inspector = sa.inspect(bind)
    for table_name, column_names in DATETIME_COLUMNS.items():
        _convert_columns_to_timestamptz(inspector, table_name, column_names)
        inspector = sa.inspect(bind)


def downgrade() -> None:
    raise NotImplementedError(
        "Downgrade is not supported for the initial baseline migration."
    )
