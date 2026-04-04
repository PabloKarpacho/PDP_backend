from datetime import datetime
from types import SimpleNamespace

import pytest

from src.schemas import KeycloakUser
from src.services import users as users_service


class FakeAsyncSession:
    pass


def build_user_dao(**overrides):
    now = datetime.now()
    payload = {
        "id": "user-1",
        "name": "John",
        "surname": "Doe",
        "email": "john@example.com",
        "role": "Teacher",
        "updated_at": now,
        "created_at": now,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def build_keycloak_user(**overrides):
    payload = {
        "id": "user-1",
        "username": "john",
        "email": "john@example.com",
        "last_name": "Doe",
        "role": "Teacher",
        "realm_roles": [],
    }
    payload.update(overrides)
    return KeycloakUser(**payload)


def test_get_current_user_profile_serializes_user():
    result = users_service.get_current_user_profile(build_user_dao())

    assert result.id == "user-1"
    assert result.email == "john@example.com"
    assert result.role == "Teacher"


@pytest.mark.asyncio
async def test_get_or_create_user_from_keycloak_returns_existing_user(monkeypatch):
    user = build_user_dao()

    async def fake_get_user(db, *, user_id):
        assert isinstance(db, FakeAsyncSession)
        assert user_id == "user-1"
        return user

    monkeypatch.setattr(users_service, "get_user_record", fake_get_user)

    result = await users_service.get_or_create_user_from_keycloak(
        db=FakeAsyncSession(),
        keycloak_user=build_keycloak_user(),
    )

    assert result is user


@pytest.mark.asyncio
async def test_get_or_create_user_from_keycloak_creates_missing_user(monkeypatch):
    created_user = build_user_dao(id="user-2", email="new@example.com")

    async def fake_get_user(db, *, user_id):
        return None

    async def fake_create_user(db, **payload):
        assert payload == {
            "user_id": "user-2",
            "name": "new-user",
            "surname": "User",
            "email": "new@example.com",
            "role": "student",
        }
        return created_user

    monkeypatch.setattr(users_service, "get_user_record", fake_get_user)
    monkeypatch.setattr(users_service, "create_user_record", fake_create_user)

    result = await users_service.get_or_create_user_from_keycloak(
        db=FakeAsyncSession(),
        keycloak_user=build_keycloak_user(
            id="user-2",
            username="new-user",
            email="new@example.com",
            last_name="User",
            role="student",
        ),
    )

    assert result is created_user
