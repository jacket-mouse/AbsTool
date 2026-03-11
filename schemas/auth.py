# schemas/auth_router.py
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token:    str
    user_id:  str
    username: str
    nickname: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    nickname: str