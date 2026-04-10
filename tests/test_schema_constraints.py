from datetime import datetime
from datetime import timezone
from types import SimpleNamespace

import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from src.models import Base
from src.models import HomeworkDAO
from src.models import LessonDAO
from src.models import TeachersStudentsDAO
from src.models import UserDAO
from src.routers.Homework import crud as homework_crud
from src.routers.Lessons import crud as lessons_crud


@pytest_asyncio.fixture
async def schema_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield SimpleNamespace(engine=engine, session=session)

    await engine.dispose()


async def _create_user(session: AsyncSession, *, user_id: str, role: str) -> UserDAO:
    user = UserDAO(
        id=user_id,
        name=user_id,
        surname="User",
        email=f"{user_id}@example.com",
        role=role,
    )
    session.add(user)
    await session.commit()
    return user


@pytest.mark.asyncio
async def test_teachers_students_requires_existing_users(schema_db) -> None:
    session = schema_db.session
    await _create_user(session, user_id="teacher-1", role="teacher")
    await _create_user(session, user_id="student-1", role="student")

    relation = TeachersStudentsDAO(teacher_id="teacher-1", student_id="student-1")
    session.add(relation)
    await session.commit()

    invalid_relation = TeachersStudentsDAO(teacher_id="missing", student_id="student-1")
    session.add(invalid_relation)

    with pytest.raises(IntegrityError):
        await session.commit()

    await session.rollback()


@pytest.mark.asyncio
async def test_teachers_students_rejects_self_links(schema_db) -> None:
    session = schema_db.session
    await _create_user(session, user_id="teacher-1", role="teacher")

    relation = TeachersStudentsDAO(
        teacher_id="teacher-1",
        student_id="teacher-1",
        status="active",
    )
    session.add(relation)

    with pytest.raises(IntegrityError):
        await session.commit()

    await session.rollback()


@pytest.mark.asyncio
async def test_lessons_enforce_user_foreign_keys_and_one_to_one_homework(
    schema_db,
) -> None:
    session = schema_db.session
    await _create_user(session, user_id="teacher-1", role="teacher")
    await _create_user(session, user_id="student-1", role="student")

    homework = HomeworkDAO(name="Homework")
    session.add(homework)
    await session.commit()

    lesson = LessonDAO(
        start_time=datetime(2026, 4, 4, 10, tzinfo=timezone.utc),
        end_time=datetime(2026, 4, 4, 11, tzinfo=timezone.utc),
        teacher_id="teacher-1",
        student_id="student-1",
        status="active",
        homework_id=homework.id,
    )
    session.add(lesson)
    await session.commit()

    duplicated_homework_lesson = LessonDAO(
        start_time=datetime(2026, 4, 4, 12, tzinfo=timezone.utc),
        end_time=datetime(2026, 4, 4, 13, tzinfo=timezone.utc),
        teacher_id="teacher-1",
        student_id="student-1",
        status="active",
        homework_id=homework.id,
    )
    session.add(duplicated_homework_lesson)

    with pytest.raises(IntegrityError):
        await session.commit()

    await session.rollback()


@pytest.mark.asyncio
async def test_ownership_queries_return_only_owned_records(schema_db) -> None:
    session = schema_db.session
    await _create_user(session, user_id="teacher-1", role="teacher")
    await _create_user(session, user_id="teacher-2", role="teacher")
    await _create_user(session, user_id="student-1", role="student")
    await _create_user(session, user_id="student-2", role="student")

    lesson_one = LessonDAO(
        start_time=datetime(2026, 4, 4, 10, tzinfo=timezone.utc),
        end_time=datetime(2026, 4, 4, 11, tzinfo=timezone.utc),
        teacher_id="teacher-1",
        student_id="student-1",
        status="active",
    )
    lesson_two = LessonDAO(
        start_time=datetime(2026, 4, 4, 12, tzinfo=timezone.utc),
        end_time=datetime(2026, 4, 4, 13, tzinfo=timezone.utc),
        teacher_id="teacher-2",
        student_id="student-2",
        status="active",
    )
    homework_one = HomeworkDAO(name="Homework 1")
    homework_two = HomeworkDAO(name="Homework 2")
    lesson_one.homework = homework_one
    lesson_two.homework = homework_two

    session.add_all([lesson_one, lesson_two])
    await session.commit()

    teacher_lessons = await lessons_crud.list_lessons(session, teacher_id="teacher-1")
    student_homeworks = await homework_crud.list_homeworks(
        session,
        student_id="student-1",
    )

    assert [lesson.id for lesson in teacher_lessons] == [lesson_one.id]
    assert [homework.id for homework in student_homeworks] == [homework_one.id]


@pytest.mark.asyncio
async def test_expected_lesson_indexes_exist(schema_db) -> None:
    async with schema_db.engine.begin() as connection:
        lesson_indexes = await connection.run_sync(
            lambda sync_connection: inspect(sync_connection).get_indexes("lessons")
        )

    indexed_columns = {tuple(index["column_names"]) for index in lesson_indexes}

    assert ("teacher_id", "start_time") in indexed_columns
    assert ("student_id", "start_time") in indexed_columns


@pytest.mark.asyncio
async def test_expected_relation_indexes_exist(schema_db) -> None:
    async with schema_db.engine.begin() as connection:
        relation_indexes = await connection.run_sync(
            lambda sync_connection: inspect(sync_connection).get_indexes(
                "teachers_students"
            )
        )

    indexed_columns = {tuple(index["column_names"]) for index in relation_indexes}

    assert ("teacher_id", "status") in indexed_columns
    assert ("student_id", "status") in indexed_columns
