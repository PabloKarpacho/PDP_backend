from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from src.constants import Roles
from src.services import homework as homework_service
from src.services.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)


class FakeAsyncSession:
    pass


def build_user(**overrides):
    payload = {"id": "teacher-1", "role": Roles.TEACHER}
    payload.update(overrides)
    return SimpleNamespace(**payload)


def build_homework(**overrides):
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


@pytest.mark.asyncio
async def test_get_homework_for_unknown_role_raises_forbidden():
    with pytest.raises(ForbiddenError, match="Forbidden"):
        await homework_service.get_homework_for_user(
            db=FakeAsyncSession(),
            homework_id=5,
            user=build_user(role="Admin"),
        )


@pytest.mark.asyncio
async def test_create_homework_for_teacher_requires_lesson_id():
    with pytest.raises(ValidationError, match="lesson_id is required"):
        await homework_service.create_homework_for_teacher(
            db=FakeAsyncSession(),
            user=build_user(),
            homework=SimpleNamespace(
                lesson_id=None,
                name="Homework 1",
                description=None,
                files_urls=None,
                answer=None,
                sent_files=None,
                deadline=None,
            ),
        )


@pytest.mark.asyncio
async def test_create_homework_for_teacher_maps_conflict(monkeypatch):
    async def fake_get_lesson(db, *, lesson_id, teacher_id):
        return SimpleNamespace(
            id=lesson_id,
            teacher_id=teacher_id,
            student_id="student-1",
        )

    async def fake_ensure_active_relation(*, db, teacher_id, student_id):
        return None

    async def fake_create_homework(db, **payload):
        raise ValueError("Lesson already has homework")

    monkeypatch.setattr(homework_service, "get_lesson_record", fake_get_lesson)
    monkeypatch.setattr(
        homework_service, "ensure_active_relation", fake_ensure_active_relation
    )
    monkeypatch.setattr(
        homework_service, "create_homework_record", fake_create_homework
    )

    with pytest.raises(ConflictError, match="Lesson already has homework"):
        await homework_service.create_homework_for_teacher(
            db=FakeAsyncSession(),
            user=build_user(),
            homework=SimpleNamespace(
                lesson_id=5,
                name="Homework 1",
                description=None,
                files_urls=None,
                answer=None,
                sent_files=None,
                deadline=None,
            ),
        )


@pytest.mark.asyncio
async def test_create_homework_for_teacher_requires_active_relation(monkeypatch):
    async def fake_get_lesson(db, *, lesson_id, teacher_id):
        return SimpleNamespace(
            id=lesson_id,
            teacher_id=teacher_id,
            student_id="student-1",
        )

    async def fake_ensure_active_relation(*, db, teacher_id, student_id):
        raise ForbiddenError("Active teacher-student relation is required")

    async def fake_create_homework(db, **payload):
        raise AssertionError("Homework must not be created without active relation")

    monkeypatch.setattr(homework_service, "get_lesson_record", fake_get_lesson)
    monkeypatch.setattr(
        homework_service,
        "ensure_active_relation",
        fake_ensure_active_relation,
    )
    monkeypatch.setattr(
        homework_service,
        "create_homework_record",
        fake_create_homework,
    )

    with pytest.raises(
        ForbiddenError,
        match="Active teacher-student relation is required",
    ):
        await homework_service.create_homework_for_teacher(
            db=FakeAsyncSession(),
            user=build_user(id="teacher-1", role=Roles.TEACHER),
            homework=SimpleNamespace(
                lesson_id=5,
                name="Homework 1",
                description=None,
                files_urls=None,
                deadline=None,
            ),
        )


@pytest.mark.asyncio
async def test_update_homework_for_student_only_updates_student_fields(monkeypatch):
    captured = {}
    homework = build_homework(answer="done", sent_files=["answer.pdf"])

    async def fake_update_homework(db, *, homework_id, student_id, **payload):
        captured["db"] = db
        captured["homework_id"] = homework_id
        captured["student_id"] = student_id
        captured["payload"] = payload
        return homework

    monkeypatch.setattr(
        homework_service, "update_homework_record", fake_update_homework
    )

    result = await homework_service.update_homework_for_user(
        db=FakeAsyncSession(),
        homework_id=9,
        user=build_user(id="student-1", role=Roles.STUDENT),
        homework=SimpleNamespace(
            model_dump=lambda **kwargs: {
                "description": "teacher-only field",
                "answer": "done",
                "sent_files": ["answer.pdf"],
            }
        ),
    )

    assert result.answer == "done"
    assert captured["homework_id"] == 9
    assert captured["student_id"] == "student-1"
    assert captured["payload"] == {"answer": "done", "sent_files": ["answer.pdf"]}


@pytest.mark.asyncio
async def test_delete_homework_for_teacher_raises_not_found(monkeypatch):
    async def fake_delete_homework(db, *, homework_id, teacher_id):
        return None

    monkeypatch.setattr(
        homework_service, "soft_delete_homework_record", fake_delete_homework
    )

    with pytest.raises(NotFoundError, match="Homework not found"):
        await homework_service.delete_homework_for_teacher(
            db=FakeAsyncSession(),
            homework_id=7,
            user=build_user(),
        )
