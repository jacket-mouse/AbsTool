# middleware/auth_middleware.py

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from core.user_context import set_user_id, clear_user_id
from utils.jwt import JwtUtils


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        if token:
            try:
                payload = JwtUtils.parse_token(token)
                set_user_id(payload.get("user_id"))
            except Exception:
                pass

        response = await call_next(request)
        clear_user_id()  # 请求结束后清理，等价于 Java 的 finally clear()
        return response