from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import get_user_info
from src.constants import Roles
from src.database_control.postgres import get_db
from src.logger import logger
from src.models import UserDAO
from src.schemas import KeycloakUser
from src.services.users import get_or_create_user_from_keycloak


def _require_keycloak_role(keycloak_user: KeycloakUser, required_role: str) -> None:
    if keycloak_user.has_role(required_role):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Forbidden",
    )


async def get_user(
    keycloak_user: KeycloakUser = Depends(get_user_info),
    db: AsyncSession = Depends(get_db),
) -> UserDAO:
    """Return the current authenticated application user.

    Args:
        keycloak_user: User data extracted from the Keycloak token.
        db: Active async database session.

    Returns:
        Application user entity from the local database.
    """
    logger.info(f"get_user dependency called with keycloak_user.id: {keycloak_user.id}")
    return await get_or_create_user_from_keycloak(keycloak_user=keycloak_user, db=db)


async def get_teacher(
    keycloak_user: KeycloakUser = Depends(get_user_info),
    db: AsyncSession = Depends(get_db),
) -> UserDAO:
    """Return the current user only if Keycloak marks them as a teacher.

    Args:
        keycloak_user: User data extracted from the Keycloak token.
        db: Active async database session.

    Raises:
        HTTPException: If the user does not have the teacher role in Keycloak.

    Returns:
        Application user entity from the local database.
    """
    _require_keycloak_role(keycloak_user, Roles.TEACHER)
    return await get_or_create_user_from_keycloak(keycloak_user=keycloak_user, db=db)


async def get_student(
    keycloak_user: KeycloakUser = Depends(get_user_info),
    db: AsyncSession = Depends(get_db),
) -> UserDAO:
    _require_keycloak_role(keycloak_user, Roles.STUDENT)
    return await get_or_create_user_from_keycloak(keycloak_user=keycloak_user, db=db)
