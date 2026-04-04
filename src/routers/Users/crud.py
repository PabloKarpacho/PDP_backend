from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import UserDAO


async def get_user(
    db: AsyncSession,
    *,
    user_id: str,
) -> UserDAO | None:
    """Return one application user by identifier."""
    result = await db.execute(select(UserDAO).filter_by(id=user_id))
    return result.scalar_one_or_none()


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
    user.name = name
    user.surname = surname
    user.email = email
    user.role = role
    await db.commit()
    await db.refresh(user)
    return user
