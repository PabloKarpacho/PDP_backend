from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from src.routers.Homework import crud as homework_crud


class FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class FakeAsyncSession:
    def __init__(self, execute_result=None):
        self.added = []
        self.commit_calls = 0
        self.refresh_calls = 0
        self.execute_result = execute_result

    def add(self, value):
        self.added.append(value)

    async def execute(self, statement):
        return FakeResult(self.execute_result)

    async def commit(self):
        self.commit_calls += 1

    async def refresh(self, value):
        self.refresh_calls += 1


def test_normalize_datetime_to_utc_converts_offset_aware_datetime():
    source = datetime(2026, 3, 29, 10, 43, tzinfo=timezone(timedelta(hours=3)))

    normalized = homework_crud._normalize_datetime_to_utc(source)

    assert normalized == datetime(2026, 3, 29, 7, 43, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_create_homework_normalizes_deadline_and_links_lesson():
    lesson = SimpleNamespace(
        id=10, teacher_id="teacher-1", is_deleted=False, homework=None
    )
    session = FakeAsyncSession(execute_result=lesson)
    deadline = datetime(2026, 3, 29, 10, 43, tzinfo=timezone(timedelta(hours=3)))

    homework = await homework_crud.create_homework(
        session,
        lesson_id=10,
        teacher_id="teacher-1",
        name="Homework 1",
        description="Solve tasks",
        files_urls=["file-1"],
        answer=None,
        sent_files=None,
        deadline=deadline,
    )

    assert homework.deadline == datetime(2026, 3, 29, 7, 43, tzinfo=timezone.utc)
    assert lesson.homework is homework
    assert session.commit_calls == 1
    assert session.refresh_calls == 1


@pytest.mark.asyncio
async def test_soft_delete_homework_marks_deleted_and_unlinks_lesson(monkeypatch):
    lesson = SimpleNamespace(homework_id=7)
    homework = SimpleNamespace(id=7, is_deleted=False, lesson=lesson)
    session = FakeAsyncSession()

    async def fake_get_homework(*args, **kwargs):
        return homework

    monkeypatch.setattr(homework_crud, "get_homework", fake_get_homework)

    result = await homework_crud.soft_delete_homework(
        session,
        homework_id=7,
        teacher_id="teacher-1",
    )

    assert result is homework
    assert homework.is_deleted is True
    assert lesson.homework_id is None
    assert session.commit_calls == 1
