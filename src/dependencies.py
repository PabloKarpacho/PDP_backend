from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import get_user_info
from src.database_control.postgres import get_db
from src.logger import logger
from src.models import UserDAO
from src.schemas import KeycloakUser


async def get_user(
    keycloak_user: KeycloakUser = Depends(get_user_info), 
    db: AsyncSession = Depends(get_db)
) -> UserDAO:
    logger.info(f"get_user called with keycloak_user.id: {keycloak_user.id}")
    result = await db.execute(select(UserDAO).filter_by(id=keycloak_user.id))
    user = result.scalar_one_or_none()

    if not user:
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
