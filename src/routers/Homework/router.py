from typing import List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


from src.models import HomeworkDAO, UserDAO
from src.database_control.postgres import get_db
from src.routers.Homework.schemas import (
    HomeworkCreateSchema,
    HomeworkGetSchema,
    HomeworkUpdateSchema,
)
from src.dependencies import get_user


PREFIX = "/homeworks"

router = APIRouter(prefix=PREFIX, tags=["Homeworks"])


@router.get("/{id}")
async def get_homework(
    id: int, user: UserDAO = Depends(get_user), db: AsyncSession = Depends(get_db)
) -> HomeworkGetSchema | None:
    result = await db.execute(
        select(HomeworkDAO)
        .options(selectinload(HomeworkDAO.lesson))
        .where(HomeworkDAO.id == id, HomeworkDAO.is_deleted.is_(False))
    )
    homework = result.scalar_one_or_none()

    if not homework:
        raise HTTPException(404, "Homework not found")

    lesson = homework.lesson

    if not lesson:
        raise HTTPException(404, "Homework isn't linked with any lesson")

    if (user.id == lesson.student_id) or (user.id == lesson.teacher_id):
        return HomeworkGetSchema(
            id=homework.id,
            name=homework.name,
            description=homework.description,
            files_urls=homework.files_urls,
            answer=homework.answer,
            sent_files=homework.sent_files,
            deadline=homework.deadline,
            is_deleted=homework.is_deleted,
            updated_at=homework.updated_at,
            created_at=homework.created_at,
        )
    else:
        raise HTTPException(403, "Forbidden")
