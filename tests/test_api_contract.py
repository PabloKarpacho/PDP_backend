from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from types import SimpleNamespace
import importlib

from fastapi.testclient import TestClient
import pytest

from src.app import app
from src.constants import LessonStatuses, Roles
from src.dependencies import get_teacher, get_user
from src.services.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)


homework_router_module = importlib.import_module("src.routers.Homework.router")
lessons_router_module = importlib.import_module("src.routers.Lessons.router")
files_router_module = importlib.import_module("src.routers.Files.router")
relations_router_module = importlib.import_module("src.routers.Relations.router")


def build_user(**overrides):
    now = datetime.now()
    payload = {
        "id": "user-1",
        "name": "John",
        "surname": "Doe",
        "email": "john@example.com",
        "role": Roles.TEACHER,
        "updated_at": now,
        "created_at": now,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def build_homework_payload():
    now = datetime.now()
    return {
        "name": "Homework 1",
        "description": "Solve tasks",
        "files_urls": ["task.pdf"],
        "deadline": (now + timedelta(days=1)).isoformat(),
        "lesson_id": 5,
    }


def build_lesson_payload():
    now = datetime.now()
    return {
        "start_time": now.isoformat(),
        "end_time": (now + timedelta(hours=1)).isoformat(),
        "theme": "Math",
        "lesson_description": "Algebra",
        "student_id": "student-1",
        "status": LessonStatuses.ACTIVE,
    }


def build_relation_payload():
    now = datetime.now()
    return {
        "id": 1,
        "teacher_id": "teacher-1",
        "student_id": "student-1",
        "status": "active",
        "archived_at": None,
        "updated_at": now.isoformat(),
        "created_at": now.isoformat(),
    }


@pytest.fixture
def client(monkeypatch):
    @asynccontextmanager
    async def noop_lifespan(_: object):
        yield

    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = noop_lifespan

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.router.lifespan_context = original_lifespan
        app.dependency_overrides.clear()


def test_readiness_endpoint_uses_success_envelope(client: TestClient):
    response = client.get("/actuator/health/readiness")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "data": {"status": "ready"},
        "error": None,
        "meta": {"pagination": None},
    }


def test_users_me_endpoint_uses_success_envelope(client: TestClient):
    app.dependency_overrides[get_user] = lambda: build_user()

    response = client.get("/users/me")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["error"] is None
    assert body["meta"] == {"pagination": None}
    assert body["data"]["id"] == "user-1"
    assert body["data"]["email"] == "john@example.com"


def test_files_upload_endpoint_uses_success_envelope(client: TestClient, monkeypatch):
    class FakeS3Client:
        async def upload_fileobj(
            self,
            *,
            fileobj,
            key,
            bucket_name,
            content_type=None,
            metadata=None,
            size=None,
        ):
            data = fileobj.read()
            if hasattr(fileobj, "seek"):
                fileobj.seek(0)
            return type(
                "StoredObject",
                (),
                {
                    "bucket_name": bucket_name,
                    "key": key,
                    "content_type": content_type,
                    "size": size if size is not None else len(data),
                },
            )()

        async def generate_presigned_download_url(
            self, *, key, bucket_name, url_expiry=3600
        ):
            return "https://example.com/file"

    monkeypatch.setattr(files_router_module, "get_s3_client", lambda: FakeS3Client())
    app.dependency_overrides[get_user] = lambda: build_user()

    response = client.post(
        "/files/file_upload",
        files={"file": ("lesson.txt", b"payload", "text/plain")},
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["error"] is None
    assert response.json()["meta"] == {"pagination": None}
    assert response.json()["data"] == {
        "download_url": "https://example.com/file",
        "original_filename": "lesson.txt",
        "content_type": "text/plain",
        "size": 7,
    }
    assert "bucket_name" not in response.json()["data"]
    assert "key" not in response.json()["data"]


def test_validation_errors_use_shared_error_envelope(client: TestClient, monkeypatch):
    async def fake_create_homework_for_teacher(*, db, user, homework):
        raise ValidationError("lesson_id is required")

    app.dependency_overrides[get_teacher] = lambda: build_user(
        id="teacher-1", role=Roles.TEACHER
    )
    monkeypatch.setattr(
        homework_router_module,
        "create_homework_for_teacher",
        fake_create_homework_for_teacher,
    )

    response = client.post("/homeworks/create", json=build_homework_payload())

    assert response.status_code == 400
    assert response.json() == {
        "success": False,
        "data": None,
        "error": {
            "code": "bad_request",
            "message": "lesson_id is required",
            "details": None,
        },
        "meta": {"pagination": None},
    }


def test_files_upload_endpoint_rejects_anonymous_requests(client: TestClient):
    response = client.post("/files/file_upload")

    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]["code"] == "unauthorized"
    assert body["error"]["message"] == "Not authenticated"
    assert body["error"]["details"] is None
    assert body["meta"] == {"pagination": None}


def test_forbidden_errors_use_shared_error_envelope(client: TestClient, monkeypatch):
    async def fake_get_homework_for_user(*, db, homework_id, user):
        raise ForbiddenError("Forbidden")

    app.dependency_overrides[get_user] = lambda: build_user(
        id="student-1", role=Roles.STUDENT
    )
    monkeypatch.setattr(
        homework_router_module,
        "get_homework_for_user",
        fake_get_homework_for_user,
    )

    response = client.get("/homeworks/7")

    assert response.status_code == 403
    assert response.json() == {
        "success": False,
        "data": None,
        "error": {
            "code": "forbidden",
            "message": "Forbidden",
            "details": None,
        },
        "meta": {"pagination": None},
    }


def test_not_found_errors_use_shared_error_envelope(client: TestClient, monkeypatch):
    async def fake_update_lesson_for_teacher(*, db, lesson_id, user, lesson):
        raise NotFoundError("Lesson not found")

    app.dependency_overrides[get_teacher] = lambda: build_user(
        id="teacher-1", role=Roles.TEACHER
    )
    monkeypatch.setattr(
        lessons_router_module,
        "update_lesson_for_teacher",
        fake_update_lesson_for_teacher,
    )

    response = client.put("/lessons/update/42", json=build_lesson_payload())

    assert response.status_code == 404
    assert response.json() == {
        "success": False,
        "data": None,
        "error": {
            "code": "not_found",
            "message": "Lesson not found",
            "details": None,
        },
        "meta": {"pagination": None},
    }


def test_conflict_errors_use_shared_error_envelope(client: TestClient, monkeypatch):
    async def fake_create_homework_for_teacher(*, db, user, homework):
        raise ConflictError("Lesson already has homework")

    app.dependency_overrides[get_teacher] = lambda: build_user(
        id="teacher-1", role=Roles.TEACHER
    )
    monkeypatch.setattr(
        homework_router_module,
        "create_homework_for_teacher",
        fake_create_homework_for_teacher,
    )

    response = client.post("/homeworks/create", json=build_homework_payload())

    assert response.status_code == 409
    assert response.json() == {
        "success": False,
        "data": None,
        "error": {
            "code": "conflict",
            "message": "Lesson already has homework",
            "details": None,
        },
        "meta": {"pagination": None},
    }


def test_relations_students_endpoint_uses_success_envelope(
    client: TestClient, monkeypatch
):
    async def fake_list_students_for_teacher(*, db, user, include_archived):
        return [build_relation_payload()]

    app.dependency_overrides[get_teacher] = lambda: build_user(
        id="teacher-1",
        role=Roles.TEACHER,
    )
    monkeypatch.setattr(
        relations_router_module,
        "list_students_for_teacher",
        fake_list_students_for_teacher,
    )

    response = client.get("/relations/students")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["error"] is None
    assert body["meta"] == {"pagination": None}
    assert body["data"][0]["teacher_id"] == "teacher-1"
    assert body["data"][0]["student_id"] == "student-1"


def test_relations_archive_forbidden_uses_shared_error_envelope(
    client: TestClient, monkeypatch
):
    async def fake_archive_relation_for_user(*, db, relation_id, user):
        raise ForbiddenError("Forbidden")

    app.dependency_overrides[get_user] = lambda: build_user(
        id="student-2",
        role=Roles.STUDENT,
    )
    monkeypatch.setattr(
        relations_router_module,
        "archive_relation_for_user",
        fake_archive_relation_for_user,
    )

    response = client.post("/relations/archive/7")

    assert response.status_code == 403
    assert response.json() == {
        "success": False,
        "data": None,
        "error": {
            "code": "forbidden",
            "message": "Forbidden",
            "details": None,
        },
        "meta": {"pagination": None},
    }
