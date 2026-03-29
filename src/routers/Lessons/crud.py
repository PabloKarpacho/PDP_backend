import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import LessonDAO


def _normalize_datetime_to_utc(value: datetime.datetime) -> datetime.datetime:
    """Normalize a datetime value to timezone-aware UTC.

    Args:
        value: Source datetime value from API input or filters.

    Returns:
        Datetime converted to UTC with timezone information preserved.
        Naive values are treated as UTC.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=datetime.timezone.utc)

    return value.astimezone(datetime.timezone.utc)


def _apply_lesson_filters(
    statement,
    *,
    lesson_id: int | None = None,
    teacher_id: str | None = None,
    student_id: str | None = None,
    start_time: datetime.datetime | None = None,
    end_time: datetime.datetime | None = None,
    include_deleted: bool = False,
):
    """Apply lesson filters to a SQLAlchemy statement.

    Args:
        statement: Base SQLAlchemy select statement for lessons.
        lesson_id: Filter by lesson identifier.
        teacher_id: Filter by teacher identifier.
        student_id: Filter by student identifier.
        start_time: Include lessons starting from this moment.
        end_time: Include lessons ending before this moment.
        include_deleted: Include soft-deleted lessons when True.

    Returns:
        SQLAlchemy statement with the requested filters applied.
    """
    if lesson_id is not None:
        statement = statement.where(LessonDAO.id == lesson_id)

    if teacher_id is not None:
        statement = statement.where(LessonDAO.teacher_id == teacher_id)

    if student_id is not None:
        statement = statement.where(LessonDAO.student_id == student_id)

    if start_time is not None:
        start_time = _normalize_datetime_to_utc(start_time)
        statement = statement.where(LessonDAO.start_time >= start_time)

    if end_time is not None:
        end_time = _normalize_datetime_to_utc(end_time)
        statement = statement.where(LessonDAO.end_time <= end_time)

    if not include_deleted:
        statement = statement.where(LessonDAO.is_deleted.is_(False))

    return statement


async def list_lessons(
    db: AsyncSession,
    *,
    teacher_id: str | None = None,
    student_id: str | None = None,
    start_time: datetime.datetime | None = None,
    end_time: datetime.datetime | None = None,
    include_deleted: bool = False,
) -> list[LessonDAO]:
    """Return lessons matching the provided filters.

    Args:
        db: Active async database session.
        teacher_id: Limit results to lessons of the given teacher.
        student_id: Limit results to lessons of the given student.
        start_time: Include lessons starting from this moment.
        end_time: Include lessons ending before this moment.
        include_deleted: Include soft-deleted lessons when True.

    Returns:
        List of lesson ORM objects.
    """
    statement = select(LessonDAO).options(selectinload(LessonDAO.homework))
    statement = _apply_lesson_filters(
        statement,
        teacher_id=teacher_id,
        student_id=student_id,
        start_time=start_time,
        end_time=end_time,
        include_deleted=include_deleted,
    )

    result = await db.execute(statement)
    return list(result.scalars().all())


async def get_lesson(
    db: AsyncSession,
    *,
    lesson_id: int,
    teacher_id: str | None = None,
    student_id: str | None = None,
    include_deleted: bool = False,
    load_homework: bool = False,
) -> LessonDAO | None:
    """Return one lesson by id with optional ownership filters.

    Args:
        db: Active async database session.
        lesson_id: Lesson identifier.
        teacher_id: Restrict lookup to lessons of the given teacher.
        student_id: Restrict lookup to lessons of the given student.
        include_deleted: Include soft-deleted lessons when True.
        load_homework: Load linked homework relation when True.

    Returns:
        Matching lesson ORM object or None.
    """
    statement = select(LessonDAO)

    if load_homework:
        statement = statement.options(selectinload(LessonDAO.homework))

    statement = _apply_lesson_filters(
        statement,
        lesson_id=lesson_id,
        teacher_id=teacher_id,
        student_id=student_id,
        include_deleted=include_deleted,
    )

    result = await db.execute(statement)
    return result.scalar_one_or_none()


async def create_lesson(
    db: AsyncSession,
    *,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    theme: str | None,
    lesson_description: str | None,
    teacher_id: str,
    student_id: str,
    status: str,
) -> LessonDAO:
    """Create a new lesson record.

    Args:
        db: Active async database session.
        start_time: Lesson start datetime.
        end_time: Lesson end datetime.
        theme: Lesson theme.
        lesson_description: Optional lesson description.
        teacher_id: Teacher identifier for the lesson.
        student_id: Student identifier for the lesson.
        status: Lesson status value.

    Returns:
        Created lesson ORM object after commit and refresh.
    """
    normalized_start_time = _normalize_datetime_to_utc(start_time)
    normalized_end_time = _normalize_datetime_to_utc(end_time)

    lesson = LessonDAO(
        start_time=normalized_start_time,
        end_time=normalized_end_time,
        theme=theme,
        lesson_description=lesson_description,
        teacher_id=teacher_id,
        student_id=student_id,
        status=status,
    )

    db.add(lesson)
    await db.commit()
    await db.refresh(lesson)

    return lesson


async def update_lesson(
    db: AsyncSession,
    *,
    lesson_id: int,
    teacher_id: str | None = None,
    student_id: str | None = None,
    **update_data,
) -> LessonDAO | None:
    """Update a lesson found by id and optional ownership filters.

    Args:
        db: Active async database session.
        lesson_id: Lesson identifier.
        teacher_id: Restrict update to lessons of the given teacher.
        student_id: Restrict update to lessons of the given student.
        **update_data: Fields to update on the lesson entity.

    Returns:
        Updated lesson ORM object or None if nothing matched.
    """
    lesson = await get_lesson(
        db,
        lesson_id=lesson_id,
        teacher_id=teacher_id,
        student_id=student_id,
    )

    if lesson is None:
        return None

    normalized_update_data = dict(update_data)

    if "start_time" in normalized_update_data and normalized_update_data["start_time"] is not None:
        normalized_update_data["start_time"] = _normalize_datetime_to_utc(
            normalized_update_data["start_time"]
        )

    if "end_time" in normalized_update_data and normalized_update_data["end_time"] is not None:
        normalized_update_data["end_time"] = _normalize_datetime_to_utc(
            normalized_update_data["end_time"]
        )

    for field, value in normalized_update_data.items():
        setattr(lesson, field, value)

    await db.commit()
    await db.refresh(lesson)

    return lesson


async def soft_delete_lesson(
    db: AsyncSession,
    *,
    lesson_id: int,
    teacher_id: str | None = None,
    student_id: str | None = None,
) -> LessonDAO | None:
    """Soft-delete a lesson and its homework if it exists.

    Args:
        db: Active async database session.
        lesson_id: Lesson identifier.
        teacher_id: Restrict deletion to lessons of the given teacher.
        student_id: Restrict deletion to lessons of the given student.

    Returns:
        Deleted lesson ORM object or None if nothing matched.
    """
    lesson = await get_lesson(
        db,
        lesson_id=lesson_id,
        teacher_id=teacher_id,
        student_id=student_id,
        load_homework=True,
    )

    if lesson is None:
        return None

    lesson.is_deleted = True

    if lesson.homework:
        lesson.homework.is_deleted = True

    await db.commit()

    return lesson
