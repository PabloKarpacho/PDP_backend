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
from src.services.exceptions import NotFoundError
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
    lesson_data = await create_lesson_for_teacher(db=db, user=user, lesson=lesson)
    return success_response(lesson_data)


@router.put("/update/{lesson_id}", response_model=ResponseEnvelope[LessonGetSchema])
async def update_lesson(
    lesson: LessonUpdateSchema,
    lesson_id: int,
    user: UserDAO = Depends(get_teacher),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[LessonGetSchema]:
    logger.info(f"Received update request for lesson {lesson_id} with data: {lesson}")
    try:
        lesson_data = await update_lesson_for_teacher(
            db=db,
            lesson_id=lesson_id,
            user=user,
            lesson=lesson,
        )
        return success_response(lesson_data)
    except NotFoundError:
        raise HTTPException(404, "Lesson not found")


@router.delete("/delete/{lesson_id}", response_model=ResponseEnvelope[int])
async def delete_lesson(
    lesson_id: int,
    user: UserDAO = Depends(get_teacher),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[int]:
    try:
        lesson_id_result = await delete_lesson_for_teacher(
            db=db,
            lesson_id=lesson_id,
            user=user,
        )
        return success_response(lesson_id_result)
    except NotFoundError:
        raise HTTPException(404, "Lesson not found")
