from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.logger import logger
from src.models import UserDAO


async def get_user(
    db: AsyncSession,
    *,
    user_id: str,
) -> UserDAO | None:
    """Return one application user by identifier."""
    logger.info(
        "Loading user from database.",
        extra={"user_id": user_id},
    )
    result = await db.execute(select(UserDAO).filter_by(id=user_id))
    user = result.scalar_one_or_none()
    logger.info(
        "User database lookup completed.",
        extra={"user_id": user_id, "user_found": user is not None},
    )
    return user


async def create_user(
    db: AsyncSession,
    *,
    user_id: str,
    name: str | None,
    surname: str | None,
    email: str,
    role: str | None,
) -> UserDAO:
    """Create a new application user record."""
    logger.info(
        "Creating user in database.",
        extra={"user_id": user_id, "role": role},
    )
    user = UserDAO(
        id=user_id,
        name=name,
        surname=surname,
        email=email,
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info(
        "User created in database.",
        extra={"user_id": user.id, "role": user.role},
    )
    return user


async def update_user(
    db: AsyncSession,
    *,
    user: UserDAO,
    name: str | None,
    surname: str | None,
    email: str,
    role: str | None,
) -> UserDAO:
    logger.info(
        "Updating user in database.",
        extra={"user_id": user.id, "role": role},
    )
    user.name = name
    user.surname = surname
    user.email = email
    user.role = role
    await db.commit()
    await db.refresh(user)
    logger.info(
        "User updated in database.",
        extra={"user_id": user.id, "role": user.role},
    )
    return user
