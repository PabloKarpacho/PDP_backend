from datetime import datetime, timedelta
from types import SimpleNamespace
import importlib

import pytest
from fastapi import HTTPException

from src.constants import Roles
from src.routers.Homework.schemas import HomeworkCreateSchema, HomeworkUpdateSchema
from src.services.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)


homework_router_module = importlib.import_module("src.routers.Homework.router")


def build_homework_dao(**overrides):
    now = datetime.now()
    payload = {
        "id": 1,
        "name": "Homework 1",
        "description": "Solve tasks",
        "files_urls": ["task.pdf"],
        "answer": None,
        "sent_files": None,
        "deadline": now + timedelta(days=1),
        "is_deleted": False,
        "updated_at": now,
        "created_at": now,
        "lesson": SimpleNamespace(id=5, teacher_id="teacher-1", student_id="student-1"),
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def build_homework_payload():
    now = datetime.now()
    return {
        "name": "Homework 1",
        "description": "Solve tasks",
        "files_urls": ["task.pdf"],
        "deadline": now + timedelta(days=1),
        "lesson_id": 5,
    }


def build_homework_update_payload():
    now = datetime.now()
    return {
        "name": "Homework 1",
        "description": "Solve tasks",
        "files_urls": ["task.pdf"],
        "deadline": now + timedelta(days=1),
    }


@pytest.mark.asyncio
async def test_get_homeworks_for_student_passes_student_filter(monkeypatch):
    captured = {}
    homework = SimpleNamespace(id=1, lesson_id=5)

    async def fake_list_homeworks_for_user(*, db, user, lesson_id):
        captured["db"] = db
        captured["user"] = user
        captured["lesson_id"] = lesson_id
        return [homework]

    monkeypatch.setattr(
        homework_router_module,
        "list_homeworks_for_user",
        fake_list_homeworks_for_user,
    )

    user = SimpleNamespace(id="student-1", role=Roles.STUDENT)
    db = object()

    result = await homework_router_module.get_homeworks(
        user=user,
        db=db,
        lesson_id=5,
    )

    assert result.success is True
    assert result.error is None
    assert result.meta.pagination is None
    assert len(result.data) == 1
    assert result.data[0].lesson_id == 5
    assert captured["db"] is db
    assert captured["user"] is user
    assert captured["lesson_id"] == 5


@pytest.mark.asyncio
async def test_get_homework_for_teacher_uses_service(monkeypatch):
    captured = {}
    homework = build_homework_dao()

    async def fake_get_homework_for_user(*, db, homework_id, user):
        captured["db"] = db
        captured["homework_id"] = homework_id
        captured["user"] = user
        return homework

    monkeypatch.setattr(
        homework_router_module,
        "get_homework_for_user",
        fake_get_homework_for_user,
    )

    user = SimpleNamespace(id="teacher-1", role=Roles.TEACHER)
    db = object()

    result = await homework_router_module.get_homework(
        homework_id=7,
        user=user,
        db=db,
    )

    assert result.success is True
    assert result.error is None
    assert result.data.id == 1
    assert captured["db"] is db
    assert captured["homework_id"] == 7
    assert captured["user"] is user


@pytest.mark.asyncio
async def test_get_homework_returns_403_when_service_raises_forbidden(monkeypatch):
    async def fake_get_homework_for_user(*, db, homework_id, user):
        raise ForbiddenError("Forbidden")

    monkeypatch.setattr(
        homework_router_module,
        "get_homework_for_user",
        fake_get_homework_for_user,
    )

    with pytest.raises(HTTPException) as exc_info:
        await homework_router_module.get_homework(
            homework_id=7,
            user=SimpleNamespace(id="student-1", role="Admin"),
            db=object(),
        )

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_create_homework_for_teacher_uses_current_teacher_id(monkeypatch):
    captured = {}

    async def fake_create_homework_for_teacher(*, db, user, homework):
        captured["db"] = db
        captured["user"] = user
        captured["homework"] = homework
        return homework

    monkeypatch.setattr(
        homework_router_module,
        "create_homework_for_teacher",
        fake_create_homework_for_teacher,
    )

    user = SimpleNamespace(id="teacher-1", role=Roles.TEACHER)
    db = object()
    homework_payload = HomeworkCreateSchema(**build_homework_payload())

    result = await homework_router_module.create_homework(
        homework=homework_payload,
        user=user,
        db=db,
    )

    assert result.success is True
    assert result.error is None
    assert result.data.lesson_id == 5
    assert captured["db"] is db
    assert captured["user"] is user
    assert captured["homework"] is homework_payload


@pytest.mark.asyncio
async def test_create_homework_maps_validation_error_to_400(monkeypatch):
    async def fake_create_homework_for_teacher(*, db, user, homework):
        raise ValidationError("lesson_id is required")

    monkeypatch.setattr(
        homework_router_module,
        "create_homework_for_teacher",
        fake_create_homework_for_teacher,
    )

    with pytest.raises(HTTPException) as exc_info:
        await homework_router_module.create_homework(
            homework=HomeworkCreateSchema(**build_homework_payload()),
            user=SimpleNamespace(id="teacher-1", role=Roles.TEACHER),
            db=object(),
        )

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_create_homework_maps_forbidden_error_to_403(monkeypatch):
    async def fake_create_homework_for_teacher(*, db, user, homework):
        raise ForbiddenError("Active teacher-student relation is required")

    monkeypatch.setattr(
        homework_router_module,
        "create_homework_for_teacher",
        fake_create_homework_for_teacher,
    )

    with pytest.raises(HTTPException) as exc_info:
        await homework_router_module.create_homework(
            homework=HomeworkCreateSchema(**build_homework_payload()),
            user=SimpleNamespace(id="teacher-1", role=Roles.TEACHER),
            db=object(),
        )

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_create_homework_maps_conflict_error_to_409(monkeypatch):
    async def fake_create_homework_for_teacher(*, db, user, homework):
        raise ConflictError("Lesson already has homework")

    monkeypatch.setattr(
        homework_router_module,
        "create_homework_for_teacher",
        fake_create_homework_for_teacher,
    )

    with pytest.raises(HTTPException) as exc_info:
        await homework_router_module.create_homework(
            homework=HomeworkCreateSchema(**build_homework_payload()),
            user=SimpleNamespace(id="teacher-1", role=Roles.TEACHER),
            db=object(),
        )

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_update_homework_for_student_uses_service(monkeypatch):
    captured = {}

    async def fake_update_homework_for_user(*, db, homework_id, user, homework):
        captured["db"] = db
        captured["homework_id"] = homework_id
        captured["user"] = user
        captured["homework"] = homework
        return homework

    monkeypatch.setattr(
        homework_router_module,
        "update_homework_for_user",
        fake_update_homework_for_user,
    )

    user = SimpleNamespace(id="student-1", role=Roles.STUDENT)
    db = object()
    homework_payload = HomeworkUpdateSchema(
        **{
            **build_homework_update_payload(),
            "description": "teacher-only field",
            "answer": "done",
            "sent_files": ["answer.pdf"],
        }
    )

    result = await homework_router_module.update_homework(
        homework=homework_payload,
        homework_id=9,
        user=user,
        db=db,
    )

    assert result.success is True
    assert result.error is None
    assert result.data.answer == "done"
    assert captured["db"] is db
    assert captured["homework_id"] == 9
    assert captured["user"] is user
    assert captured["homework"] is homework_payload


@pytest.mark.asyncio
async def test_update_homework_maps_not_found_to_404(monkeypatch):
    async def fake_update_homework_for_user(*, db, homework_id, user, homework):
        raise NotFoundError("Homework not found")

    monkeypatch.setattr(
        homework_router_module,
        "update_homework_for_user",
        fake_update_homework_for_user,
    )

    with pytest.raises(HTTPException) as exc_info:
        await homework_router_module.update_homework(
            homework=HomeworkUpdateSchema(**build_homework_update_payload()),
            homework_id=9,
            user=SimpleNamespace(id="student-1", role=Roles.STUDENT),
            db=object(),
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_homework_for_teacher_uses_service(monkeypatch):
    captured = {}

    async def fake_delete_homework_for_teacher(*, db, homework_id, user):
        captured["db"] = db
        captured["homework_id"] = homework_id
        captured["user"] = user
        return 7

    monkeypatch.setattr(
        homework_router_module,
        "delete_homework_for_teacher",
        fake_delete_homework_for_teacher,
    )

    user = SimpleNamespace(id="teacher-1", role=Roles.TEACHER)
    db = object()

    result = await homework_router_module.delete_homework(
        homework_id=7,
        user=user,
        db=db,
    )

    assert result.success is True
    assert result.error is None
    assert result.data == 7
    assert captured["db"] is db
    assert captured["homework_id"] == 7
    assert captured["user"] is user
