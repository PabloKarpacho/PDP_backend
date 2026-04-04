from sqlalchemy.ext.asyncio import AsyncSession

from src.logger import logger
from src.models import UserDAO
from src.routers.Users.crud import create_user as create_user_record
from src.routers.Users.crud import get_user as get_user_record
from src.routers.Users.utils import serialize_user
from src.routers.Users.schemas import UserGetSchema
from src.schemas import KeycloakUser


def get_current_user_profile(user: UserDAO) -> UserGetSchema:
    """Serialize the authenticated user into the API schema."""
    return serialize_user(user)


async def get_or_create_user_from_keycloak(
    db: AsyncSession,
    *,
    keycloak_user: KeycloakUser,
) -> UserDAO:
    """Load the application user or create one from Keycloak claims."""
    logger.info(f"get_user called with keycloak_user.id: {keycloak_user.id}")
    user = await get_user_record(db, user_id=keycloak_user.id)

    if user is not None:
        return user

    user = await create_user_record(
        db,
        user_id=keycloak_user.id,
        name=keycloak_user.username,
        surname=keycloak_user.last_name,
        email=keycloak_user.email,
        role=keycloak_user.role,
    )
    logger.info(f"Добавили пользователя {user.id}")
    return user
