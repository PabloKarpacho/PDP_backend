import datetime
from typing import List
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
from src.services.exceptions import NotFoundError
from src.services.lessons import (
    create_lesson_for_teacher,
    delete_lesson_for_teacher,
    list_lessons_for_user,
    update_lesson_for_teacher,
)


PREFIX = "/lessons"

router = APIRouter(prefix=PREFIX, tags=["Lessons"])


@router.get("")
async def get_lessons(
    user: UserDAO = Depends(get_user),
    db: AsyncSession = Depends(get_db),
    start_time: datetime.datetime | None = None,
    end_time: datetime.datetime | None = None,
) -> List[LessonGetSchema | None]:
    return await list_lessons_for_user(
        db=db,
        user=user,
        start_time=start_time,
        end_time=end_time,
    )


@router.post("/create")
async def create_lesson(
    lesson: LessonCreateSchema,
    user: UserDAO = Depends(get_teacher),
    db: AsyncSession = Depends(get_db),
) -> LessonGetSchema:
    return await create_lesson_for_teacher(db=db, user=user, lesson=lesson)


@router.put("/update/{lesson_id}")
async def update_lesson(
    lesson: LessonUpdateSchema,
    lesson_id: int,
    user: UserDAO = Depends(get_teacher),
    db: AsyncSession = Depends(get_db),
) -> LessonGetSchema:
    logger.info(f"Received update request for lesson {lesson_id} with data: {lesson}")
    try:
        return await update_lesson_for_teacher(
            db=db,
            lesson_id=lesson_id,
            user=user,
            lesson=lesson,
        )
    except NotFoundError:
        raise HTTPException(404, "Lesson not found")


@router.delete("/delete/{lesson_id}")
async def delete_lesson(
    lesson_id: int,
    user: UserDAO = Depends(get_teacher),
    db: AsyncSession = Depends(get_db),
) -> int:
    try:
        return await delete_lesson_for_teacher(
            db=db,
            lesson_id=lesson_id,
            user=user,
        )
    except NotFoundError:
        raise HTTPException(404, "Lesson not found")
