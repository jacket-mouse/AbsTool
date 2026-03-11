# schemas/common.py
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional

T = TypeVar("T") # 定义泛型变量

class Result(BaseModel, Generic[T]):
    code:    int         = 200
    message: str         = "success"
    data:    Optional[T] = None