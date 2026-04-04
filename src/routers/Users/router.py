from fastapi import APIRouter, Depends

from src.dependencies import get_user
from src.models import UserDAO
from src.routers.Users.schemas import UserGetSchema
from src.schemas import ResponseEnvelope, success_response
from src.services.users import get_current_user_profile


PREFIX = "/users"

router = APIRouter(prefix=PREFIX, tags=["Users"])


@router.get("/me", response_model=ResponseEnvelope[UserGetSchema])
async def get_current_user(
    user: UserDAO = Depends(get_user),
) -> ResponseEnvelope[UserGetSchema]:
    return success_response(get_current_user_profile(user))
