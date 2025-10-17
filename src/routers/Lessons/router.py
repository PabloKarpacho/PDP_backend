import datetime
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from src.config import CONFIG
from src.logger import logger

from src.models import LessonDAO, UserDAO
from src.database_control.db import get_db
from src.dependencies import get_user
from src.constants import Roles
from src.routers.Lessons.schemas import LessonGetSchema, LessonCreateSchema, LessonUpdateSchema


PREFIX = "/lessons"

router = APIRouter(prefix=PREFIX, tags=["Lessons"])


@router.get("")
def get_lessons(
    user: UserDAO = Depends(get_user),
    db: Session = Depends(get_db),
    start_time: datetime.datetime | None = None,
    end_time: datetime.datetime | None = None,
) -> List[LessonGetSchema | None]:

    # base query by role
    if user.role == Roles.STUDENT:
        query = db.query(LessonDAO).filter(
            LessonDAO.student_id == user.id, LessonDAO.is_deleted == False
        )
    elif user.role == Roles.TEACHER:
        query = db.query(LessonDAO).filter(
            LessonDAO.teacher_id == user.id, LessonDAO.is_deleted == False
        )

    # time range filters
    if start_time is not None:
        query = query.filter(LessonDAO.start_time >= start_time)
    if end_time is not None:
        query = query.filter(LessonDAO.end_time <= end_time)

    lessons = query.all()

    result = []

    if lessons:
        result = [
            LessonGetSchema(
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
            for lesson in lessons
        ]

    return result


@router.post("/create")
def create_lesson(
    lesson: LessonCreateSchema,
    user: UserDAO = Depends(get_user),
    db: Session = Depends(get_db),
) -> LessonGetSchema:
    if user.role == Roles.STUDENT:
        raise HTTPException(403, "Forbidden")

    if user.role == Roles.TEACHER:
        lesson_dao = LessonDAO(
            start_time=lesson.start_time,
            end_time=lesson.end_time,
            theme=lesson.theme,
            lesson_description=lesson.lesson_description,
            teacher_id=user.id,
            student_id=lesson.student_id,
            status=lesson.status,
        )
        db.add(lesson_dao)
        db.commit()

        db.refresh(lesson_dao)

        lesson_schema = LessonGetSchema(
            id=lesson_dao.id,
            start_time=lesson_dao.start_time,
            end_time=lesson_dao.end_time,
            theme=lesson_dao.theme,
            lesson_description=lesson_dao.lesson_description,
            teacher_id=lesson_dao.teacher_id,
            student_id=lesson_dao.student_id,
            status=lesson_dao.status,
            homework_id=lesson_dao.homework_id,
            is_deleted=lesson_dao.is_deleted,
            updated_at=lesson_dao.updated_at,
            created_at=lesson_dao.created_at,
        )

        return lesson_schema


@router.put("/update/{lesson_id}")
def update_lesson(
    lesson: LessonUpdateSchema,
    lesson_id: int,
    user: UserDAO = Depends(get_user),
    db: Session = Depends(get_db),
) -> LessonGetSchema:
    if user.role == Roles.STUDENT:
        raise HTTPException(403, "Forbidden")

    if user.role == Roles.TEACHER:
        lesson_dao = db.query(LessonDAO).filter(LessonDAO.id == lesson_id).first()

        if not lesson_dao:
            raise HTTPException(404, "Lesson not found")

        update_data = lesson.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(lesson_dao, field, value)

        db.commit()
        db.refresh(lesson_dao)

        lesson_schema = LessonGetSchema(
            id=lesson_dao.id,
            start_time=lesson_dao.start_time,
            end_time=lesson_dao.end_time,
            theme=lesson_dao.theme,
            lesson_description=lesson_dao.lesson_description,
            teacher_id=lesson_dao.teacher_id,
            student_id=lesson_dao.student_id,
            status=lesson_dao.status,
            homework_id=lesson_dao.homework_id,
            is_deleted=lesson_dao.is_deleted,
            updated_at=lesson_dao.updated_at,
            created_at=lesson_dao.created_at,
        )
        return lesson_schema


@router.delete("/delete/{lesson_id}")
def delete_lesson(
    lesson_id: int,
    user: UserDAO = Depends(get_user),
    db: Session = Depends(get_db),
) -> int:
    if user.role == Roles.STUDENT:
        raise HTTPException(403, "Forbidden")

    if user.role == Roles.TEACHER:
        lesson_dao = db.query(LessonDAO).filter(LessonDAO.id == lesson_id).first()

        if not lesson_dao:
            raise HTTPException(404, "Lesson not found")

        lesson_dao.is_deleted = True

        if lesson_dao.homework:
            lesson_dao.homework.is_deleted = True

        db.commit()

        return lesson_dao.id