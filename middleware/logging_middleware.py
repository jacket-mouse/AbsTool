import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 排除对 WebSocket 和一些无关紧要的静态文件的拦截（按需保留）
        if request.url.path.startswith("/api/ws/"):
            return await call_next(request)

        start_time = time.time()
        client_ip = request.client.host if request.client else "unknown"
        
        # 1. 在接口执行前，输出 Request 信息
        logger.info(f"==> Request: {request.method} {request.url.path} ({client_ip})")
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # 2. 在接口执行后返回前，输出 Response 摘要信息
            # 如果成功，用 success，否则用 warning
            if 200 <= response.status_code < 400:
                logger.success(f"<== Response: {request.method} {request.url.path} | Status: {response.status_code} | {process_time:.3f}s")
            else:
                logger.warning(f"<== Response: {request.method} {request.url.path} | Status: {response.status_code} | {process_time:.3f}s")
                
            return response
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(f"<== Response Error: {request.method} {request.url.path} | {process_time:.3f}s")
            raise e
