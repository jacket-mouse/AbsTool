# utils/jwt.py
from datetime import datetime, timedelta, timezone
from jose import jwt
import os


SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM  = "HS256"
EXPIRE_DAYS = 7

class JwtUtils:
    @staticmethod
    def generate_token(user_id: str, username: str) -> str:
        payload = {
            "user_id":  user_id,
            "username": username,
            "exp":      datetime.now(timezone.utc) + timedelta(days=EXPIRE_DAYS)
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    @staticmethod
    def parse_token(token: str) -> dict:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])