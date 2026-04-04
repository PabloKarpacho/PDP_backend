"""Align relationship column types, foreign keys, and indexes.

Revision ID: 20260404_090000
Revises: 20260329_120000
Create Date: 2026-04-04 09:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260404_090000"
down_revision = "20260329_120000"
branch_labels = None
depends_on = None


LESSON_TEACHER_TIME_INDEX = "ix_lessons_teacher_id_start_time"
LESSON_STUDENT_TIME_INDEX = "ix_lessons_student_id_start_time"
TEACHERS_STUDENTS_TEACHER_INDEX = "ix_teachers_students_teacher_id"
TEACHERS_STUDENTS_STUDENT_INDEX = "ix_teachers_students_student_id"
TEACHERS_STUDENTS_UNIQUE = "uq_teachers_students_teacher_student"
LESSON_HOMEWORK_UNIQUE = "uq_lessons_homework_id"
TEACHERS_STUDENTS_TEACHER_FK = "fk_teachers_students_teacher_id_users"
TEACHERS_STUDENTS_STUDENT_FK = "fk_teachers_students_student_id_users"
LESSON_TEACHER_FK = "fk_lessons_teacher_id_users"
LESSON_STUDENT_FK = "fk_lessons_student_id_users"
LESSON_HOMEWORK_FK = "fk_lessons_homework_id_homeworks"


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_type(
    inspector: sa.Inspector,
    table_name: str,
    column_name: str,
) -> sa.types.TypeEngine | None:
    for column in inspector.get_columns(table_name):
        if column["name"] == column_name:
            return column["type"]
    return None


def _is_string_column(
    inspector: sa.Inspector,
    table_name: str,
    column_name: str,
) -> bool:
    column_type = _column_type(inspector, table_name, column_name)
    return isinstance(column_type, sa.String)


def _foreign_key(
    inspector: sa.Inspector,
    table_name: str,
    constrained_columns: list[str],
    referred_table: str,
) -> dict | None:
    for foreign_key in inspector.get_foreign_keys(table_name):
        if (
            foreign_key["constrained_columns"] == constrained_columns
            and foreign_key["referred_table"] == referred_table
        ):
            return foreign_key
    return None


def _unique_constraint_exists(
    inspector: sa.Inspector,
    table_name: str,
    constraint_name: str,
) -> bool:
    return any(
        constraint["name"] == constraint_name
        for constraint in inspector.get_unique_constraints(table_name)
    )


def _index_exists(
    inspector: sa.Inspector,
    table_name: str,
    index_name: str,
) -> bool:
    return any(
        index["name"] == index_name for index in inspector.get_indexes(table_name)
    )


def _validate_no_orphan_user_refs(table_name: str, column_name: str) -> None:
    bind = op.get_bind()
    orphans = (
        bind.execute(
            sa.text(
                f"""
            SELECT DISTINCT CAST("{column_name}" AS TEXT)
            FROM "{table_name}"
            WHERE "{column_name}" IS NOT NULL
              AND CAST("{column_name}" AS TEXT) NOT IN (SELECT id FROM users)
            LIMIT 5
            """
            )
        )
        .scalars()
        .all()
    )

    if orphans:
        orphan_values = ", ".join(str(value) for value in orphans)
        raise RuntimeError(
            f"Cannot add foreign key for {table_name}.{column_name}. "
            f"Found orphan values: {orphan_values}"
        )


def _validate_no_duplicate_pairs() -> None:
    bind = op.get_bind()
    duplicates = bind.execute(
        sa.text(
            """
            SELECT teacher_id, student_id
            FROM teachers_students
            GROUP BY teacher_id, student_id
            HAVING COUNT(*) > 1
            LIMIT 5
            """
        )
    ).all()

    if duplicates:
        duplicate_values = ", ".join(
            f"({teacher}, {student})" for teacher, student in duplicates
        )
        raise RuntimeError(
            "Cannot add unique teacher/student constraint. "
            f"Duplicate pairs found: {duplicate_values}"
        )


def _validate_no_duplicate_homework_links() -> None:
    bind = op.get_bind()
    duplicates = (
        bind.execute(
            sa.text(
                """
            SELECT homework_id
            FROM lessons
            WHERE homework_id IS NOT NULL
            GROUP BY homework_id
            HAVING COUNT(*) > 1
            LIMIT 5
            """
            )
        )
        .scalars()
        .all()
    )

    if duplicates:
        duplicate_values = ", ".join(str(value) for value in duplicates)
        raise RuntimeError(
            "Cannot enforce one-to-one lesson/homework relation. "
            f"Duplicate homework_id values found: {duplicate_values}"
        )


def _alter_column_to_string(
    inspector: sa.Inspector,
    table_name: str,
    column_name: str,
) -> None:
    if _is_string_column(inspector, table_name, column_name):
        return

    existing_type = _column_type(inspector, table_name, column_name)
    alter_kwargs = {}
    if op.get_bind().dialect.name == "postgresql":
        alter_kwargs["postgresql_using"] = f'"{column_name}"::text'

    with op.batch_alter_table(table_name) as batch_op:
        batch_op.alter_column(
            column_name,
            existing_type=existing_type,
            type_=sa.String(),
            **alter_kwargs,
        )


def _ensure_teachers_students_schema() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "teachers_students"):
        return

    _validate_no_orphan_user_refs("teachers_students", "teacher_id")
    _validate_no_orphan_user_refs("teachers_students", "student_id")
    _validate_no_duplicate_pairs()

    _alter_column_to_string(inspector, "teachers_students", "teacher_id")
    inspector = sa.inspect(bind)
    _alter_column_to_string(inspector, "teachers_students", "student_id")
    inspector = sa.inspect(bind)

    if _foreign_key(inspector, "teachers_students", ["teacher_id"], "users") is None:
        with op.batch_alter_table("teachers_students") as batch_op:
            batch_op.create_foreign_key(
                TEACHERS_STUDENTS_TEACHER_FK,
                "users",
                ["teacher_id"],
                ["id"],
                ondelete="CASCADE",
            )

    inspector = sa.inspect(bind)
    if _foreign_key(inspector, "teachers_students", ["student_id"], "users") is None:
        with op.batch_alter_table("teachers_students") as batch_op:
            batch_op.create_foreign_key(
                TEACHERS_STUDENTS_STUDENT_FK,
                "users",
                ["student_id"],
                ["id"],
                ondelete="CASCADE",
            )

    inspector = sa.inspect(bind)
    if not _unique_constraint_exists(
        inspector,
        "teachers_students",
        TEACHERS_STUDENTS_UNIQUE,
    ):
        with op.batch_alter_table("teachers_students") as batch_op:
            batch_op.create_unique_constraint(
                TEACHERS_STUDENTS_UNIQUE,
                ["teacher_id", "student_id"],
            )

    inspector = sa.inspect(bind)
    if not _index_exists(
        inspector,
        "teachers_students",
        TEACHERS_STUDENTS_TEACHER_INDEX,
    ):
        op.create_index(
            TEACHERS_STUDENTS_TEACHER_INDEX,
            "teachers_students",
            ["teacher_id"],
        )

    inspector = sa.inspect(bind)
    if not _index_exists(
        inspector,
        "teachers_students",
        TEACHERS_STUDENTS_STUDENT_INDEX,
    ):
        op.create_index(
            TEACHERS_STUDENTS_STUDENT_INDEX,
            "teachers_students",
            ["student_id"],
        )


def _ensure_lessons_schema() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "lessons"):
        return

    _validate_no_orphan_user_refs("lessons", "teacher_id")
    _validate_no_orphan_user_refs("lessons", "student_id")
    _validate_no_duplicate_homework_links()

    if not _is_string_column(inspector, "lessons", "teacher_id"):
        _alter_column_to_string(inspector, "lessons", "teacher_id")
        inspector = sa.inspect(bind)

    if not _is_string_column(inspector, "lessons", "student_id"):
        _alter_column_to_string(inspector, "lessons", "student_id")
        inspector = sa.inspect(bind)

    if _foreign_key(inspector, "lessons", ["teacher_id"], "users") is None:
        with op.batch_alter_table("lessons") as batch_op:
            batch_op.create_foreign_key(
                LESSON_TEACHER_FK,
                "users",
                ["teacher_id"],
                ["id"],
                ondelete="RESTRICT",
            )

    inspector = sa.inspect(bind)
    if _foreign_key(inspector, "lessons", ["student_id"], "users") is None:
        with op.batch_alter_table("lessons") as batch_op:
            batch_op.create_foreign_key(
                LESSON_STUDENT_FK,
                "users",
                ["student_id"],
                ["id"],
                ondelete="RESTRICT",
            )

    inspector = sa.inspect(bind)
    homework_fk = _foreign_key(inspector, "lessons", ["homework_id"], "homeworks")
    homework_fk_ondelete = (homework_fk or {}).get("options", {}).get("ondelete")
    if homework_fk is not None and homework_fk_ondelete != "SET NULL":
        with op.batch_alter_table("lessons") as batch_op:
            batch_op.drop_constraint(homework_fk["name"], type_="foreignkey")
        inspector = sa.inspect(bind)
        homework_fk = None

    if homework_fk is None:
        with op.batch_alter_table("lessons") as batch_op:
            batch_op.create_foreign_key(
                LESSON_HOMEWORK_FK,
                "homeworks",
                ["homework_id"],
                ["id"],
                ondelete="SET NULL",
            )

    inspector = sa.inspect(bind)
    if not _unique_constraint_exists(inspector, "lessons", LESSON_HOMEWORK_UNIQUE):
        with op.batch_alter_table("lessons") as batch_op:
            batch_op.create_unique_constraint(
                LESSON_HOMEWORK_UNIQUE,
                ["homework_id"],
            )

    inspector = sa.inspect(bind)
    if not _index_exists(inspector, "lessons", LESSON_TEACHER_TIME_INDEX):
        op.create_index(
            LESSON_TEACHER_TIME_INDEX,
            "lessons",
            ["teacher_id", "start_time"],
        )

    inspector = sa.inspect(bind)
    if not _index_exists(inspector, "lessons", LESSON_STUDENT_TIME_INDEX):
        op.create_index(
            LESSON_STUDENT_TIME_INDEX,
            "lessons",
            ["student_id", "start_time"],
        )


def upgrade() -> None:
    _ensure_teachers_students_schema()
    _ensure_lessons_schema()


def downgrade() -> None:
    raise NotImplementedError(
        "Downgrade is not supported for relationship-alignment migration."
    )
