from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.constants import Roles
from src.database_control.postgres import get_db
from src.dependencies import get_teacher, get_user
from src.logger import logger
from src.models import HomeworkDAO, UserDAO
from src.routers.Homework.schemas import (
    HomeworkCreateSchema,
    HomeworkGetSchema,
    HomeworkUpdateSchema,
)
from src.routers.Homework.crud import (
    create_homework as create_homework_record,
    get_homework as get_homework_record,
    list_homeworks,
    soft_delete_homework,
    update_homework as update_homework_record,
)


PREFIX = "/homeworks"

router = APIRouter(prefix=PREFIX, tags=["Homeworks"])


def _serialize_homework(homework: HomeworkDAO) -> HomeworkGetSchema:
    """Convert a homework ORM object to API response schema."""
    lesson_id = homework.lesson.id if homework.lesson is not None else None
    return HomeworkGetSchema(
        id=homework.id,
        name=homework.name,
        description=homework.description,
        files_urls=homework.files_urls,
        answer=homework.answer,
        sent_files=homework.sent_files,
        deadline=homework.deadline,
        lesson_id=lesson_id,
        is_deleted=homework.is_deleted,
        updated_at=homework.updated_at,
        created_at=homework.created_at,
    )


def _get_homework_filters(user: UserDAO) -> dict[str, str] | None:
    """Build homework visibility filters based on the current user's role."""
    if user.role == Roles.STUDENT:
        return {"student_id": user.id}

    if user.role == Roles.TEACHER:
        return {"teacher_id": user.id}

    return None


def _get_homework_update_data(
    homework: HomeworkUpdateSchema,
    user: UserDAO,
) -> dict:
    """Prepare safe homework update payload from the request body."""
    if user.role == Roles.STUDENT:
        payload = homework.model_dump(
            exclude_unset=True,
            include={"answer", "sent_files"},
        )
    else:
        payload = homework.model_dump(
            exclude_unset=True,
            exclude={
                "lesson_id",
                "answer",
                "sent_files",
                "is_deleted",
                "updated_at",
                "created_at",
            },
        )

    logger.info(f"Prepared homework update payload: {payload}")
    return payload


@router.get("")
async def get_homeworks(
    user: UserDAO = Depends(get_user),
    db: AsyncSession = Depends(get_db),
    lesson_id: int | None = None,
) -> List[HomeworkGetSchema]:
    homework_filters = _get_homework_filters(user)

    if homework_filters is None:
        return []

    homeworks = await list_homeworks(
        db,
        lesson_id=lesson_id,
        **homework_filters,
    )
    return [_serialize_homework(homework) for homework in homeworks]


@router.get("/{homework_id}")
async def get_homework(
    homework_id: int,
    user: UserDAO = Depends(get_user),
    db: AsyncSession = Depends(get_db),
) -> HomeworkGetSchema:
    homework_filters = _get_homework_filters(user)

    if homework_filters is None:
        raise HTTPException(403, "Forbidden")

    homework = await get_homework_record(
        db,
        homework_id=homework_id,
        load_lesson=True,
        **homework_filters,
    )

    if not homework:
        raise HTTPException(404, "Homework not found")

    return _serialize_homework(homework)


@router.post("/create")
async def create_homework(
    homework: HomeworkCreateSchema,
    user: UserDAO = Depends(get_teacher),
    db: AsyncSession = Depends(get_db),
) -> HomeworkGetSchema:
    if homework.lesson_id is None:
        raise HTTPException(400, "lesson_id is required")

    try:
        homework_dao = await create_homework_record(
            db,
            lesson_id=homework.lesson_id,
            teacher_id=user.id,
            name=homework.name,
            description=homework.description,
            files_urls=homework.files_urls,
            answer=homework.answer,
            sent_files=homework.sent_files,
            deadline=homework.deadline,
        )
    except ValueError as error:
        raise HTTPException(409, str(error)) from error

    if homework_dao is None:
        raise HTTPException(404, "Lesson not found")

    return _serialize_homework(homework_dao)


@router.put("/update/{homework_id}")
async def update_homework(
    homework: HomeworkUpdateSchema,
    homework_id: int,
    user: UserDAO = Depends(get_user),
    db: AsyncSession = Depends(get_db),
) -> HomeworkGetSchema:
    logger.info(f"Received update request for homework {homework_id} with data: {homework}")

    homework_filters = _get_homework_filters(user)

    if homework_filters is None:
        raise HTTPException(403, "Forbidden")

    homework_dao = await update_homework_record(
        db,
        homework_id=homework_id,
        **homework_filters,
        **_get_homework_update_data(homework, user),
    )

    if not homework_dao:
        raise HTTPException(404, "Homework not found")

    return _serialize_homework(homework_dao)


@router.delete("/delete/{homework_id}")
async def delete_homework(
    homework_id: int,
    user: UserDAO = Depends(get_teacher),
    db: AsyncSession = Depends(get_db),
) -> int:
    homework_dao = await soft_delete_homework(
        db,
        homework_id=homework_id,
        teacher_id=user.id,
    )

    if not homework_dao:
        raise HTTPException(404, "Homework not found")

    return homework_dao.id
