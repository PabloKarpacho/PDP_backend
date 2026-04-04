from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database_control.postgres import get_db
from src.dependencies import get_teacher, get_user
from src.logger import logger
from src.models import UserDAO
from src.routers.Homework.schemas import (
    HomeworkCreateSchema,
    HomeworkGetSchema,
    HomeworkUpdateSchema,
)
from src.services.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from src.services.homework import (
    create_homework_for_teacher,
    delete_homework_for_teacher,
    get_homework_for_user,
    list_homeworks_for_user,
    update_homework_for_user,
)


PREFIX = "/homeworks"

router = APIRouter(prefix=PREFIX, tags=["Homeworks"])


@router.get("")
async def get_homeworks(
    user: UserDAO = Depends(get_user),
    db: AsyncSession = Depends(get_db),
    lesson_id: int | None = None,
) -> List[HomeworkGetSchema]:
    return await list_homeworks_for_user(
        db=db,
        user=user,
        lesson_id=lesson_id,
    )


@router.get("/{homework_id}")
async def get_homework(
    homework_id: int,
    user: UserDAO = Depends(get_user),
    db: AsyncSession = Depends(get_db),
) -> HomeworkGetSchema:
    try:
        return await get_homework_for_user(
            db=db,
            homework_id=homework_id,
            user=user,
        )
    except ForbiddenError:
        raise HTTPException(403, "Forbidden")
    except NotFoundError:
        raise HTTPException(404, "Homework not found")


@router.post("/create")
async def create_homework(
    homework: HomeworkCreateSchema,
    user: UserDAO = Depends(get_teacher),
    db: AsyncSession = Depends(get_db),
) -> HomeworkGetSchema:
    try:
        return await create_homework_for_teacher(
            db=db,
            user=user,
            homework=homework,
        )
    except ValidationError as error:
        raise HTTPException(400, str(error)) from error
    except ConflictError as error:
        raise HTTPException(409, str(error)) from error
    except NotFoundError as error:
        raise HTTPException(404, "Lesson not found") from error


@router.put("/update/{homework_id}")
async def update_homework(
    homework: HomeworkUpdateSchema,
    homework_id: int,
    user: UserDAO = Depends(get_user),
    db: AsyncSession = Depends(get_db),
) -> HomeworkGetSchema:
    logger.info(
        f"Received update request for homework {homework_id} with data: {homework}"
    )
    try:
        return await update_homework_for_user(
            db=db,
            homework_id=homework_id,
            user=user,
            homework=homework,
        )
    except ForbiddenError as error:
        raise HTTPException(403, "Forbidden") from error
    except NotFoundError as error:
        raise HTTPException(404, "Homework not found") from error


@router.delete("/delete/{homework_id}")
async def delete_homework(
    homework_id: int,
    user: UserDAO = Depends(get_teacher),
    db: AsyncSession = Depends(get_db),
) -> int:
    try:
        return await delete_homework_for_teacher(
            db=db,
            homework_id=homework_id,
            user=user,
        )
    except NotFoundError as error:
        raise HTTPException(404, "Homework not found") from error
