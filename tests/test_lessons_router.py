from datetime import datetime, timedelta
from types import SimpleNamespace
import importlib

import pytest
from fastapi import HTTPException

from src.constants import LessonStatuses, Roles
from src.routers.Lessons.schemas import LessonCreateSchema, LessonUpdateSchema
from src.services.exceptions import ForbiddenError, NotFoundError


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
        "student_id": "student-1",
        "status": LessonStatuses.ACTIVE,
    }


@pytest.mark.asyncio
async def test_get_lessons_for_student_passes_student_filter(monkeypatch):
    captured = {}
    lesson = SimpleNamespace(id=1, student_id="student-1")

    async def fake_list_lessons_for_user(*, db, user, start_time, end_time):
        captured["db"] = db
        captured["user"] = user
        captured["start_time"] = start_time
        captured["end_time"] = end_time
        return [lesson]

    monkeypatch.setattr(
        lessons_router_module,
        "list_lessons_for_user",
        fake_list_lessons_for_user,
    )

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

    assert result.success is True
    assert result.error is None
    assert result.meta.pagination is None
    assert len(result.data) == 1
    assert result.data[0].student_id == "student-1"
    assert captured["db"] is db
    assert captured["user"] is user
    assert captured["start_time"] == start_time
    assert captured["end_time"] == end_time


@pytest.mark.asyncio
async def test_get_lessons_returns_only_lessons_in_requested_time_range(monkeypatch):
    requested_start = datetime(2026, 3, 29, 9, 0)
    requested_end = datetime(2026, 3, 29, 12, 0)
    lesson_in_range = SimpleNamespace(
        id=2,
        start_time=datetime(2026, 3, 29, 10, 0),
        end_time=datetime(2026, 3, 29, 11, 0),
    )

    async def fake_list_lessons_for_user(*, db, user, start_time, end_time):
        assert start_time == requested_start
        assert end_time == requested_end
        return [lesson_in_range]

    monkeypatch.setattr(
        lessons_router_module,
        "list_lessons_for_user",
        fake_list_lessons_for_user,
    )

    user = SimpleNamespace(id="student-1", role=Roles.STUDENT)

    result = await lessons_router_module.get_lessons(
        user=user,
        db=object(),
        start_time=requested_start,
        end_time=requested_end,
    )

    assert result.success is True
    assert [lesson.id for lesson in result.data] == [2]
    assert result.data[0].start_time == datetime(2026, 3, 29, 10, 0)
    assert result.data[0].end_time == datetime(2026, 3, 29, 11, 0)


@pytest.mark.asyncio
async def test_create_lesson_for_teacher_uses_current_teacher_id(monkeypatch):
    captured = {}
    service_result = build_lesson_dao(teacher_id="teacher-1")

    async def fake_create_lesson_for_teacher(*, db, user, lesson):
        captured["db"] = db
        captured["user"] = user
        captured["lesson"] = lesson
        return service_result

    monkeypatch.setattr(
        lessons_router_module,
        "create_lesson_for_teacher",
        fake_create_lesson_for_teacher,
    )

    user = SimpleNamespace(id="teacher-1", role=Roles.TEACHER)
    db = object()
    lesson_payload = LessonCreateSchema(**build_lesson_payload())

    result = await lessons_router_module.create_lesson(
        lesson=lesson_payload,
        user=user,
        db=db,
    )

    assert result.success is True
    assert result.error is None
    assert result.data.teacher_id == "teacher-1"
    assert captured["db"] is db
    assert captured["user"] is user
    assert captured["lesson"] is lesson_payload


@pytest.mark.asyncio
async def test_create_lesson_maps_forbidden_error_to_403(monkeypatch):
    async def fake_create_lesson_for_teacher(*, db, user, lesson):
        raise ForbiddenError("Active teacher-student relation is required")

    monkeypatch.setattr(
        lessons_router_module,
        "create_lesson_for_teacher",
        fake_create_lesson_for_teacher,
    )

    with pytest.raises(HTTPException) as exc_info:
        await lessons_router_module.create_lesson(
            lesson=LessonCreateSchema(**build_lesson_payload()),
            user=SimpleNamespace(id="teacher-1", role=Roles.TEACHER),
            db=object(),
        )

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_update_lesson_for_teacher_passes_request_to_service(monkeypatch):
    captured = {}
    service_result = build_lesson_dao(theme="Geometry")

    async def fake_update_lesson_for_teacher(*, db, lesson_id, user, lesson):
        captured["db"] = db
        captured["lesson_id"] = lesson_id
        captured["user"] = user
        captured["lesson"] = lesson
        return service_result

    monkeypatch.setattr(
        lessons_router_module,
        "update_lesson_for_teacher",
        fake_update_lesson_for_teacher,
    )

    user = SimpleNamespace(id="teacher-1", role=Roles.TEACHER)
    db = object()
    lesson_payload = LessonUpdateSchema(**build_lesson_payload())

    result = await lessons_router_module.update_lesson(
        lesson=lesson_payload,
        lesson_id=42,
        user=user,
        db=db,
    )

    assert result.success is True
    assert result.error is None
    assert result.data.id == 1
    assert captured["db"] is db
    assert captured["lesson_id"] == 42
    assert captured["user"] is user
    assert captured["lesson"] is lesson_payload


@pytest.mark.asyncio
async def test_update_lesson_returns_404_when_service_raises_not_found(monkeypatch):
    async def fake_update_lesson_for_teacher(*, db, lesson_id, user, lesson):
        raise NotFoundError("Lesson not found")

    monkeypatch.setattr(
        lessons_router_module,
        "update_lesson_for_teacher",
        fake_update_lesson_for_teacher,
    )

    with pytest.raises(HTTPException) as exc_info:
        await lessons_router_module.update_lesson(
            lesson=LessonUpdateSchema(**build_lesson_payload()),
            lesson_id=42,
            user=SimpleNamespace(id="teacher-1", role=Roles.TEACHER),
            db=object(),
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_lesson_for_teacher_passes_request_to_service(monkeypatch):
    captured = {}

    async def fake_delete_lesson_for_teacher(*, db, lesson_id, user):
        captured["db"] = db
        captured["lesson_id"] = lesson_id
        captured["user"] = user
        return 7

    monkeypatch.setattr(
        lessons_router_module,
        "delete_lesson_for_teacher",
        fake_delete_lesson_for_teacher,
    )

    user = SimpleNamespace(id="teacher-1", role=Roles.TEACHER)
    db = object()

    result = await lessons_router_module.delete_lesson(
        lesson_id=7,
        user=user,
        db=db,
    )

    assert result.success is True
    assert result.error is None
    assert result.data == 7
    assert captured["db"] is db
    assert captured["lesson_id"] == 7
    assert captured["user"] is user
