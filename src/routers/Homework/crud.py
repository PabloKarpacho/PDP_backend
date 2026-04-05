import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.logger import logger
from src.models import HomeworkDAO, LessonDAO


def _normalize_datetime_to_utc(value: datetime.datetime) -> datetime.datetime:
    """Normalize a datetime value to timezone-aware UTC."""
    if value.tzinfo is None:
        normalized_value = value.replace(tzinfo=datetime.timezone.utc)
        logger.info(
            "Normalizing naive datetime to UTC: "
            f"source={value.isoformat()} result={normalized_value.isoformat()}"
        )
        return normalized_value

    normalized_value = value.astimezone(datetime.timezone.utc)
    logger.info(
        "Normalizing aware datetime to UTC: "
        f"source={value.isoformat()} result={normalized_value.isoformat()}"
    )
    return normalized_value


def _apply_homework_filters(
    statement,
    *,
    homework_id: int | None = None,
    lesson_id: int | None = None,
    teacher_id: str | None = None,
    student_id: str | None = None,
    include_deleted: bool = False,
):
    """Apply homework visibility filters to a SQLAlchemy statement."""
    if homework_id is not None:
        statement = statement.where(HomeworkDAO.id == homework_id)

    if lesson_id is not None:
        statement = statement.where(LessonDAO.id == lesson_id)

    if teacher_id is not None:
        statement = statement.where(LessonDAO.teacher_id == teacher_id)

    if student_id is not None:
        statement = statement.where(LessonDAO.student_id == student_id)

    if not include_deleted:
        statement = statement.where(
            HomeworkDAO.is_deleted.is_(False),
            LessonDAO.is_deleted.is_(False),
        )

    return statement


async def list_homeworks(
    db: AsyncSession,
    *,
    lesson_id: int | None = None,
    teacher_id: str | None = None,
    student_id: str | None = None,
    include_deleted: bool = False,
) -> list[HomeworkDAO]:
    """Return homeworks matching the provided filters."""
    logger.info(
        "Executing homework list query.",
        extra={
            "lesson_id": lesson_id,
            "teacher_id": teacher_id,
            "student_id": student_id,
            "include_deleted": include_deleted,
        },
    )
    statement = (
        select(HomeworkDAO)
        .join(HomeworkDAO.lesson)
        .options(selectinload(HomeworkDAO.lesson))
    )
    statement = _apply_homework_filters(
        statement,
        lesson_id=lesson_id,
        teacher_id=teacher_id,
        student_id=student_id,
        include_deleted=include_deleted,
    )

    result = await db.execute(statement)
    homeworks = list(result.scalars().all())
    logger.info(
        "Homework list query completed.",
        extra={"result_count": len(homeworks)},
    )
    return homeworks


async def get_homework(
    db: AsyncSession,
    *,
    homework_id: int,
    teacher_id: str | None = None,
    student_id: str | None = None,
    include_deleted: bool = False,
    load_lesson: bool = False,
) -> HomeworkDAO | None:
    """Return one homework by id with optional ownership filters."""
    logger.info(
        "Executing homework detail query.",
        extra={
            "homework_id": homework_id,
            "teacher_id": teacher_id,
            "student_id": student_id,
            "include_deleted": include_deleted,
            "load_lesson": load_lesson,
        },
    )
    statement = select(HomeworkDAO).join(HomeworkDAO.lesson)

    if load_lesson:
        statement = statement.options(selectinload(HomeworkDAO.lesson))

    statement = _apply_homework_filters(
        statement,
        homework_id=homework_id,
        teacher_id=teacher_id,
        student_id=student_id,
        include_deleted=include_deleted,
    )

    result = await db.execute(statement)
    homework = result.scalar_one_or_none()
    logger.info(
        "Homework detail query completed.",
        extra={"homework_id": homework_id, "homework_found": homework is not None},
    )
    return homework


async def create_homework(
    db: AsyncSession,
    *,
    lesson_id: int,
    teacher_id: str,
    name: str | None,
    description: str | None,
    files_urls: list[str] | None,
    answer: str | None,
    sent_files: list[str] | None,
    deadline: datetime.datetime | None,
) -> HomeworkDAO | None:
    """Create a homework record and attach it to the requested lesson."""
    logger.info(
        "Creating homework in database.",
        extra={"lesson_id": lesson_id, "teacher_id": teacher_id},
    )
    statement = (
        select(LessonDAO)
        .options(selectinload(LessonDAO.homework))
        .where(
            LessonDAO.id == lesson_id,
            LessonDAO.teacher_id == teacher_id,
            LessonDAO.is_deleted.is_(False),
        )
    )
    result = await db.execute(statement)
    lesson = result.scalar_one_or_none()

    if lesson is None:
        logger.info(
            "Homework creation aborted because lesson was not found.",
            extra={"lesson_id": lesson_id, "teacher_id": teacher_id},
        )
        return None

    if lesson.homework and not lesson.homework.is_deleted:
        logger.error(
            "Homework creation conflict detected for lesson.",
            extra={"lesson_id": lesson_id, "teacher_id": teacher_id},
        )
        raise ValueError("Lesson already has homework")

    normalized_deadline = (
        _normalize_datetime_to_utc(deadline) if deadline is not None else None
    )

    homework = HomeworkDAO(
        name=name,
        description=description,
        files_urls=files_urls,
        answer=answer,
        sent_files=sent_files,
        deadline=normalized_deadline,
    )

    db.add(homework)
    lesson.homework = homework
    await db.commit()
    await db.refresh(homework)
    logger.info(
        "Homework created in database.",
        extra={"lesson_id": lesson_id, "homework_id": homework.id},
    )

    return homework


async def update_homework(
    db: AsyncSession,
    *,
    homework_id: int,
    teacher_id: str | None = None,
    student_id: str | None = None,
    **update_data,
) -> HomeworkDAO | None:
    """Update a homework found by id and optional ownership filters."""
    logger.info(
        "Updating homework in database.",
        extra={
            "homework_id": homework_id,
            "teacher_id": teacher_id,
            "student_id": student_id,
            "fields": sorted(update_data.keys()),
        },
    )
    homework = await get_homework(
        db,
        homework_id=homework_id,
        teacher_id=teacher_id,
        student_id=student_id,
        load_lesson=True,
    )

    if homework is None:
        logger.info(
            "Homework update target was not found in database.",
            extra={"homework_id": homework_id},
        )
        return None

    normalized_update_data = dict(update_data)

    if (
        "deadline" in normalized_update_data
        and normalized_update_data["deadline"] is not None
    ):
        normalized_update_data["deadline"] = _normalize_datetime_to_utc(
            normalized_update_data["deadline"]
        )

    for field, value in normalized_update_data.items():
        setattr(homework, field, value)

    await db.commit()
    await db.refresh(homework)
    logger.info(
        "Homework updated in database.",
        extra={"homework_id": homework.id},
    )

    return homework


async def soft_delete_homework(
    db: AsyncSession,
    *,
    homework_id: int,
    teacher_id: str,
) -> HomeworkDAO | None:
    """Soft-delete homework and unlink it from the lesson."""
    logger.info(
        "Soft deleting homework in database.",
        extra={"homework_id": homework_id, "teacher_id": teacher_id},
    )
    homework = await get_homework(
        db,
        homework_id=homework_id,
        teacher_id=teacher_id,
        load_lesson=True,
    )

    if homework is None:
        logger.info(
            "Homework deletion target was not found in database.",
            extra={"homework_id": homework_id, "teacher_id": teacher_id},
        )
        return None

    homework.is_deleted = True

    if homework.lesson is not None:
        homework.lesson.homework_id = None

    await db.commit()
    logger.info(
        "Homework soft deleted in database.",
        extra={"homework_id": homework.id, "teacher_id": teacher_id},
    )

    return homework
