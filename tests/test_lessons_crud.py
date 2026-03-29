from datetime import datetime, timedelta, timezone

import pytest

from src.routers.Lessons import crud as lessons_crud


class FakeAsyncSession:
    def __init__(self):
        self.added = []
        self.commit_calls = 0
        self.refresh_calls = 0

    def add(self, value):
        self.added.append(value)

    async def commit(self):
        self.commit_calls += 1

    async def refresh(self, value):
        self.refresh_calls += 1


def test_normalize_datetime_to_utc_converts_offset_aware_datetime():
    source = datetime(2026, 3, 29, 10, 43, tzinfo=timezone(timedelta(hours=3)))

    normalized = lessons_crud._normalize_datetime_to_utc(source)

    assert normalized == datetime(2026, 3, 29, 7, 43, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_create_lesson_normalizes_datetimes_before_save():
    session = FakeAsyncSession()
    start_time = datetime(2026, 3, 29, 10, 43, tzinfo=timezone(timedelta(hours=3)))
    end_time = datetime(2026, 3, 29, 11, 43, tzinfo=timezone(timedelta(hours=3)))

    lesson = await lessons_crud.create_lesson(
        session,
        start_time=start_time,
        end_time=end_time,
        theme="Math",
        lesson_description="Algebra",
        teacher_id="teacher-1",
        student_id="student-1",
        status="active",
    )

    assert lesson.start_time == datetime(2026, 3, 29, 7, 43, tzinfo=timezone.utc)
    assert lesson.end_time == datetime(2026, 3, 29, 8, 43, tzinfo=timezone.utc)
    assert session.commit_calls == 1
    assert session.refresh_calls == 1
