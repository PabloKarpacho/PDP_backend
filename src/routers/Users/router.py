from fastapi import APIRouter, Depends

from src.dependencies import get_user
from src.models import UserDAO
from src.routers.Users.schemas import UserGetSchema
from src.services.users import get_current_user_profile


PREFIX = "/users"

router = APIRouter(prefix=PREFIX, tags=["Users"])


@router.get("/me", response_model=UserGetSchema)
async def get_current_user(
    user: UserDAO = Depends(get_user),
) -> UserGetSchema:
    return get_current_user_profile(user)
