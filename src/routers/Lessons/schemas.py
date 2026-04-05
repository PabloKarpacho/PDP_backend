from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from src.constants import LessonStatuses
from src.schemas import normalize_datetime_to_utc, normalize_optional_string


LessonStatusValue = Literal[
    LessonStatuses.ACTIVE,
    LessonStatuses.PASSED,
    LessonStatuses.CANCELLED,
]


class LessonSchemaBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator(
        "start_time",
        "end_time",
        "updated_at",
        "created_at",
        mode="after",
        check_fields=False,
    )
    @classmethod
    def normalize_datetime_fields(cls, value: datetime) -> datetime:
        return normalize_datetime_to_utc(value)

    @field_validator(
        "theme",
        "lesson_description",
        "student_id",
        "teacher_id",
        mode="before",
        check_fields=False,
    )
    @classmethod
    def normalize_string_fields(cls, value: str | None) -> str | None:
        return normalize_optional_string(value)


class LessonGetSchema(LessonSchemaBase):
    id: int
    start_time: datetime
    end_time: datetime
    theme: str | None = None
    lesson_description: str | None = None
    teacher_id: str
    student_id: str
    status: LessonStatusValue
    homework_id: int | None = None
    is_deleted: bool
    updated_at: datetime
    created_at: datetime


class LessonCreateSchema(LessonSchemaBase):
    start_time: datetime
    end_time: datetime
    theme: str | None = None
    lesson_description: str | None = None
    student_id: str
    status: LessonStatusValue = LessonStatuses.ACTIVE

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
        return self


class LessonUpdateSchema(LessonSchemaBase):
    start_time: datetime | None = None
    end_time: datetime | None = None
    theme: str | None = None
    lesson_description: str | None = None
    student_id: str | None = None
    status: LessonStatusValue | None = None

    @model_validator(mode="after")
    def validate_payload(self):
        if not self.model_fields_set:
            raise ValueError("At least one lesson field must be provided")

        if (
            self.start_time is not None
            and self.end_time is not None
            and self.start_time >= self.end_time
        ):
            raise ValueError("start_time must be before end_time")

        return self
