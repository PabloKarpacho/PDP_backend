from datetime import datetime, timedelta
from types import SimpleNamespace
import importlib

import pytest

from src.constants import LessonStatuses, Roles
from src.routers.Lessons.schemas import LessonCreateSchema, LessonUpdateSchema


lessons_router_module = importlib.import_module("src.routers.Lessons.router")


def build_lesson_dao(**overrides):
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


def build_lesson_payload():
    now = datetime.now()
    return {
        "start_time": now,
        "end_time": now + timedelta(hours=1),
        "theme": "Math",
        "lesson_description": "Algebra",
        "teacher_id": "body-teacher-id",
        "student_id": "student-1",
        "status": LessonStatuses.ACTIVE,
        "homework_id": None,
        "is_deleted": False,
        "updated_at": now,
        "created_at": now,
    }


@pytest.mark.asyncio
async def test_get_lessons_for_student_passes_student_filter(monkeypatch):
    captured = {}
    lesson = build_lesson_dao()

    async def fake_list_lessons(db, **filters):
        captured["db"] = db
        captured["filters"] = filters
        return [lesson]

    monkeypatch.setattr(lessons_router_module, "list_lessons", fake_list_lessons)

    user = SimpleNamespace(id="student-1", role=Roles.STUDENT)
    db = object()
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=1)

    result = await lessons_router_module.get_lessons(
        user=user,
        db=db,
        start_time=start_time,
        end_time=end_time,
    )

    assert len(result) == 1
    assert result[0].student_id == "student-1"
    assert captured["db"] is db
    assert captured["filters"]["student_id"] == "student-1"
    assert captured["filters"]["start_time"] == start_time
    assert captured["filters"]["end_time"] == end_time
    assert "teacher_id" not in captured["filters"]


@pytest.mark.asyncio
async def test_get_lessons_returns_only_lessons_in_requested_time_range(monkeypatch):
    requested_start = datetime(2026, 3, 29, 9, 0)
    requested_end = datetime(2026, 3, 29, 12, 0)

    lesson_before_range = build_lesson_dao(
        id=1,
        start_time=datetime(2026, 3, 29, 8, 0),
        end_time=datetime(2026, 3, 29, 8, 45),
    )
    lesson_in_range = build_lesson_dao(
        id=2,
        start_time=datetime(2026, 3, 29, 10, 0),
        end_time=datetime(2026, 3, 29, 11, 0),
    )
    lesson_after_range = build_lesson_dao(
        id=3,
        start_time=datetime(2026, 3, 29, 12, 30),
        end_time=datetime(2026, 3, 29, 13, 30),
    )

    async def fake_list_lessons(db, **filters):
        lessons = [lesson_before_range, lesson_in_range, lesson_after_range]
        return [
            lesson
            for lesson in lessons
            if lesson.start_time >= filters["start_time"]
            and lesson.end_time <= filters["end_time"]
        ]

    monkeypatch.setattr(lessons_router_module, "list_lessons", fake_list_lessons)

    user = SimpleNamespace(id="student-1", role=Roles.STUDENT)

    result = await lessons_router_module.get_lessons(
        user=user,
        db=object(),
        start_time=requested_start,
        end_time=requested_end,
    )

    assert [lesson.id for lesson in result] == [2]
    assert result[0].start_time == datetime(2026, 3, 29, 10, 0)
    assert result[0].end_time == datetime(2026, 3, 29, 11, 0)


@pytest.mark.asyncio
async def test_create_lesson_for_teacher_uses_current_teacher_id(monkeypatch):
    captured = {}
    lesson = build_lesson_dao(teacher_id="teacher-1")

    async def fake_create_lesson(db, **payload):
        captured["db"] = db
        captured["payload"] = payload
        return lesson

    monkeypatch.setattr(lessons_router_module, "create_lesson_record", fake_create_lesson)

    user = SimpleNamespace(id="teacher-1", role=Roles.TEACHER)
    db = object()
    lesson_payload = LessonCreateSchema(**build_lesson_payload())

    result = await lessons_router_module.create_lesson(
        lesson=lesson_payload,
        user=user,
        db=db,
    )

    assert result.teacher_id == "teacher-1"
    assert captured["db"] is db
    assert captured["payload"]["teacher_id"] == "teacher-1"
    assert captured["payload"]["student_id"] == "student-1"


@pytest.mark.asyncio
async def test_update_lesson_for_teacher_passes_teacher_filter(monkeypatch):
    captured = {}
    lesson = build_lesson_dao(theme="Geometry")

    async def fake_update_lesson(db, *, lesson_id, teacher_id, **payload):
        captured["db"] = db
        captured["lesson_id"] = lesson_id
        captured["teacher_id"] = teacher_id
        captured["payload"] = payload
        return lesson

    monkeypatch.setattr(lessons_router_module, "update_lesson_record", fake_update_lesson)

    user = SimpleNamespace(id="teacher-1", role=Roles.TEACHER)
    db = object()
    lesson_payload = LessonUpdateSchema(**build_lesson_payload())

    result = await lessons_router_module.update_lesson(
        lesson=lesson_payload,
        lesson_id=42,
        user=user,
        db=db,
    )

    assert result.id == 1
    assert captured["db"] is db
    assert captured["lesson_id"] == 42
    assert captured["teacher_id"] == "teacher-1"
    assert captured["payload"]["theme"] == "Math"


@pytest.mark.asyncio
async def test_delete_lesson_for_teacher_passes_teacher_filter(monkeypatch):
    captured = {}
    lesson = build_lesson_dao(id=7)

    async def fake_soft_delete_lesson(db, *, lesson_id, teacher_id):
        captured["db"] = db
        captured["lesson_id"] = lesson_id
        captured["teacher_id"] = teacher_id
        return lesson

    monkeypatch.setattr(lessons_router_module, "soft_delete_lesson", fake_soft_delete_lesson)

    user = SimpleNamespace(id="teacher-1", role=Roles.TEACHER)
    db = object()

    result = await lessons_router_module.delete_lesson(
        lesson_id=7,
        user=user,
        db=db,
    )

    assert result == 7
    assert captured["db"] is db
    assert captured["lesson_id"] == 7
    assert captured["teacher_id"] == "teacher-1"
