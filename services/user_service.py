# services/user_service.py
from datetime import datetime
from uuid import uuid4
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from core.exceptions import BusinessException
from models.user import SysUser
from schemas.auth import LoginRequest, RegisterRequest, LoginResponse
from utils.jwt import JwtUtils

pwd_context = CryptContext(schemes=["bcrypt"])

class UserService:
    def __init__(self, db: Session):
        self.db  = db

    def login(self, request: LoginRequest) -> LoginResponse:
        # 1. 根据用户名查询用户
        user = self.db.query(SysUser).filter(
            SysUser.username == request.username
        ).first()

        # 2. 校验用户是否存在
        if not user:
            raise BusinessException("用户不存在")

        # 3. 校验密码
        if not pwd_context.verify(request.password, user.password):
            raise BusinessException("密码错误")

        # 4. 生成 Token
        token = JwtUtils.generate_token(user.user_id, user.username)

        # 5. 返回结果
        return LoginResponse(
            token    = token,
            user_id  = user.user_id,
            username = user.username,
            nickname = user.nickname
        )

    def register(self, request: RegisterRequest) -> None:
        # 1. 检查用户名是否存在
        exists = self.db.query(SysUser).filter(
            SysUser.username == request.username
        ).first()
        if exists:
            raise BusinessException("用户名已存在")

        # 2. 创建用户
        user = SysUser(
            user_id     = uuid4().hex,
            username    = request.username,
            password    = pwd_context.hash(request.password),
            nickname    = request.nickname,
            create_time = datetime.now()
        )

        # 3. 保存
        self.db.add(user)
        self.db.commit()