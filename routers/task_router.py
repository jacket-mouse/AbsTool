# routers/task_router.py
import asyncio
import json
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import asc

from core.database import get_db
from core.user_context import get_current_user_id
from services.task_service import TaskService
from services.task_run_service import execute_task, get_run_queue, stop_run
from services.scheduler_service import add_or_update_job, remove_job
from schemas.task import TaskListRequest, TaskCreateRequest, TaskUpdateRequest
from models.task_info import TaskInfo
from models.script_template_rel import ScriptTemplateRel
from models.script_info import ScriptInfo

router = APIRouter(prefix="/api/task")


def get_task_service(db: Session = Depends(get_db)):
    return TaskService(db=db)


# ─── 1. POST /api/task/list ──────────────────────────────────────────────────
@router.post("/list")
def list_tasks(request: TaskListRequest, service: TaskService = Depends(get_task_service)):
    result = service.get_task_list(request)
    return {
        "success": True,
        "data": {
            "list": [t.model_dump(by_alias=True) for t in result.list],
            "total": result.total,
        },
    }


# ─── 2. POST /api/task/create ────────────────────────────────────────────────
@router.post("/create")
def create_task(request: TaskCreateRequest, service: TaskService = Depends(get_task_service)):
    try:
        user_id = get_current_user_id()
        dto = service.create_task(request, user_id)
        # 同步调度器：如果是 CRON 类型，注册定时 job
        add_or_update_job(dto.task_id)
        return {"success": True, "data": dto.model_dump(by_alias=True)}
    except Exception as e:
        return {"success": False, "message": str(e)}


# ─── 3. PUT /api/task/update ─────────────────────────────────────────────────
@router.put("/update")
def update_task(request: TaskUpdateRequest, service: TaskService = Depends(get_task_service)):
    try:
        dto = service.update_task(request)
        if dto is None:
            return {"success": False, "message": "任务不存在"}
        # 同步调度器：更新 cron 表达式或状态变更时刷新 job
        add_or_update_job(dto.task_id)
        return {"success": True, "data": dto.model_dump(by_alias=True)}
    except Exception as e:
        return {"success": False, "message": str(e)}


# ─── 4. DELETE /api/task/delete/{taskId} ─────────────────────────────────────
@router.delete("/delete/{task_id}")
def delete_task(task_id: str, service: TaskService = Depends(get_task_service)):
    try:
        # 先移除调度 job，再删除数据库记录
        remove_job(task_id)
        service.delete_task(task_id)
        return {"success": True, "data": None}
    except Exception as e:
        return {"success": False, "message": str(e)}


# ─── 5. POST /api/task/run/{taskId} — 启动任务 ──────────────────────────────
@router.post("/run/{task_id}")
async def run_task(task_id: str, db: Session = Depends(get_db)):
    """
    启动任务运行，立即返回 runId。
    流程：查任务 → 取 template_id → 查关联脚本 → 启动后台执行。
    """
    task = db.query(TaskInfo).filter(TaskInfo.task_id == task_id).first()
    if not task:
        return {"success": False, "message": "任务不存在"}
    if not task.template_id:
        return {"success": False, "message": "该任务未关联模板"}

    rels = (
        db.query(ScriptTemplateRel)
        .filter(ScriptTemplateRel.template_id == task.template_id)
        .order_by(asc(ScriptTemplateRel.sort_order))
        .all()
    )
    if not rels:
        return {"success": False, "message": "该任务关联的模板没有任何脚本"}

    script_py_paths = []
    for rel in rels:
        script_info = db.query(ScriptInfo).filter(ScriptInfo.script_id == rel.script_id).first()
        if not script_info:
            return {"success": False, "message": f"脚本 {rel.script_id} 不存在"}
        py_path = f"scripts/{script_info.script_id}/{script_info.latest_version}.py"
        script_py_paths.append(py_path)

    run_id = uuid.uuid4().hex

    asyncio.create_task(
        execute_task(
            run_id=run_id,
            task_id=task_id,
            device_id=task.device_id or "local",
            script_py_paths=script_py_paths,
        )
    )

    return {"success": True, "data": {"runId": run_id}}


# ─── 6. GET /api/task/run/logs/{runId} — SSE 日志流 ──────────────────────────
@router.get("/run/logs/{run_id}")
async def run_logs_sse(run_id: str):
    """
    SSE 端点：前端通过 EventSource 订阅，实时接收任务运行日志。
    每条数据格式：data: {"type":"info|success|warning|error|finished","message":"..."}
    收到 type=finished 后前端应关闭连接。
    """

    async def event_generator():
        queue = get_run_queue(run_id)

        # 等待队列创建（后台任务可能还没启动完毕）
        retry_count = 0
        while queue is None and retry_count < 50:
            await asyncio.sleep(0.1)
            queue = get_run_queue(run_id)
            retry_count += 1

        if queue is None:
            yield f"data: {json.dumps({'type': 'error', 'message': '运行实例不存在或已结束'}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'finished', 'message': '连接关闭'}, ensure_ascii=False)}\n\n"
            return

        while True:
            msg = await queue.get()
            if msg is None:
                # 兜底：如果收到 None 也发 finished
                yield f"data: {json.dumps({'type': 'finished', 'message': '运行已结束'}, ensure_ascii=False)}\n\n"
                break
            yield f"data: {msg}\n\n"
            # 检查是否是 finished 事件
            try:
                parsed = json.loads(msg)
                if parsed.get("type") == "finished":
                    break
            except Exception:
                pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ─── 7. POST /api/task/stop/{runId} — 停止运行中的任务 ───────────────────────
@router.post("/stop/{run_id}")
def stop_task(run_id: str):
    """
    停止正在运行的任务实例。
    会杀掉当前正在执行的子进程，后台协程会完成日志上传和数据库写入。
    """
    success = stop_run(run_id)
    if success:
        return {"success": True, "data": None}
    else:
        return {"success": False, "message": "运行实例不存在或已结束"}
