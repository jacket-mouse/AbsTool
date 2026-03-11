from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from core.exceptions import AppException
from middleware.auth_middleware import AuthMiddleware
from middleware.logging_middleware import LoggingMiddleware
from routers import auth_router, script_router, script_editor_router, task_router, template_router, generator_router, device_inspector_router
from ws_handlers.script_debug_ws import script_debug_ws_handler
from ws_handlers.task_execute_ws import task_execute_ws_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化定时任务调度器
    from scheduler.task_scheduler import task_scheduler_manager
    task_scheduler_manager.init_from_db()
    yield
    # 关闭时停止调度器
    from scheduler.task_scheduler import task_scheduler_manager
    task_scheduler_manager.shutdown()


app = FastAPI(lifespan=lifespan)


# 全局异常处理器
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    logger.warning(f"⚠️ [业务异常] {request.method} {request.url.path} -> {exc.message}")
    return JSONResponse(status_code=exc.code, content={"code": exc.code, "message": exc.message, "data": None})


# 捕获所有未处理的异常，只打印关键信息，防止输出长篇大论的错误追踪
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_msg = f"{exc.__class__.__name__}: {str(exc)}"
    logger.exception(f"💥 {request.method} {request.url.path} 引发服务器内部异常")
    return JSONResponse(status_code=500, content={"code": 500, "message": "服务器内部错误", "error": error_msg, "data": None})


# 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT 认证中间件
app.add_middleware(AuthMiddleware)

# 日志中间件 (由于 FastAPI 中间件执行栈是后进先出，所以日志要放在更外层包装)
app.add_middleware(LoggingMiddleware)

# 注册 REST 路由
app.include_router(auth_router.router)
app.include_router(script_router.router)
app.include_router(script_editor_router.router)
app.include_router(task_router.router)
app.include_router(template_router.router)
app.include_router(generator_router.router)
app.include_router(device_inspector_router.router)


# WebSocket 端点
@app.websocket("/api/ws/script/debug")
async def ws_script_debug(websocket: WebSocket):
    await script_debug_ws_handler(websocket)


@app.websocket("/api/ws/task/execute")
async def ws_task_execute(websocket: WebSocket):
    await task_execute_ws_handler(websocket)


if __name__ == "__main__":
    import uvicorn
    # 配置 reload_excludes 排除特定文件或文件夹触发重启
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8080, 
        reload=True,
        reload_excludes=["engine/script_template.py", "*.log"]
    )
