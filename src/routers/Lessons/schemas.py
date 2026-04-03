from typing import Literal
from pydantic import BaseModel
from datetime import datetime
from src.constants import LessonStatuses


class LessonBaseSchema(BaseModel):
    start_time: datetime
    end_time: datetime
    theme: str | None
    lesson_description: str | None
    teacher_id: str
    student_id: str
    status: Literal[
        LessonStatuses.ACTIVE, LessonStatuses.PASSED, LessonStatuses.CANCELLED
    ]
    homework_id: int | None
    is_deleted: bool
    updated_at: datetime
    created_at: datetime


class LessonGetSchema(LessonBaseSchema):
    id: int


class LessonCreateSchema(LessonBaseSchema):
    pass


class LessonUpdateSchema(LessonBaseSchema):
    pass
