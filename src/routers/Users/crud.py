from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.logger import logger
from src.models import UserDAO
from src.schemas import KeycloakUser


async def get_user(
    db: AsyncSession,
    *,
    user_id: str,
) -> UserDAO | None:
    """Return one application user by identifier."""
    result = await db.execute(select(UserDAO).filter_by(id=user_id))
    return result.scalar_one_or_none()


async def get_or_create_user(
    db: AsyncSession,
    *,
    keycloak_user: KeycloakUser,
) -> UserDAO:
    """Return an existing application user or create one from Keycloak data."""
    logger.info(f"get_user called with keycloak_user.id: {keycloak_user.id}")
    user = await get_user(db, user_id=keycloak_user.id)

    if user is not None:
        return user

    user = UserDAO(
        id=keycloak_user.id,
        name=keycloak_user.username,
        surname=keycloak_user.last_name,
        email=keycloak_user.email,
        role=keycloak_user.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(f"Добавили пользователя {user.id}")
    return user
