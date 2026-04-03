from datetime import datetime
from pydantic import BaseModel


class HomeworkBaseSchema(BaseModel):
    name: str | None
    description: str | None
    files_urls: list[str] | None
    answer: str | None
    sent_files: list[str] | None
    deadline: datetime | None
    lesson_id: int | None
    is_deleted: bool
    updated_at: datetime
    created_at: datetime


class HomeworkGetSchema(HomeworkBaseSchema):
    id: int


class HomeworkCreateSchema(HomeworkBaseSchema):
    pass


class HomeworkUpdateSchema(HomeworkBaseSchema):
    pass
