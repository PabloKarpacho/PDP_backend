from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.constants import RelationStatuses
from src.schemas import normalize_datetime_to_utc, normalize_optional_string


RelationStatusValue = Literal[
    RelationStatuses.ACTIVE,
    RelationStatuses.ARCHIVED,
]


class RelationSchemaBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator(
        "teacher_id",
        "student_id",
        mode="before",
        check_fields=False,
    )
    @classmethod
    def normalize_string_fields(cls, value: str | None) -> str | None:
        return normalize_optional_string(value)

    @field_validator(
        "archived_at",
        "updated_at",
        "created_at",
        mode="after",
        check_fields=False,
    )
    @classmethod
    def normalize_datetime_fields(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return normalize_datetime_to_utc(value)


class RelationCreateSchema(RelationSchemaBase):
    student_id: str = Field(min_length=1)


class RelationGetSchema(RelationSchemaBase):
    id: int
    teacher_id: str
    student_id: str
    status: RelationStatusValue
    archived_at: datetime | None = None
    updated_at: datetime
    created_at: datetime
