from datetime import datetime, timedelta
from types import SimpleNamespace
import importlib

import pytest

from src.constants import Roles
from src.routers.Homework.schemas import HomeworkCreateSchema, HomeworkUpdateSchema


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
        "answer": None,
        "sent_files": None,
        "deadline": now + timedelta(days=1),
        "lesson_id": 5,
        "is_deleted": False,
        "updated_at": now,
        "created_at": now,
    }


@pytest.mark.asyncio
async def test_get_homeworks_for_student_passes_student_filter(monkeypatch):
    captured = {}
    homework = build_homework_dao()

    async def fake_list_homeworks(db, **filters):
        captured["db"] = db
        captured["filters"] = filters
        return [homework]

    monkeypatch.setattr(homework_router_module, "list_homeworks", fake_list_homeworks)

    user = SimpleNamespace(id="student-1", role=Roles.STUDENT)
    db = object()

    result = await homework_router_module.get_homeworks(
        user=user,
        db=db,
        lesson_id=5,
    )

    assert len(result) == 1
    assert result[0].lesson_id == 5
    assert captured["db"] is db
    assert captured["filters"]["student_id"] == "student-1"
    assert captured["filters"]["lesson_id"] == 5
    assert "teacher_id" not in captured["filters"]


@pytest.mark.asyncio
async def test_get_homework_for_teacher_passes_teacher_filter(monkeypatch):
    captured = {}
    homework = build_homework_dao()

    async def fake_get_homework(db, *, homework_id, load_lesson, **filters):
        captured["db"] = db
        captured["homework_id"] = homework_id
        captured["load_lesson"] = load_lesson
        captured["filters"] = filters
        return homework

    monkeypatch.setattr(
        homework_router_module, "get_homework_record", fake_get_homework
    )

    user = SimpleNamespace(id="teacher-1", role=Roles.TEACHER)
    db = object()

    result = await homework_router_module.get_homework(
        homework_id=7,
        user=user,
        db=db,
    )

    assert result.id == 1
    assert captured["db"] is db
    assert captured["homework_id"] == 7
    assert captured["load_lesson"] is True
    assert captured["filters"]["teacher_id"] == "teacher-1"


@pytest.mark.asyncio
async def test_create_homework_for_teacher_uses_current_teacher_id(monkeypatch):
    captured = {}
    homework = build_homework_dao()

    async def fake_create_homework(db, **payload):
        captured["db"] = db
        captured["payload"] = payload
        return homework

    monkeypatch.setattr(
        homework_router_module, "create_homework_record", fake_create_homework
    )

    user = SimpleNamespace(id="teacher-1", role=Roles.TEACHER)
    db = object()
    homework_payload = HomeworkCreateSchema(**build_homework_payload())

    result = await homework_router_module.create_homework(
        homework=homework_payload,
        user=user,
        db=db,
    )

    assert result.lesson_id == 5
    assert captured["db"] is db
    assert captured["payload"]["teacher_id"] == "teacher-1"
    assert captured["payload"]["lesson_id"] == 5


@pytest.mark.asyncio
async def test_update_homework_for_student_passes_only_student_fields(monkeypatch):
    captured = {}
    homework = build_homework_dao(answer="done", sent_files=["answer.pdf"])

    async def fake_update_homework(db, *, homework_id, student_id, **payload):
        captured["db"] = db
        captured["homework_id"] = homework_id
        captured["student_id"] = student_id
        captured["payload"] = payload
        return homework

    monkeypatch.setattr(
        homework_router_module, "update_homework_record", fake_update_homework
    )

    user = SimpleNamespace(id="student-1", role=Roles.STUDENT)
    db = object()
    homework_payload = HomeworkUpdateSchema(
        **{
            **build_homework_payload(),
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

    assert result.answer == "done"
    assert captured["db"] is db
    assert captured["homework_id"] == 9
    assert captured["student_id"] == "student-1"
    assert captured["payload"] == {"answer": "done", "sent_files": ["answer.pdf"]}


@pytest.mark.asyncio
async def test_delete_homework_for_teacher_passes_teacher_filter(monkeypatch):
    captured = {}
    homework = build_homework_dao(id=7)

    async def fake_soft_delete_homework(db, *, homework_id, teacher_id):
        captured["db"] = db
        captured["homework_id"] = homework_id
        captured["teacher_id"] = teacher_id
        return homework

    monkeypatch.setattr(
        homework_router_module, "soft_delete_homework", fake_soft_delete_homework
    )

    user = SimpleNamespace(id="teacher-1", role=Roles.TEACHER)
    db = object()

    result = await homework_router_module.delete_homework(
        homework_id=7,
        user=user,
        db=db,
    )

    assert result == 7
    assert captured["db"] is db
    assert captured["homework_id"] == 7
    assert captured["teacher_id"] == "teacher-1"
