from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserBaseSchema(BaseModel):
    name: str | None
    surname: str | None
    email: EmailStr
    role: str | None
    updated_at: datetime
    created_at: datetime


class UserGetSchema(UserBaseSchema):
    id: str


class UserMessageSchema(BaseModel):
    message: str
