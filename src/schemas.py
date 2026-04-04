from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field


ResponseDataT = TypeVar("ResponseDataT")


class KeycloakUser(BaseModel):
    id: str
    username: str | None = None
    email: str
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    role: str | None = None
    realm_roles: list

    def has_role(self, role_name: str) -> bool:
        return role_name in self.realm_roles


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
