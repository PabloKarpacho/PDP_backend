from types import SimpleNamespace
import importlib

import pytest
from fastapi import HTTPException

from src import dependencies as dependencies_module
from src.constants import Roles
from src.schemas import KeycloakUser
from src.services import users as users_service


users_router_module = importlib.import_module("src.routers.Users.router")


class FakeLogger:
    def __init__(self) -> None:
        self.info_messages: list[tuple[str, dict | None]] = []
        self.error_messages: list[tuple[str, dict | None]] = []

    def info(self, message: str, extra: dict | None = None) -> None:
        self.info_messages.append((message, extra))

    def error(self, message: str, extra: dict | None = None) -> None:
        self.error_messages.append((message, extra))


@pytest.mark.asyncio
async def test_get_teacher_logs_role_guard_failure(monkeypatch):
    fake_logger = FakeLogger()
    monkeypatch.setattr(dependencies_module, "logger", fake_logger)

    keycloak_user = KeycloakUser(
        id="student-1",
        username="student",
        email="student@example.com",
        realm_roles=[Roles.STUDENT.lower()],
    )

    with pytest.raises(HTTPException):
        await dependencies_module.get_teacher(
            keycloak_user=keycloak_user,
            db=object(),
        )

    assert fake_logger.info_messages[0][0] == "Resolving teacher dependency."
    assert fake_logger.error_messages[0][0] == "Role guard failed."
    assert fake_logger.error_messages[0][1]["user_id"] == "student-1"


@pytest.mark.asyncio
async def test_get_or_create_user_logs_sync_update(monkeypatch):
    fake_logger = FakeLogger()
    existing_user = SimpleNamespace(
        id="user-1",
        name="Old",
        surname="User",
        email="old@example.com",
        role=Roles.STUDENT,
    )
    captured = {}

    async def fake_get_user_record(db, *, user_id):
        return existing_user

    async def fake_update_user_record(db, *, user, name, surname, email, role):
        captured["user"] = user
        captured["payload"] = {
            "name": name,
            "surname": surname,
            "email": email,
            "role": role,
        }
        return existing_user

    monkeypatch.setattr(users_service, "logger", fake_logger)
    monkeypatch.setattr(users_service, "get_user_record", fake_get_user_record)
    monkeypatch.setattr(users_service, "update_user_record", fake_update_user_record)

    await users_service.get_or_create_user_from_keycloak(
        db=object(),
        keycloak_user=KeycloakUser(
            id="user-1",
            username="john",
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            realm_roles=[Roles.TEACHER.lower()],
        ),
    )

    assert (
        fake_logger.info_messages[0][0]
        == "Synchronizing application user from Keycloak."
    )
    assert (
        fake_logger.info_messages[1][0]
        == "Updating existing application user from Keycloak."
    )
    assert captured["payload"]["role"] == Roles.TEACHER


@pytest.mark.asyncio
async def test_users_router_logs_profile_request(monkeypatch):
    fake_logger = FakeLogger()
    monkeypatch.setattr(users_router_module, "logger", fake_logger)
    monkeypatch.setattr(
        users_router_module,
        "get_current_user_profile",
        lambda user: SimpleNamespace(
            id=user.id, email="john@example.com", role=user.role
        ),
    )

    user = SimpleNamespace(id="user-1", role=Roles.TEACHER)

    result = await users_router_module.get_current_user(user=user)

    assert result.success is True
    assert fake_logger.info_messages[0][0] == "Current user profile requested."
    assert fake_logger.info_messages[0][1] == {
        "user_id": "user-1",
        "role": Roles.TEACHER,
    }
