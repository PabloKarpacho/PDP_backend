from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from src.constants import LessonStatuses, Roles
from src.services import lessons as lessons_service
from src.services.exceptions import NotFoundError, ValidationError


class FakeAsyncSession:
    pass


def build_user(**overrides):
    payload = {"id": "teacher-1", "role": Roles.TEACHER}
    payload.update(overrides)
    return SimpleNamespace(**payload)


def build_lesson(**overrides):
    now = datetime.now()
    payload = {
        "id": 1,
        "start_time": now,
        "end_time": now + timedelta(hours=1),
        "theme": "Math",
        "lesson_description": "Algebra",
        "teacher_id": "teacher-1",
        "student_id": "student-1",
        "status": LessonStatuses.ACTIVE,
        "homework_id": None,
        "is_deleted": False,
        "updated_at": now,
        "created_at": now,
        "homework": None,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


@pytest.mark.asyncio
async def test_list_lessons_for_student_uses_student_visibility(monkeypatch):
    captured = {}
    lesson = build_lesson()

    async def fake_list_lessons(db, **filters):
        captured["db"] = db
        captured["filters"] = filters
        return [lesson]

    monkeypatch.setattr(lessons_service, "list_lessons_records", fake_list_lessons)

    db = FakeAsyncSession()
    user = build_user(id="student-1", role=Roles.STUDENT)
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=1)

    result = await lessons_service.list_lessons_for_user(
        db=db,
        user=user,
        start_time=start_time,
        end_time=end_time,
    )

    assert [item.id for item in result] == [1]
    assert captured["db"] is db
    assert captured["filters"] == {
        "student_id": "student-1",
        "start_time": start_time,
        "end_time": end_time,
    }


@pytest.mark.asyncio
async def test_list_lessons_for_unknown_role_returns_empty_list():
    result = await lessons_service.list_lessons_for_user(
        db=FakeAsyncSession(),
        user=build_user(role="Admin"),
    )

    assert result == []


@pytest.mark.asyncio
async def test_update_lesson_for_teacher_raises_not_found(monkeypatch):
    async def fake_get_lesson(db, *, lesson_id, teacher_id):
        return None

    async def fake_update_lesson(db, *, lesson_id, teacher_id, **update_data):
        return None

    monkeypatch.setattr(lessons_service, "get_lesson_record", fake_get_lesson)
    monkeypatch.setattr(lessons_service, "update_lesson_record", fake_update_lesson)

    with pytest.raises(NotFoundError, match="Lesson not found"):
        await lessons_service.update_lesson_for_teacher(
            db=FakeAsyncSession(),
            lesson_id=42,
            user=build_user(),
            lesson=SimpleNamespace(
                model_dump=lambda **kwargs: {
                    "theme": "Geometry",
                    "teacher_id": "ignored",
                }
            ),
        )


@pytest.mark.asyncio
async def test_create_lesson_for_teacher_uses_current_teacher_id(monkeypatch):
    captured = {}
    created_lesson = build_lesson(teacher_id="teacher-1")

    async def fake_create_lesson(db, **payload):
        captured["db"] = db
        captured["payload"] = payload
        return created_lesson

    monkeypatch.setattr(lessons_service, "create_lesson_record", fake_create_lesson)

    lesson = SimpleNamespace(
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(hours=1),
        theme="Math",
        lesson_description="Algebra",
        student_id="student-1",
        status=LessonStatuses.ACTIVE,
    )
    db = FakeAsyncSession()

    result = await lessons_service.create_lesson_for_teacher(
        db=db,
        user=build_user(),
        lesson=lesson,
    )

    assert result.teacher_id == "teacher-1"
    assert captured["db"] is db
    assert captured["payload"]["teacher_id"] == "teacher-1"
    assert captured["payload"]["student_id"] == "student-1"


@pytest.mark.asyncio
async def test_update_lesson_for_teacher_rejects_invalid_status_transition(monkeypatch):
    async def fake_get_lesson(db, *, lesson_id, teacher_id):
        return build_lesson(status=LessonStatuses.PASSED)

    async def fake_update_lesson(db, *, lesson_id, teacher_id, **update_data):
        raise AssertionError("Update should not be called for invalid transition")

    monkeypatch.setattr(lessons_service, "get_lesson_record", fake_get_lesson)
    monkeypatch.setattr(lessons_service, "update_lesson_record", fake_update_lesson)

    with pytest.raises(ValidationError, match="Invalid lesson status transition"):
        await lessons_service.update_lesson_for_teacher(
            db=FakeAsyncSession(),
            lesson_id=42,
            user=build_user(),
            lesson=SimpleNamespace(
                model_dump=lambda **kwargs: {"status": LessonStatuses.ACTIVE}
            ),
        )


@pytest.mark.asyncio
async def test_update_lesson_for_teacher_rejects_invalid_resulting_time_range(
    monkeypatch,
):
    async def fake_get_lesson(db, *, lesson_id, teacher_id):
        return build_lesson(
            start_time=datetime(2026, 3, 29, 10, 0),
            end_time=datetime(2026, 3, 29, 11, 0),
        )

    async def fake_update_lesson(db, *, lesson_id, teacher_id, **update_data):
        raise AssertionError("Update should not be called for invalid time range")

    monkeypatch.setattr(lessons_service, "get_lesson_record", fake_get_lesson)
    monkeypatch.setattr(lessons_service, "update_lesson_record", fake_update_lesson)

    with pytest.raises(ValidationError, match="start_time must be before end_time"):
        await lessons_service.update_lesson_for_teacher(
            db=FakeAsyncSession(),
            lesson_id=42,
            user=build_user(),
            lesson=SimpleNamespace(
                model_dump=lambda **kwargs: {"end_time": datetime(2026, 3, 29, 9, 0)}
            ),
        )
