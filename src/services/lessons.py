import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.constants import Roles
from src.models import UserDAO
from src.routers.Lessons.crud import create_lesson as create_lesson_record
from src.routers.Lessons.crud import list_lessons as list_lessons_records
from src.routers.Lessons.crud import soft_delete_lesson as soft_delete_lesson_record
from src.routers.Lessons.crud import update_lesson as update_lesson_record
from src.routers.Lessons.schemas import (
    LessonCreateSchema,
    LessonGetSchema,
    LessonUpdateSchema,
)
from src.routers.Lessons.utils import serialize_lesson
from src.services.exceptions import NotFoundError


def _get_lesson_filters(user: UserDAO) -> dict[str, str] | None:
    if user.role == Roles.STUDENT:
        return {"student_id": user.id}

    if user.role == Roles.TEACHER:
        return {"teacher_id": user.id}

    return None


def _get_lesson_update_data(lesson: LessonUpdateSchema) -> dict:
    payload = lesson.model_dump(exclude_unset=True)
    payload.pop("teacher_id", None)
    payload.pop("is_deleted", None)
    payload.pop("updated_at", None)
    payload.pop("created_at", None)
    return payload


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
    lesson_dao = await update_lesson_record(
        db,
        lesson_id=lesson_id,
        teacher_id=user.id,
        **_get_lesson_update_data(lesson),
    )

    if lesson_dao is None:
        raise NotFoundError("Lesson not found")

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
