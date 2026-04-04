from datetime import datetime
from types import SimpleNamespace
import importlib

import pytest


users_router_module = importlib.import_module("src.routers.Users.router")


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


@pytest.mark.asyncio
async def test_get_current_user_uses_user_service(monkeypatch):
    user = build_user_dao()
    captured = {}

    def fake_get_current_user_profile(service_user):
        captured["user"] = service_user
        return SimpleNamespace(id="user-1", email="john@example.com", role="Teacher")

    monkeypatch.setattr(
        users_router_module,
        "get_current_user_profile",
        fake_get_current_user_profile,
    )

    result = await users_router_module.get_current_user(user=user)

    assert captured["user"] is user
    assert result.success is True
    assert result.error is None
    assert result.meta.pagination is None
    assert result.data.id == "user-1"
    assert result.data.email == "john@example.com"
    assert result.data.role == "Teacher"
