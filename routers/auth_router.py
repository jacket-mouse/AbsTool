from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database import get_db
from schemas.auth import LoginRequest, LoginResponse, RegisterRequest
from services.user_service import UserService
from schemas.common import Result

router = APIRouter(prefix="/api/auth")

# 依赖注入 UserService
def get_user_service(db: Session = Depends(get_db)):
    return UserService(db=db)


@router.post("/login", response_model=Result[LoginResponse])
def login(
        body: LoginRequest,
        user_service: UserService = Depends(get_user_service)
) -> Result[LoginResponse]:
    return Result(data=user_service.login(body))

@router.post("/register", response_model=Result[None])
def register(
        body: RegisterRequest,
        user_service: UserService = Depends(get_user_service)
) -> Result[None]:
    user_service.register(body)
    return Result(message="注册成功")
