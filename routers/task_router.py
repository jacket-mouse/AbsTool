# routers/task_router.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database import get_db
from services.task_service import TaskService
from schemas.task import (
    TaskDto, TaskListRequest, TaskListResponse,
    TaskCreateRequest, TaskUpdateRequest, TaskStatusRequest,
)
from schemas.common import Result

router = APIRouter(prefix="/api/task")


def get_task_service(db: Session = Depends(get_db)):
    return TaskService(db=db)


@router.post("/list")
def list_tasks(request: TaskListRequest, service: TaskService = Depends(get_task_service)):
    result = service.get_task_list(request)
    return {"success": True, "data": {"list": [t.model_dump(by_alias=True) for t in result.list], "total": result.total}}


@router.post("/create")
def create_task(request: TaskCreateRequest, service: TaskService = Depends(get_task_service)):
    try:
        dto = service.create_task(request)
        # Notify scheduler if SCHEDULED type
        from scheduler.task_scheduler import task_scheduler_manager
        if dto.trigger_type == "SCHEDULED" and dto.cron_expression:
            task_scheduler_manager.schedule_task(dto.task_id, dto.cron_expression)
        return {"success": True, "data": dto.model_dump(by_alias=True)}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.delete("/delete/{task_id}")
def delete_task(task_id: str, service: TaskService = Depends(get_task_service)):
    try:
        service.delete_task(task_id)
        from scheduler.task_scheduler import task_scheduler_manager
        task_scheduler_manager.cancel_task(task_id)
        return {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/update")
def update_task(request: TaskUpdateRequest, service: TaskService = Depends(get_task_service)):
    try:
        dto = service.update_task(request)
        from scheduler.task_scheduler import task_scheduler_manager
        if dto and dto.trigger_type == "SCHEDULED" and dto.cron_expression:
            task_scheduler_manager.schedule_task(dto.task_id, dto.cron_expression)
        elif dto:
            task_scheduler_manager.cancel_task(dto.task_id)
        return {"success": True, "data": dto.model_dump(by_alias=True) if dto else None}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/updateStatus")
def update_task_status(request: TaskStatusRequest, service: TaskService = Depends(get_task_service)):
    try:
        service.update_task_status(request.task_id, request.status)
        return {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}
