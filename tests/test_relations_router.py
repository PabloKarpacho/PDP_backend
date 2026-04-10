from datetime import datetime, timezone
from types import SimpleNamespace
import importlib

import pytest
from fastapi import HTTPException

from src.constants import RelationStatuses, Roles
from src.services.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)


relations_router_module = importlib.import_module("src.routers.Relations.router")


def build_relation(**overrides):
    now = datetime.now(timezone.utc)
    payload = {
        "id": 1,
        "teacher_id": "teacher-1",
        "student_id": "student-1",
        "status": RelationStatuses.ACTIVE,
        "archived_at": None,
        "updated_at": now,
        "created_at": now,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


@pytest.mark.asyncio
async def test_create_relation_uses_current_teacher(monkeypatch):
    captured = {}

    async def fake_create_relation_for_teacher(*, db, user, student_id):
        captured["user"] = user
        captured["student_id"] = student_id
        return build_relation()

    monkeypatch.setattr(
        relations_router_module,
        "create_relation_for_teacher",
        fake_create_relation_for_teacher,
    )

    user = SimpleNamespace(id="teacher-1", role=Roles.TEACHER)
    result = await relations_router_module.create_relation(
        relation=SimpleNamespace(student_id="student-1"),
        user=user,
        db=object(),
    )

    assert result.success is True
    assert result.data.teacher_id == "teacher-1"
    assert captured["user"] is user
    assert captured["student_id"] == "student-1"


@pytest.mark.asyncio
async def test_create_relation_maps_validation_error(monkeypatch):
    async def fake_create_relation_for_teacher(*, db, user, student_id):
        raise ValidationError("teacher and student must be different users")

    monkeypatch.setattr(
        relations_router_module,
        "create_relation_for_teacher",
        fake_create_relation_for_teacher,
    )

    with pytest.raises(HTTPException) as exc_info:
        await relations_router_module.create_relation(
            relation=SimpleNamespace(student_id="teacher-1"),
            user=SimpleNamespace(id="teacher-1", role=Roles.TEACHER),
            db=object(),
        )

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_create_relation_maps_conflict_error(monkeypatch):
    async def fake_create_relation_for_teacher(*, db, user, student_id):
        raise ConflictError("Teacher-student relation already exists")

    monkeypatch.setattr(
        relations_router_module,
        "create_relation_for_teacher",
        fake_create_relation_for_teacher,
    )

    with pytest.raises(HTTPException) as exc_info:
        await relations_router_module.create_relation(
            relation=SimpleNamespace(student_id="student-1"),
            user=SimpleNamespace(id="teacher-1", role=Roles.TEACHER),
            db=object(),
        )

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_list_students_returns_relations(monkeypatch):
    async def fake_list_students_for_teacher(*, db, user, include_archived):
        return [build_relation()]

    monkeypatch.setattr(
        relations_router_module,
        "list_students_for_teacher",
        fake_list_students_for_teacher,
    )

    result = await relations_router_module.get_students(
        user=SimpleNamespace(id="teacher-1", role=Roles.TEACHER),
        db=object(),
        include_archived=False,
    )

    assert result.success is True
    assert [relation.student_id for relation in result.data] == ["student-1"]


@pytest.mark.asyncio
async def test_list_teachers_returns_relations(monkeypatch):
    async def fake_list_teachers_for_student(*, db, user, include_archived):
        return [build_relation()]

    monkeypatch.setattr(
        relations_router_module,
        "list_teachers_for_student",
        fake_list_teachers_for_student,
    )

    result = await relations_router_module.get_teachers(
        user=SimpleNamespace(id="student-1", role=Roles.STUDENT),
        db=object(),
        include_archived=True,
    )

    assert result.success is True
    assert [relation.teacher_id for relation in result.data] == ["teacher-1"]


@pytest.mark.asyncio
async def test_archive_relation_maps_not_found(monkeypatch):
    async def fake_archive_relation_for_user(*, db, relation_id, user):
        raise NotFoundError("Relation not found")

    monkeypatch.setattr(
        relations_router_module,
        "archive_relation_for_user",
        fake_archive_relation_for_user,
    )

    with pytest.raises(HTTPException) as exc_info:
        await relations_router_module.archive_relation(
            relation_id=1,
            user=SimpleNamespace(id="teacher-1", role=Roles.TEACHER),
            db=object(),
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_archive_relation_maps_forbidden(monkeypatch):
    async def fake_archive_relation_for_user(*, db, relation_id, user):
        raise ForbiddenError("Forbidden")

    monkeypatch.setattr(
        relations_router_module,
        "archive_relation_for_user",
        fake_archive_relation_for_user,
    )

    with pytest.raises(HTTPException) as exc_info:
        await relations_router_module.archive_relation(
            relation_id=1,
            user=SimpleNamespace(id="student-2", role=Roles.STUDENT),
            db=object(),
        )

    assert exc_info.value.status_code == 403
