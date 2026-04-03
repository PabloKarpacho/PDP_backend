from src.models import UserDAO
from src.routers.Users.schemas import UserGetSchema


def serialize_user(user: UserDAO) -> UserGetSchema:
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
