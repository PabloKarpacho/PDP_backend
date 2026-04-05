import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.constants import (
    Roles,
    is_allowed_lesson_status_transition,
    role_matches,
)
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
        return {"student_id": user.id}

    if role_matches(user.role, Roles.TEACHER):
        return {"teacher_id": user.id}

    return None


def _get_lesson_update_data(lesson: LessonUpdateSchema) -> dict:
    payload = lesson.model_dump(exclude_unset=True)
    payload.pop("teacher_id", None)
    payload.pop("is_deleted", None)
    payload.pop("updated_at", None)
    payload.pop("created_at", None)
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
    lesson_filters = _get_lesson_filters(user)

    if lesson_filters is None:
        return []

    lessons = await list_lessons_records(
        db,
        start_time=start_time,
        end_time=end_time,
        **lesson_filters,
    )
    return [serialize_lesson(lesson) for lesson in lessons]


async def create_lesson_for_teacher(
    *,
    db: AsyncSession,
    user: UserDAO,
    lesson: LessonCreateSchema,
) -> LessonGetSchema:
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
    return serialize_lesson(lesson_dao)


async def update_lesson_for_teacher(
    *,
    db: AsyncSession,
    lesson_id: int,
    user: UserDAO,
    lesson: LessonUpdateSchema,
) -> LessonGetSchema:
    existing_lesson = await get_lesson_record(
        db,
        lesson_id=lesson_id,
        teacher_id=user.id,
    )

    if existing_lesson is None:
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
        raise ValidationError("Invalid lesson status transition")

    lesson_dao = await update_lesson_record(
        db,
        lesson_id=lesson_id,
        teacher_id=user.id,
        **update_data,
    )

    return serialize_lesson(lesson_dao)


async def delete_lesson_for_teacher(
    *,
    db: AsyncSession,
    lesson_id: int,
    user: UserDAO,
) -> int:
    lesson_dao = await soft_delete_lesson_record(
        db,
        lesson_id=lesson_id,
        teacher_id=user.id,
    )

    if lesson_dao is None:
        raise NotFoundError("Lesson not found")

    return lesson_dao.id
