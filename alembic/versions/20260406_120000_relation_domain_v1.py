"""Promote teacher-student links to a relation domain with lifecycle fields.

Revision ID: 20260406_120000
Revises: 20260404_090000
Create Date: 2026-04-06 12:00:00.000000
"""

from collections.abc import Iterable

from alembic import op
import sqlalchemy as sa


revision = "20260406_120000"
down_revision = "20260404_090000"
branch_labels = None
depends_on = None

TABLE_NAME = "teachers_students"
STATUS_COLUMN = "status"
ARCHIVED_AT_COLUMN = "archived_at"
UPDATED_AT_COLUMN = "updated_at"
CREATED_AT_COLUMN = "created_at"
OLD_TEACHER_INDEX = "ix_teachers_students_teacher_id"
OLD_STUDENT_INDEX = "ix_teachers_students_student_id"
TEACHER_STATUS_INDEX = "ix_teachers_students_teacher_id_status"
STUDENT_STATUS_INDEX = "ix_teachers_students_student_id_status"
NOT_SELF_CHECK = "ck_teachers_students_not_self"
STATUS_CHECK = "ck_teachers_students_status"
ARCHIVED_AT_MATCHES_STATUS_CHECK = "ck_teachers_students_archived_at_matches_status"


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _check_constraint_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {
        constraint["name"]
        for constraint in inspector.get_check_constraints(table_name)
        if constraint.get("name")
    }


def _drop_indexes_if_exist(index_names: Iterable[str]) -> None:
    inspector = sa.inspect(op.get_bind())
    existing_indexes = _index_names(inspector, TABLE_NAME)
    for index_name in index_names:
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name=TABLE_NAME)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, TABLE_NAME):
        return

    column_names = _column_names(inspector, TABLE_NAME)
    with op.batch_alter_table(TABLE_NAME) as batch_op:
        if STATUS_COLUMN not in column_names:
            batch_op.add_column(
                sa.Column(
                    STATUS_COLUMN,
                    sa.String(),
                    nullable=True,
                    server_default=sa.text("'active'"),
                )
            )
        if ARCHIVED_AT_COLUMN not in column_names:
            batch_op.add_column(
                sa.Column(
                    ARCHIVED_AT_COLUMN,
                    sa.DateTime(timezone=True),
                    nullable=True,
                )
            )
        if UPDATED_AT_COLUMN not in column_names:
            batch_op.add_column(
                sa.Column(
                    UPDATED_AT_COLUMN,
                    sa.DateTime(timezone=True),
                    nullable=True,
                    server_default=sa.text("now()"),
                )
            )
        if CREATED_AT_COLUMN not in column_names:
            batch_op.add_column(
                sa.Column(
                    CREATED_AT_COLUMN,
                    sa.DateTime(timezone=True),
                    nullable=True,
                    server_default=sa.text("now()"),
                )
            )

    op.execute(
        sa.text(
            """
            DELETE FROM teachers_students
            WHERE teacher_id = student_id
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE teachers_students
            SET status = 'active'
            WHERE status IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE teachers_students
            SET archived_at = NULL
            WHERE status = 'active'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE teachers_students
            SET updated_at = COALESCE(updated_at, now()),
                created_at = COALESCE(created_at, now())
            """
        )
    )

    with op.batch_alter_table(TABLE_NAME) as batch_op:
        batch_op.alter_column(
            STATUS_COLUMN,
            existing_type=sa.String(),
            nullable=False,
            server_default=sa.text("'active'"),
        )
        batch_op.alter_column(
            UPDATED_AT_COLUMN,
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        )
        batch_op.alter_column(
            CREATED_AT_COLUMN,
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        )

    inspector = sa.inspect(bind)
    existing_checks = _check_constraint_names(inspector, TABLE_NAME)
    with op.batch_alter_table(TABLE_NAME) as batch_op:
        if NOT_SELF_CHECK not in existing_checks:
            batch_op.create_check_constraint(
                NOT_SELF_CHECK,
                "teacher_id <> student_id",
            )
        if STATUS_CHECK not in existing_checks:
            batch_op.create_check_constraint(
                STATUS_CHECK,
                "status IN ('active', 'archived')",
            )
        if ARCHIVED_AT_MATCHES_STATUS_CHECK not in existing_checks:
            batch_op.create_check_constraint(
                ARCHIVED_AT_MATCHES_STATUS_CHECK,
                "(status = 'active' AND archived_at IS NULL) OR "
                "(status = 'archived' AND archived_at IS NOT NULL)",
            )

    _drop_indexes_if_exist([OLD_TEACHER_INDEX, OLD_STUDENT_INDEX])

    inspector = sa.inspect(bind)
    existing_indexes = _index_names(inspector, TABLE_NAME)
    if TEACHER_STATUS_INDEX not in existing_indexes:
        op.create_index(
            TEACHER_STATUS_INDEX,
            TABLE_NAME,
            ["teacher_id", "status"],
        )

    inspector = sa.inspect(bind)
    existing_indexes = _index_names(inspector, TABLE_NAME)
    if STUDENT_STATUS_INDEX not in existing_indexes:
        op.create_index(
            STUDENT_STATUS_INDEX,
            TABLE_NAME,
            ["student_id", "status"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, TABLE_NAME):
        return

    _drop_indexes_if_exist([TEACHER_STATUS_INDEX, STUDENT_STATUS_INDEX])

    inspector = sa.inspect(bind)
    existing_indexes = _index_names(inspector, TABLE_NAME)
    if OLD_TEACHER_INDEX not in existing_indexes:
        op.create_index(OLD_TEACHER_INDEX, TABLE_NAME, ["teacher_id"])

    inspector = sa.inspect(bind)
    existing_indexes = _index_names(inspector, TABLE_NAME)
    if OLD_STUDENT_INDEX not in existing_indexes:
        op.create_index(OLD_STUDENT_INDEX, TABLE_NAME, ["student_id"])

    existing_checks = _check_constraint_names(inspector, TABLE_NAME)
    with op.batch_alter_table(TABLE_NAME) as batch_op:
        if ARCHIVED_AT_MATCHES_STATUS_CHECK in existing_checks:
            batch_op.drop_constraint(
                ARCHIVED_AT_MATCHES_STATUS_CHECK,
                type_="check",
            )
        if STATUS_CHECK in existing_checks:
            batch_op.drop_constraint(STATUS_CHECK, type_="check")
        if NOT_SELF_CHECK in existing_checks:
            batch_op.drop_constraint(NOT_SELF_CHECK, type_="check")

        batch_op.drop_column(ARCHIVED_AT_COLUMN)
        batch_op.drop_column(UPDATED_AT_COLUMN)
        batch_op.drop_column(CREATED_AT_COLUMN)
        batch_op.drop_column(STATUS_COLUMN)
