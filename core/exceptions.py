# core/exceptions.py


class AppException(Exception):
    def __init__(self, code: int, message: str):
        self.code    = code
        self.message = message

class BusinessException(AppException):
    def __init__(self, message: str):
        super().__init__(code=400, message=message)

class NotFoundException(AppException):
    def __init__(self, message: str = "资源不存在"):
        super().__init__(code=404, message=message)

class UnauthorizedException(AppException):
    def __init__(self, message: str = "未登录或登录已过期"):
        super().__init__(code=401, message=message)