import time
from starlette.types import ASGIApp, Receive, Scope, Send
from loguru import logger


class LoggingMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # 排除 WebSocket 相关路径
        path = scope.get("path", "")
        if path.startswith("/api/ws/"):
            await self.app(scope, receive, send)
            return

        # 获取客户端 IP
        client = scope.get("client")
        client_ip = client[0] if client else "unknown"
        method = scope.get("method", "UNKNOWN")

        start_time = time.time()
        logger.info(f"==> Request: {method} {path} ({client_ip})")

        status_code = None

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
            process_time = time.time() - start_time
            if status_code is not None:
                if 200 <= status_code < 400:
                    logger.success(f"<== Response: {method} {path} | Status: {status_code} | {process_time:.3f}s")
                else:
                    logger.warning(f"<== Response: {method} {path} | Status: {status_code} | {process_time:.3f}s")
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(f"<== Response Error: {method} {path} | {process_time:.3f}s")
            raise e
