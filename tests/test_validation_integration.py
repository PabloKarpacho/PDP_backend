from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from types import SimpleNamespace
import importlib

from fastapi.testclient import TestClient
import pytest

from src.app import app
from src.constants import LessonStatuses, Roles
from src.dependencies import get_teacher, get_user


homework_router_module = importlib.import_module("src.routers.Homework.router")
lessons_router_module = importlib.import_module("src.routers.Lessons.router")


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


@pytest.fixture
def client():
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


def test_create_lesson_rejects_invalid_time_range_before_service(client, monkeypatch):
    called = {"value": False}

    async def fake_create_lesson_for_teacher(*, db, user, lesson):
        called["value"] = True
        raise AssertionError("Service should not be called for invalid payload")

    app.dependency_overrides[get_teacher] = lambda: build_user(
        id="teacher-1", role=Roles.TEACHER
    )
    monkeypatch.setattr(
        lessons_router_module,
        "create_lesson_for_teacher",
        fake_create_lesson_for_teacher,
    )

    now = datetime(2026, 3, 29, 10, 0)
    response = client.post(
        "/lessons/create",
        json={
            "start_time": now.isoformat(),
            "end_time": now.isoformat(),
            "student_id": "student-1",
            "status": LessonStatuses.ACTIVE,
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "bad_request"
    assert body["error"]["message"] == "Request validation failed"
    assert called["value"] is False


def test_update_lesson_rejects_forbidden_boundary_fields(client, monkeypatch):
    called = {"value": False}

    async def fake_update_lesson_for_teacher(*, db, lesson_id, user, lesson):
        called["value"] = True
        raise AssertionError("Service should not be called for invalid payload")

    app.dependency_overrides[get_teacher] = lambda: build_user(
        id="teacher-1", role=Roles.TEACHER
    )
    monkeypatch.setattr(
        lessons_router_module,
        "update_lesson_for_teacher",
        fake_update_lesson_for_teacher,
    )

    response = client.put(
        "/lessons/update/42",
        json={"teacher_id": "forbidden-from-client"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"
    assert called["value"] is False


def test_update_homework_rejects_invalid_file_list_before_service(client, monkeypatch):
    called = {"value": False}

    async def fake_update_homework_for_user(*, db, homework_id, user, homework):
        called["value"] = True
        raise AssertionError("Service should not be called for invalid payload")

    app.dependency_overrides[get_user] = lambda: build_user(
        id="student-1", role=Roles.STUDENT
    )
    monkeypatch.setattr(
        homework_router_module,
        "update_homework_for_user",
        fake_update_homework_for_user,
    )

    response = client.put(
        "/homeworks/update/9",
        json={
            "answer": "done",
            "sent_files": ["answer.pdf", "   "],
            "deadline": (datetime.now() + timedelta(days=1)).isoformat(),
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "bad_request"
    assert body["error"]["message"] == "Request validation failed"
    assert called["value"] is False
