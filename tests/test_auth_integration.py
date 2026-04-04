from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
import pytest

from src.app import app
from src.auth import get_user_info
from src.constants import LessonStatuses, Roles
from src.database_control.postgres import get_db
from src.schemas import KeycloakUser


class FakeExecuteResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class FakeAsyncSession:
    def __init__(self, existing_user=None):
        self.existing_user = existing_user
        self.added = []
        self.commit_calls = 0
        self.refresh_calls = 0

    async def execute(self, statement):
        return FakeExecuteResult(self.existing_user)

    def add(self, value):
        self.added.append(value)

    async def commit(self):
        self.commit_calls += 1

    async def refresh(self, value):
        self.refresh_calls += 1


def build_lesson_payload():
    now = datetime.now()
    return {
        "start_time": now.isoformat(),
        "end_time": (now + timedelta(hours=1)).isoformat(),
        "theme": "Math",
        "lesson_description": "Algebra",
        "teacher_id": "teacher-1",
        "student_id": "student-1",
        "status": LessonStatuses.ACTIVE,
        "homework_id": None,
        "is_deleted": False,
        "updated_at": now.isoformat(),
        "created_at": now.isoformat(),
    }


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


def test_teacher_only_endpoint_forbids_student_realm_role(client: TestClient):
    session = FakeAsyncSession()
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_user_info] = lambda: KeycloakUser(
        id="student-1",
        username="student",
        email="student@example.com",
        last_name="User",
        role=Roles.TEACHER,
        realm_roles=[Roles.STUDENT.lower()],
    )

    response = client.post("/lessons/create", json=build_lesson_payload())

    assert response.status_code == 403
    assert response.json()["error"] == {
        "code": "forbidden",
        "message": "Forbidden",
        "details": None,
    }
    assert session.added == []
    assert session.commit_calls == 0


def test_user_endpoint_forbids_roleless_user_on_owned_resource(client: TestClient):
    session = FakeAsyncSession(existing_user=None)
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_user_info] = lambda: KeycloakUser(
        id="user-1",
        username="user",
        email="user@example.com",
        last_name="User",
        role=Roles.TEACHER,
        realm_roles=["admin"],
    )

    response = client.get("/homeworks/7")

    assert response.status_code == 403
    assert response.json()["error"] == {
        "code": "forbidden",
        "message": "Forbidden",
        "details": None,
    }
