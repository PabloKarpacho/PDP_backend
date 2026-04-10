from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from src.constants import normalize_role_name
from src.schemas import normalize_datetime_to_utc, normalize_optional_string


class UserBaseSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    surname: str | None
    email: EmailStr
    role: str | None
    updated_at: datetime
    created_at: datetime

    @field_validator("name", "surname", mode="before")
    @classmethod
    def normalize_name_fields(cls, value: str | None) -> str | None:
        return normalize_optional_string(value)

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role_field(cls, value: str | None) -> str | None:
        normalized_role = normalize_role_name(value)
        return normalized_role if normalized_role is not None else value

    @field_validator("updated_at", "created_at", mode="after")
    @classmethod
    def normalize_datetime_fields(cls, value: datetime) -> datetime:
        return normalize_datetime_to_utc(value)


class UserGetSchema(UserBaseSchema):
    id: str


class UserMessageSchema(BaseModel):
    message: str
