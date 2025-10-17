from fastapi import Depends
from sqlalchemy.orm import Session

from src.auth import get_user_info
from src.database_control.db import get_db
from src.logger import logger
from src.models import UserDAO
from src.schemas import KeycloakUser


def get_user(
    keycloak_user: KeycloakUser = Depends(get_user_info), 
    db: Session = Depends(get_db)
) -> UserDAO:
    logger.info(f"get_user called with keycloak_user.id: {keycloak_user.id}")
    user = db.query(UserDAO).filter_by(id=keycloak_user.id).first()

    if not user:
        user = UserDAO(
            id=keycloak_user.id,
            name=keycloak_user.username,
            surname=keycloak_user.last_name,
            email=keycloak_user.email,
            role=keycloak_user.role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        logger.info(f"Добавили пользователя {user.id}")

    return user