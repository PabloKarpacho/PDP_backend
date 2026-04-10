from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field, model_validator

from src.constants import (
    normalize_realm_roles,
    resolve_authoritative_role,
    role_matches,
)


ResponseDataT = TypeVar("ResponseDataT")


class KeycloakUser(BaseModel):
    id: str
    username: str | None = None
    email: str
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    role: str | None = None
    realm_roles: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_role_authority(cls, value):
        if not isinstance(value, dict):
            return value

        payload = dict(value)
        payload["realm_roles"] = normalize_realm_roles(payload.get("realm_roles"))
        payload["role"] = resolve_authoritative_role(payload["realm_roles"])
        return payload

    def has_role(self, role_name: str) -> bool:
        return any(role_matches(role, role_name) for role in self.realm_roles)


class authConfiguration(BaseModel):
    server_url: str
    realm: str
    client_id: str
    client_secret: str
    authorization_url: str
    token_url: str


class PaginationMetadata(BaseModel):
    page: int | None = None
    page_size: int | None = None
    total_items: int | None = None
    total_pages: int | None = None


class ResponseMetadata(BaseModel):
    pagination: PaginationMetadata | None = None


class ErrorModel(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ResponseEnvelope(BaseModel, Generic[ResponseDataT]):
    success: bool
    data: ResponseDataT | None = None
    error: ErrorModel | None = None
    meta: ResponseMetadata = Field(default_factory=ResponseMetadata)


class HealthStatusSchema(BaseModel):
    status: str


def normalize_datetime_to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value.astimezone(UTC)


def normalize_optional_string(value: str | None) -> str | None:
    if value is None:
        return None

    normalized_value = value.strip()
    return normalized_value or None


def normalize_string_list(
    values: list[str] | None,
    *,
    field_name: str,
) -> list[str] | None:
    if values is None:
        return None

    normalized_values: list[str] = []
    for value in values:
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError(f"{field_name} must not be blank")
        normalized_values.append(normalized_value)

    return normalized_values


def success_response(
    data: Any,
    *,
    pagination: PaginationMetadata | None = None,
) -> ResponseEnvelope[Any]:
    return ResponseEnvelope(
        success=True,
        data=data,
        error=None,
        meta=ResponseMetadata(pagination=pagination),
    )


def error_response(
    *,
    code: str,
    message: str,
    details: Any | None = None,
    pagination: PaginationMetadata | None = None,
) -> ResponseEnvelope[Any]:
    return ResponseEnvelope(
        success=False,
        data=None,
        error=ErrorModel(
            code=code,
            message=message,
            details=details,
        ),
        meta=ResponseMetadata(pagination=pagination),
    )
