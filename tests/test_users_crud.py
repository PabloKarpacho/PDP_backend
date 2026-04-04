from types import SimpleNamespace

import pytest

from src.routers.Users import crud as users_crud


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


@pytest.mark.asyncio
async def test_get_user_returns_existing_user():
    existing_user = SimpleNamespace(id="user-1")
    session = FakeAsyncSession(existing_user=existing_user)

    result = await users_crud.get_user(session, user_id="user-1")

    assert result is existing_user
    assert session.added == []
    assert session.commit_calls == 0
    assert session.refresh_calls == 0


@pytest.mark.asyncio
async def test_create_user_persists_record():
    session = FakeAsyncSession(existing_user=None)

    result = await users_crud.create_user(
        session,
        user_id="user-2",
        name="new-user",
        surname="User",
        email="new@example.com",
        role="student",
    )

    assert result.id == "user-2"
    assert result.email == "new@example.com"
    assert len(session.added) == 1
    assert session.commit_calls == 1
    assert session.refresh_calls == 1
