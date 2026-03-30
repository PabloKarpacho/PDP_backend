import datetime
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import LessonDAO, UserDAO
from src.database_control.postgres import get_db
from src.dependencies import get_user, get_teacher
from src.logger import logger
from src.constants import Roles
from src.routers.Lessons.schemas import LessonGetSchema, LessonCreateSchema, LessonUpdateSchema
from src.routers.Lessons.crud import (
    list_lessons,
    create_lesson as create_lesson_record,
    update_lesson as update_lesson_record,
    soft_delete_lesson,
)


PREFIX = "/lessons"

router = APIRouter(prefix=PREFIX, tags=["Lessons"])


def _serialize_lesson(lesson: LessonDAO) -> LessonGetSchema:
    """Convert a lesson ORM object to API response schema.

    Args:
        lesson: Lesson ORM object from the database.

    Returns:
        Serialized lesson response schema.
    """
    return LessonGetSchema(
        id=lesson.id,
        start_time=lesson.start_time,
        end_time=lesson.end_time,
        theme=lesson.theme,
        lesson_description=lesson.lesson_description,
        teacher_id=lesson.teacher_id,
        student_id=lesson.student_id,
        status=lesson.status,
        homework_id=lesson.homework_id,
        is_deleted=lesson.is_deleted,
        updated_at=lesson.updated_at,
        created_at=lesson.created_at,
    )


def _get_lesson_filters(user: UserDAO) -> dict[str, str] | None:
    """Build lesson visibility filters based on the current user's role.

    Args:
        user: Current authenticated application user.

    Returns:
        Dictionary with ownership filters for teacher or student,
        or None when the role has no access to lessons.
    """
    if user.role == Roles.STUDENT:
        return {"student_id": user.id}

    if user.role == Roles.TEACHER:
        return {"teacher_id": user.id}

    return None


def _get_lesson_update_data(lesson: LessonUpdateSchema) -> dict:
    """Prepare safe lesson update payload from the request body.

    Args:
        lesson: Incoming lesson update schema.

    Returns:
        Dictionary with mutable lesson fields only.
    """
    payload = lesson.model_dump(
        exclude_unset=True,
        exclude={"teacher_id", "is_deleted", "updated_at", "created_at"},
    )
    logger.info(f"Prepared lesson update payload: {payload}")
    return payload


@router.get("")
async def get_lessons(
    user: UserDAO = Depends(get_user),
    db: AsyncSession = Depends(get_db),
    start_time: datetime.datetime | None = None,
    end_time: datetime.datetime | None = None,
) -> List[LessonGetSchema | None]:
    lesson_filters = _get_lesson_filters(user)

    if lesson_filters is None:
        return []

    lessons = await list_lessons(
        db,
        start_time=start_time,
        end_time=end_time,
        **lesson_filters,
    )
    return [_serialize_lesson(lesson) for lesson in lessons]


@router.post("/create")
async def create_lesson(
    lesson: LessonCreateSchema,
    user: UserDAO = Depends(get_teacher),
    db: AsyncSession = Depends(get_db),
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
    return _serialize_lesson(lesson_dao)


@router.put("/update/{lesson_id}")
async def update_lesson(
    lesson: LessonUpdateSchema,
    lesson_id: int,
    user: UserDAO = Depends(get_teacher),
    db: AsyncSession = Depends(get_db),
) -> LessonGetSchema:
    logger.info(f"Received update request for lesson {lesson_id} with data: {lesson}")
    lesson_dao = await update_lesson_record(
        db,
        lesson_id=lesson_id,
        teacher_id=user.id,
        **_get_lesson_update_data(lesson),
    )

    if not lesson_dao:
        raise HTTPException(404, "Lesson not found")

    return _serialize_lesson(lesson_dao)


@router.delete("/delete/{lesson_id}")
async def delete_lesson(
    lesson_id: int,
    user: UserDAO = Depends(get_teacher),
    db: AsyncSession = Depends(get_db),
) -> int:
    lesson_dao = await soft_delete_lesson(
        db,
        lesson_id=lesson_id,
        teacher_id=user.id,
    )

    if not lesson_dao:
        raise HTTPException(404, "Lesson not found")

    return lesson_dao.id
