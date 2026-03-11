# core/user_context.py

from contextvars import ContextVar
from typing import Optional

_user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)


def set_user_id(user_id: str) -> None:
    _user_id_var.set(user_id)

def get_user_id() -> Optional[str]:
    return _user_id_var.get()

def clear_user_id() -> None:
    _user_id_var.set(None)

# Alias for compatibility
get_current_user_id = get_user_id