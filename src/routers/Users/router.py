from fastapi import APIRouter, Depends

from src.dependencies import get_user
from src.models import UserDAO
from src.routers.Users.schemas import UserGetSchema, UserMessageSchema


PREFIX = "/users"

router = APIRouter(prefix=PREFIX, tags=["Users"])


def _serialize_user(user: UserDAO) -> UserGetSchema:
    """Convert a user ORM object to API response schema."""
    return UserGetSchema(
        id=user.id,
        name=user.name,
        surname=user.surname,
        email=user.email,
        role=user.role,
        updated_at=user.updated_at,
        created_at=user.created_at,
    )


@router.get("/me", response_model=UserGetSchema)
async def get_current_user(
    user: UserDAO = Depends(get_user),
) -> UserGetSchema:
    return _serialize_user(user)
