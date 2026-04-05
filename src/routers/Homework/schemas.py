from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.schemas import (
    normalize_datetime_to_utc,
    normalize_optional_string,
    normalize_string_list,
)


class HomeworkSchemaBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator(
        "deadline",
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

    @field_validator("name", "description", "answer", mode="before", check_fields=False)
    @classmethod
    def normalize_text_fields(cls, value: str | None) -> str | None:
        return normalize_optional_string(value)

    @field_validator("files_urls", "sent_files", mode="before", check_fields=False)
    @classmethod
    def normalize_file_lists(cls, value: list[str] | None) -> list[str] | None:
        return normalize_string_list(value, field_name="File references")


class HomeworkGetSchema(HomeworkSchemaBase):
    id: int
    name: str | None = None
    description: str | None = None
    files_urls: list[str] | None = None
    answer: str | None = None
    sent_files: list[str] | None = None
    deadline: datetime | None = None
    lesson_id: int | None = None
    is_deleted: bool
    updated_at: datetime
    created_at: datetime


class HomeworkCreateSchema(HomeworkSchemaBase):
    lesson_id: int = Field(gt=0)
    name: str | None = None
    description: str | None = None
    files_urls: list[str] | None = None
    deadline: datetime | None = None


class HomeworkUpdateSchema(HomeworkSchemaBase):
    name: str | None = None
    description: str | None = None
    files_urls: list[str] | None = None
    answer: str | None = None
    sent_files: list[str] | None = None
    deadline: datetime | None = None

    @model_validator(mode="after")
    def validate_payload(self):
        if not self.model_fields_set:
            raise ValueError("At least one homework field must be provided")
        return self
