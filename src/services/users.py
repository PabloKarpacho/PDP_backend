from sqlalchemy.ext.asyncio import AsyncSession

from src.logger import logger
from src.models import UserDAO
from src.routers.Users.crud import create_user as create_user_record
from src.routers.Users.crud import get_user as get_user_record
from src.routers.Users.crud import update_user as update_user_record
from src.routers.Users.utils import serialize_user
from src.routers.Users.schemas import UserGetSchema
from src.schemas import KeycloakUser


def get_current_user_profile(user: UserDAO) -> UserGetSchema:
    """Serialize the authenticated user into the API schema."""
    logger.info(
        "Serializing current user profile.",
        extra={"user_id": user.id, "role": user.role},
    )
    return serialize_user(user)


def _resolve_user_name(keycloak_user: KeycloakUser) -> str | None:
    return keycloak_user.first_name or keycloak_user.username


async def get_or_create_user_from_keycloak(
    db: AsyncSession,
    *,
    keycloak_user: KeycloakUser,
) -> UserDAO:
    """Load the application user or create one from Keycloak claims."""
    logger.info(
        "Synchronizing application user from Keycloak.",
        extra={
            "user_id": keycloak_user.id,
            "realm_roles": keycloak_user.realm_roles,
        },
    )
    user = await get_user_record(db, user_id=keycloak_user.id)

    if user is not None:
        if (
            user.name != _resolve_user_name(keycloak_user)
            or user.surname != keycloak_user.last_name
            or user.email != keycloak_user.email
            or user.role != keycloak_user.role
        ):
            logger.info(
                "Updating existing application user from Keycloak.",
                extra={"user_id": keycloak_user.id},
            )
            return await update_user_record(
                db,
                user=user,
                name=_resolve_user_name(keycloak_user),
                surname=keycloak_user.last_name,
                email=keycloak_user.email,
                role=keycloak_user.role,
            )
        logger.info(
            "Existing application user is already in sync.",
            extra={"user_id": keycloak_user.id},
        )
        return user

    logger.info(
        "Creating application user from Keycloak.",
        extra={"user_id": keycloak_user.id},
    )
    user = await create_user_record(
        db,
        user_id=keycloak_user.id,
        name=_resolve_user_name(keycloak_user),
        surname=keycloak_user.last_name,
        email=keycloak_user.email,
        role=keycloak_user.role,
    )
    logger.info(
        "Application user created.",
        extra={"user_id": user.id, "role": user.role},
    )
    return user
