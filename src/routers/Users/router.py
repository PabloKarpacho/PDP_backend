
from fastapi import APIRouter, Depends

from src.models import UserDAO

from src.auth import get_user_info


router = APIRouter(prefix="/users", tags=["Users"]) 

@router.get("/")
async def root():
    return {"message": "Hello World"}

@router.get("/secure")
async def root(user: UserDAO = Depends(get_user_info)):
    return {"message": f"Hello {user.email}"}

