import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.constants import (
    Roles,
    is_allowed_lesson_status_transition,
    role_matches,
)
from src.logger import logger
from src.models import UserDAO
from src.routers.Lessons.crud import create_lesson as create_lesson_record
from src.routers.Lessons.crud import get_lesson as get_lesson_record
from src.routers.Lessons.crud import list_lessons as list_lessons_records
from src.routers.Lessons.crud import soft_delete_lesson as soft_delete_lesson_record
from src.routers.Lessons.crud import update_lesson as update_lesson_record
from src.routers.Lessons.schemas import (
    LessonCreateSchema,
    LessonGetSchema,
    LessonUpdateSchema,
)
from src.routers.Lessons.utils import serialize_lesson
from src.services.exceptions import NotFoundError, ValidationError


def _get_lesson_filters(user: UserDAO) -> dict[str, str] | None:
    if role_matches(user.role, Roles.STUDENT):
        logger.info(
            "Lesson visibility resolved for student.", extra={"user_id": user.id}
        )
        return {"student_id": user.id}

    if role_matches(user.role, Roles.TEACHER):
        logger.info(
            "Lesson visibility resolved for teacher.", extra={"user_id": user.id}
        )
        return {"teacher_id": user.id}

    logger.info(
        "Lesson visibility could not be resolved for role.",
        extra={"user_id": user.id, "role": user.role},
    )
    return None


def _get_lesson_update_data(lesson: LessonUpdateSchema) -> dict:
    payload = lesson.model_dump(exclude_unset=True)
    payload.pop("teacher_id", None)
    payload.pop("is_deleted", None)
    payload.pop("updated_at", None)
    payload.pop("created_at", None)
    logger.info(
        "Lesson service update payload prepared.",
        extra={"fields": sorted(payload.keys()), "field_count": len(payload)},
    )
    return payload


def _validate_lesson_time_range(
    *,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
) -> None:
    if start_time >= end_time:
        raise ValidationError("start_time must be before end_time")


async def list_lessons_for_user(
    *,
    db: AsyncSession,
    user: UserDAO,
    start_time: datetime.datetime | None = None,
    end_time: datetime.datetime | None = None,
) -> list[LessonGetSchema]:
    logger.info(
        "Listing lessons for user.",
        extra={
            "user_id": user.id,
            "role": user.role,
            "has_start_time_filter": start_time is not None,
            "has_end_time_filter": end_time is not None,
        },
    )
    lesson_filters = _get_lesson_filters(user)

    if lesson_filters is None:
        logger.info(
            "No lesson visibility filters available; returning empty result.",
            extra={"user_id": user.id},
        )
        return []

    lessons = await list_lessons_records(
        db,
        start_time=start_time,
        end_time=end_time,
        **lesson_filters,
    )
    logger.info(
        "Lessons listed successfully.",
        extra={"user_id": user.id, "lesson_count": len(lessons)},
    )
    return [serialize_lesson(lesson) for lesson in lessons]


async def create_lesson_for_teacher(
    *,
    db: AsyncSession,
    user: UserDAO,
    lesson: LessonCreateSchema,
) -> LessonGetSchema:
    logger.info(
        "Creating lesson for teacher.",
        extra={"user_id": user.id, "student_id": lesson.student_id},
    )
    lesson_dao = await create_lesson_record(
        db,
        start_time=lesson.start_time,
        end_time=lesson.end_time,
        theme=lesson.theme,
        lesson_description=lesson.lesson_description,
        teacher_id=user.id,
        student_id=lesson.student_id,
        status=lesson.status,
    )
    logger.info(
        "Lesson created for teacher.",
        extra={"user_id": user.id, "lesson_id": lesson_dao.id},
    )
    return serialize_lesson(lesson_dao)


async def update_lesson_for_teacher(
    *,
    db: AsyncSession,
    lesson_id: int,
    user: UserDAO,
    lesson: LessonUpdateSchema,
) -> LessonGetSchema:
    logger.info(
        "Updating lesson for teacher.",
        extra={"user_id": user.id, "lesson_id": lesson_id},
    )
    existing_lesson = await get_lesson_record(
        db,
        lesson_id=lesson_id,
        teacher_id=user.id,
    )

    if existing_lesson is None:
        logger.error(
            "Lesson update target not found.",
            extra={"user_id": user.id, "lesson_id": lesson_id},
        )
        raise NotFoundError("Lesson not found")

    update_data = _get_lesson_update_data(lesson)

    _validate_lesson_time_range(
        start_time=update_data.get("start_time", existing_lesson.start_time),
        end_time=update_data.get("end_time", existing_lesson.end_time),
    )

    if "status" in update_data and not is_allowed_lesson_status_transition(
        existing_lesson.status,
        update_data["status"],
    ):
        logger.error(
            "Lesson status transition rejected.",
            extra={
                "user_id": user.id,
                "lesson_id": lesson_id,
                "from_status": existing_lesson.status,
                "to_status": update_data["status"],
            },
        )
        raise ValidationError("Invalid lesson status transition")

    lesson_dao = await update_lesson_record(
        db,
        lesson_id=lesson_id,
        teacher_id=user.id,
        **update_data,
    )
    logger.info(
        "Lesson updated for teacher.",
        extra={"user_id": user.id, "lesson_id": lesson_dao.id},
    )

    return serialize_lesson(lesson_dao)


async def delete_lesson_for_teacher(
    *,
    db: AsyncSession,
    lesson_id: int,
    user: UserDAO,
) -> int:
    logger.info(
        "Deleting lesson for teacher.",
        extra={"user_id": user.id, "lesson_id": lesson_id},
    )
    lesson_dao = await soft_delete_lesson_record(
        db,
        lesson_id=lesson_id,
        teacher_id=user.id,
    )

    if lesson_dao is None:
        logger.error(
            "Lesson deletion target not found.",
            extra={"user_id": user.id, "lesson_id": lesson_id},
        )
        raise NotFoundError("Lesson not found")

    logger.info(
        "Lesson deleted for teacher.",
        extra={"user_id": user.id, "lesson_id": lesson_dao.id},
    )
    return lesson_dao.id
