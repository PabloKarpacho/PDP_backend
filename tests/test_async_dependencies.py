from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from src.constants import Roles
from src.dependencies import get_teacher, get_user
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


def build_existing_user(**overrides):
    payload = {
        "id": "user-1",
        "name": "existing",
        "surname": "User",
        "email": "existing@example.com",
        "role": Roles.TEACHER,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


@pytest.mark.asyncio
async def test_get_user_returns_existing_user_without_creating_new_one():
    existing_user = build_existing_user()
    session = FakeAsyncSession(existing_user=existing_user)
    keycloak_user = KeycloakUser(
        id="user-1",
        username="existing",
        email="existing@example.com",
        last_name="User",
        role="teacher",
        realm_roles=[Roles.TEACHER.lower()],
    )

    result = await get_user(keycloak_user=keycloak_user, db=session)

    assert result is existing_user
    assert session.added == []
    assert session.commit_calls == 0
    assert session.refresh_calls == 0


@pytest.mark.asyncio
async def test_get_user_creates_user_when_missing():
    session = FakeAsyncSession(existing_user=None)
    keycloak_user = KeycloakUser(
        id="user-2",
        username="new-user",
        email="new@example.com",
        last_name="User",
        role="teacher",
        realm_roles=[Roles.STUDENT.lower()],
    )

    result = await get_user(keycloak_user=keycloak_user, db=session)

    assert result.id == "user-2"
    assert result.email == "new@example.com"
    assert result.role == Roles.STUDENT
    assert len(session.added) == 1
    assert session.commit_calls == 1
    assert session.refresh_calls == 1


@pytest.mark.asyncio
async def test_get_teacher_rejects_payload_role_without_teacher_realm_role():
    session = FakeAsyncSession(existing_user=None)
    keycloak_user = KeycloakUser(
        id="teacher-1",
        username="teacher",
        email="teacher@example.com",
        last_name="User",
        role=Roles.TEACHER,
        realm_roles=[Roles.STUDENT.lower()],
    )

    with pytest.raises(HTTPException) as exc_info:
        await get_teacher(keycloak_user=keycloak_user, db=session)

    assert exc_info.value.status_code == 403
    assert session.added == []
    assert session.commit_calls == 0


@pytest.mark.asyncio
async def test_get_teacher_uses_teacher_realm_role_even_when_payload_role_conflicts():
    existing_user = build_existing_user(
        id="teacher-1",
        name="teacher",
        email="teacher@example.com",
    )
    session = FakeAsyncSession(existing_user=existing_user)
    keycloak_user = KeycloakUser(
        id="teacher-1",
        username="teacher",
        email="teacher@example.com",
        last_name="User",
        role=Roles.STUDENT,
        realm_roles=[Roles.TEACHER.lower()],
    )

    result = await get_teacher(keycloak_user=keycloak_user, db=session)

    assert result is existing_user
    assert session.added == []
    assert session.commit_calls == 0


@pytest.mark.asyncio
async def test_get_teacher_prefers_teacher_when_multiple_supported_realm_roles_exist():
    existing_user = build_existing_user(
        id="teacher-2",
        name="teacher",
        email="teacher2@example.com",
    )
    session = FakeAsyncSession(existing_user=existing_user)
    keycloak_user = KeycloakUser(
        id="teacher-2",
        username="teacher",
        email="teacher2@example.com",
        last_name="User",
        role=None,
        realm_roles=[Roles.STUDENT.lower(), Roles.TEACHER.lower()],
    )

    result = await get_teacher(keycloak_user=keycloak_user, db=session)

    assert result is existing_user


@pytest.mark.asyncio
async def test_get_teacher_raises_for_non_teacher():
    session = FakeAsyncSession(existing_user=None)
    keycloak_user = KeycloakUser(
        id="student-1",
        username="student",
        email="student@example.com",
        last_name="User",
        role=Roles.STUDENT,
        realm_roles=[Roles.STUDENT.lower()],
    )

    with pytest.raises(HTTPException) as exc_info:
        await get_teacher(keycloak_user=keycloak_user, db=session)

    assert exc_info.value.status_code == 403
    assert session.added == []
    assert session.commit_calls == 0
