from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.constants import LessonStatuses, Roles
from src.routers.Homework.schemas import HomeworkCreateSchema, HomeworkUpdateSchema
from src.routers.Lessons.schemas import LessonCreateSchema, LessonUpdateSchema
from src.routers.Users.schemas import UserGetSchema


def test_lesson_create_schema_rejects_invalid_time_range():
    with pytest.raises(ValidationError, match="start_time must be before end_time"):
        LessonCreateSchema(
            start_time="2026-03-29T11:00:00Z",
            end_time="2026-03-29T10:00:00Z",
            student_id="student-1",
        )


def test_lesson_create_schema_normalizes_datetimes_and_defaults_status():
    lesson = LessonCreateSchema(
        start_time="2026-03-29T10:00:00+03:00",
        end_time="2026-03-29T11:00:00+03:00",
        student_id="  student-1  ",
        theme="  Math  ",
        lesson_description="  Algebra  ",
    )

    assert lesson.start_time == datetime(2026, 3, 29, 7, 0, tzinfo=UTC)
    assert lesson.end_time == datetime(2026, 3, 29, 8, 0, tzinfo=UTC)
    assert lesson.student_id == "student-1"
    assert lesson.theme == "Math"
    assert lesson.lesson_description == "Algebra"
    assert lesson.status == LessonStatuses.ACTIVE


def test_lesson_update_schema_requires_mutable_fields():
    with pytest.raises(
        ValidationError, match="At least one lesson field must be provided"
    ):
        LessonUpdateSchema()


def test_homework_create_schema_requires_lesson_id():
    with pytest.raises(ValidationError, match="Field required"):
        HomeworkCreateSchema(name="Homework 1")


def test_homework_update_schema_rejects_blank_file_references():
    with pytest.raises(ValidationError, match="File references must not be blank"):
        HomeworkUpdateSchema(sent_files=["answer.pdf", "   "])


def test_user_get_schema_normalizes_role_and_datetimes():
    user = UserGetSchema(
        id="user-1",
        name="  John  ",
        surname="  Doe  ",
        email="john@example.com",
        role=" teacher ",
        updated_at="2026-03-29T10:00:00+03:00",
        created_at="2026-03-29T09:00:00",
    )

    assert user.name == "John"
    assert user.surname == "Doe"
    assert user.role == Roles.TEACHER
    assert user.updated_at == datetime(2026, 3, 29, 7, 0, tzinfo=UTC)
    assert user.created_at == datetime(2026, 3, 29, 9, 0, tzinfo=UTC)
