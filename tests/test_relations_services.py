from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from src.constants import RelationStatuses, Roles
from src.services import relations as relations_service
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
async def test_create_relation_for_teacher_rejects_self_link():
    with pytest.raises(
        ValidationError,
        match="teacher and student must be different users",
    ):
        await relations_service.create_relation_for_teacher(
            db=FakeAsyncSession(),
            user=build_user(id="teacher-1"),
            student_id="teacher-1",
        )


@pytest.mark.asyncio
async def test_create_relation_for_teacher_rejects_duplicate_relation(monkeypatch):
    async def fake_get_relation_by_pair(db, *, teacher_id, student_id):
        return build_relation(teacher_id=teacher_id, student_id=student_id)

    monkeypatch.setattr(
        relations_service,
        "get_relation_by_pair_record",
        fake_get_relation_by_pair,
    )

    with pytest.raises(
        ConflictError,
        match="Teacher-student relation already exists",
    ):
        await relations_service.create_relation_for_teacher(
            db=FakeAsyncSession(),
            user=build_user(),
            student_id="student-1",
        )


@pytest.mark.asyncio
async def test_create_relation_for_teacher_requires_student_role(monkeypatch):
    async def fake_get_user(db, *, user_id):
        return build_user(id=user_id, role=Roles.TEACHER)

    async def fake_get_relation_by_pair(db, *, teacher_id, student_id):
        return None

    monkeypatch.setattr(relations_service, "get_user_record", fake_get_user)
    monkeypatch.setattr(
        relations_service,
        "get_relation_by_pair_record",
        fake_get_relation_by_pair,
    )

    with pytest.raises(ValidationError, match="Relation target must be a student"):
        await relations_service.create_relation_for_teacher(
            db=FakeAsyncSession(),
            user=build_user(),
            student_id="teacher-2",
        )


@pytest.mark.asyncio
async def test_create_relation_for_teacher_uses_current_teacher_id(monkeypatch):
    captured = {}

    async def fake_get_relation_by_pair(db, *, teacher_id, student_id):
        return None

    async def fake_get_user(db, *, user_id):
        return build_user(id=user_id, role=Roles.STUDENT)

    async def fake_create_relation(db, *, teacher_id, student_id, status):
        captured["teacher_id"] = teacher_id
        captured["student_id"] = student_id
        captured["status"] = status
        return build_relation(
            teacher_id=teacher_id,
            student_id=student_id,
            status=status,
        )

    monkeypatch.setattr(
        relations_service,
        "get_relation_by_pair_record",
        fake_get_relation_by_pair,
    )
    monkeypatch.setattr(relations_service, "get_user_record", fake_get_user)
    monkeypatch.setattr(
        relations_service, "create_relation_record", fake_create_relation
    )

    result = await relations_service.create_relation_for_teacher(
        db=FakeAsyncSession(),
        user=build_user(id="teacher-1"),
        student_id="student-1",
    )

    assert result.teacher_id == "teacher-1"
    assert result.student_id == "student-1"
    assert result.status == RelationStatuses.ACTIVE
    assert captured["teacher_id"] == "teacher-1"
    assert captured["student_id"] == "student-1"
    assert captured["status"] == RelationStatuses.ACTIVE


@pytest.mark.asyncio
async def test_list_students_for_teacher_uses_teacher_visibility(monkeypatch):
    captured = {}

    async def fake_list_relations(db, *, teacher_id=None, student_id=None, status=None):
        captured["teacher_id"] = teacher_id
        captured["student_id"] = student_id
        captured["status"] = status
        return [build_relation()]

    monkeypatch.setattr(
        relations_service, "list_relations_records", fake_list_relations
    )

    result = await relations_service.list_students_for_teacher(
        db=FakeAsyncSession(),
        user=build_user(id="teacher-1"),
        include_archived=False,
    )

    assert [relation.student_id for relation in result] == ["student-1"]
    assert captured == {
        "teacher_id": "teacher-1",
        "student_id": None,
        "status": RelationStatuses.ACTIVE,
    }


@pytest.mark.asyncio
async def test_list_teachers_for_student_uses_student_visibility(monkeypatch):
    captured = {}

    async def fake_list_relations(db, *, teacher_id=None, student_id=None, status=None):
        captured["teacher_id"] = teacher_id
        captured["student_id"] = student_id
        captured["status"] = status
        return [build_relation(student_id="student-1")]

    monkeypatch.setattr(
        relations_service, "list_relations_records", fake_list_relations
    )

    result = await relations_service.list_teachers_for_student(
        db=FakeAsyncSession(),
        user=build_user(id="student-1", role=Roles.STUDENT),
        include_archived=True,
    )

    assert [relation.teacher_id for relation in result] == ["teacher-1"]
    assert captured == {
        "teacher_id": None,
        "student_id": "student-1",
        "status": None,
    }


@pytest.mark.asyncio
async def test_archive_relation_for_user_rejects_non_participant(monkeypatch):
    async def fake_get_relation(db, *, relation_id):
        return build_relation(teacher_id="teacher-1", student_id="student-1")

    monkeypatch.setattr(
        relations_service, "get_relation_by_id_record", fake_get_relation
    )

    with pytest.raises(ForbiddenError, match="Forbidden"):
        await relations_service.archive_relation_for_user(
            db=FakeAsyncSession(),
            relation_id=1,
            user=build_user(id="teacher-2"),
        )


@pytest.mark.asyncio
async def test_archive_relation_for_user_archives_relation(monkeypatch):
    captured = {}

    async def fake_get_relation(db, *, relation_id):
        return build_relation(id=relation_id)

    async def fake_archive_relation(db, *, relation_id):
        captured["relation_id"] = relation_id
        return build_relation(
            id=relation_id,
            status=RelationStatuses.ARCHIVED,
            archived_at=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(
        relations_service, "get_relation_by_id_record", fake_get_relation
    )
    monkeypatch.setattr(
        relations_service, "archive_relation_record", fake_archive_relation
    )

    result = await relations_service.archive_relation_for_user(
        db=FakeAsyncSession(),
        relation_id=7,
        user=build_user(id="teacher-1"),
    )

    assert result.id == 7
    assert result.status == RelationStatuses.ARCHIVED
    assert result.archived_at is not None
    assert captured["relation_id"] == 7


@pytest.mark.asyncio
async def test_archive_relation_for_user_raises_not_found(monkeypatch):
    async def fake_get_relation(db, *, relation_id):
        return None

    monkeypatch.setattr(
        relations_service, "get_relation_by_id_record", fake_get_relation
    )

    with pytest.raises(NotFoundError, match="Relation not found"):
        await relations_service.archive_relation_for_user(
            db=FakeAsyncSession(),
            relation_id=1,
            user=build_user(id="teacher-1"),
        )


@pytest.mark.asyncio
async def test_ensure_active_relation_raises_when_relation_missing(monkeypatch):
    async def fake_get_relation_by_pair(db, *, teacher_id, student_id):
        return None

    monkeypatch.setattr(
        relations_service,
        "get_relation_by_pair_record",
        fake_get_relation_by_pair,
    )

    with pytest.raises(
        ForbiddenError,
        match="Active teacher-student relation is required",
    ):
        await relations_service.ensure_active_relation(
            db=FakeAsyncSession(),
            teacher_id="teacher-1",
            student_id="student-1",
        )


@pytest.mark.asyncio
async def test_ensure_active_relation_raises_when_relation_archived(monkeypatch):
    async def fake_get_relation_by_pair(db, *, teacher_id, student_id):
        return build_relation(
            status=RelationStatuses.ARCHIVED,
            archived_at=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(
        relations_service,
        "get_relation_by_pair_record",
        fake_get_relation_by_pair,
    )

    with pytest.raises(
        ForbiddenError,
        match="Active teacher-student relation is required",
    ):
        await relations_service.ensure_active_relation(
            db=FakeAsyncSession(),
            teacher_id="teacher-1",
            student_id="student-1",
        )
