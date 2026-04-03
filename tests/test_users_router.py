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
async def test_get_current_user_returns_serialized_user():
    user = build_user_dao()

    result = await users_router_module.get_current_user(user=user)

    assert result.id == "user-1"
    assert result.email == "john@example.com"
    assert result.role == "Teacher"
