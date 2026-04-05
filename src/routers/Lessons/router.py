import datetime
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import UserDAO
from src.database_control.postgres import get_db
from src.dependencies import get_user, get_teacher
from src.logger import logger
from src.routers.Lessons.schemas import (
    LessonGetSchema,
    LessonCreateSchema,
    LessonUpdateSchema,
)
from src.schemas import ResponseEnvelope, success_response
from src.services.exceptions import NotFoundError, ValidationError
from src.services.lessons import (
    create_lesson_for_teacher,
    delete_lesson_for_teacher,
    list_lessons_for_user,
    update_lesson_for_teacher,
)


PREFIX = "/lessons"

router = APIRouter(prefix=PREFIX, tags=["Lessons"])


@router.get("", response_model=ResponseEnvelope[list[LessonGetSchema]])
async def get_lessons(
    user: UserDAO = Depends(get_user),
    db: AsyncSession = Depends(get_db),
    start_time: datetime.datetime | None = None,
    end_time: datetime.datetime | None = None,
) -> ResponseEnvelope[list[LessonGetSchema]]:
    logger.info(
        "Lessons list requested.",
        extra={
            "user_id": user.id,
            "role": user.role,
            "has_start_time_filter": start_time is not None,
            "has_end_time_filter": end_time is not None,
        },
    )
    lessons = await list_lessons_for_user(
        db=db,
        user=user,
        start_time=start_time,
        end_time=end_time,
    )
    return success_response(lessons)


@router.post("/create", response_model=ResponseEnvelope[LessonGetSchema])
async def create_lesson(
    lesson: LessonCreateSchema,
    user: UserDAO = Depends(get_teacher),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[LessonGetSchema]:
    logger.info(
        "Lesson creation requested.",
        extra={
            "user_id": user.id,
            "student_id": lesson.student_id,
            "status": lesson.status,
        },
    )
    try:
        lesson_data = await create_lesson_for_teacher(db=db, user=user, lesson=lesson)
        logger.info(
            "Lesson created successfully.",
            extra={"user_id": user.id, "lesson_id": lesson_data.id},
        )
        return success_response(lesson_data)
    except ValidationError as error:
        logger.error(
            "Lesson creation rejected by validation.",
            extra={"user_id": user.id, "error_type": type(error).__name__},
        )
        raise HTTPException(400, str(error)) from error


@router.put("/update/{lesson_id}", response_model=ResponseEnvelope[LessonGetSchema])
async def update_lesson(
    lesson: LessonUpdateSchema,
    lesson_id: int,
    user: UserDAO = Depends(get_teacher),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[LessonGetSchema]:
    logger.info(
        "Lesson update requested.",
        extra={
            "user_id": user.id,
            "lesson_id": lesson_id,
            "fields": sorted(lesson.model_dump(exclude_unset=True).keys()),
        },
    )
    try:
        lesson_data = await update_lesson_for_teacher(
            db=db,
            lesson_id=lesson_id,
            user=user,
            lesson=lesson,
        )
        logger.info(
            "Lesson updated successfully.",
            extra={"user_id": user.id, "lesson_id": lesson_data.id},
        )
        return success_response(lesson_data)
    except NotFoundError:
        logger.error(
            "Lesson update failed because lesson was not found.",
            extra={"user_id": user.id, "lesson_id": lesson_id},
        )
        raise HTTPException(404, "Lesson not found")
    except ValidationError as error:
        logger.error(
            "Lesson update rejected by validation.",
            extra={
                "user_id": user.id,
                "lesson_id": lesson_id,
                "error_type": type(error).__name__,
            },
        )
        raise HTTPException(400, str(error)) from error


@router.delete("/delete/{lesson_id}", response_model=ResponseEnvelope[int])
async def delete_lesson(
    lesson_id: int,
    user: UserDAO = Depends(get_teacher),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[int]:
    logger.info(
        "Lesson deletion requested.",
        extra={"user_id": user.id, "lesson_id": lesson_id},
    )
    try:
        lesson_id_result = await delete_lesson_for_teacher(
            db=db,
            lesson_id=lesson_id,
            user=user,
        )
        logger.info(
            "Lesson deleted successfully.",
            extra={"user_id": user.id, "lesson_id": lesson_id_result},
        )
        return success_response(lesson_id_result)
    except NotFoundError:
        logger.error(
            "Lesson deletion failed because lesson was not found.",
            extra={"user_id": user.id, "lesson_id": lesson_id},
        )
        raise HTTPException(404, "Lesson not found")
