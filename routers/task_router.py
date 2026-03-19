# routers/task_router.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database import get_db
from core.user_context import get_current_user_id
from services.task_service import TaskService
from schemas.task import TaskListRequest, TaskCreateRequest, TaskUpdateRequest

router = APIRouter(prefix="/api/task")


def get_task_service(db: Session = Depends(get_db)):
    return TaskService(db=db)


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


@router.post("/create")
def create_task(request: TaskCreateRequest, service: TaskService = Depends(get_task_service)):
    try:
        user_id = get_current_user_id()
        dto = service.create_task(request, user_id)
        return {"success": True, "data": dto.model_dump(by_alias=True)}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.put("/update")
def update_task(request: TaskUpdateRequest, service: TaskService = Depends(get_task_service)):
    try:
        dto = service.update_task(request)
        if dto is None:
            return {"success": False, "message": "任务不存在"}
        return {"success": True, "data": dto.model_dump(by_alias=True)}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.delete("/delete/{task_id}")
def delete_task(task_id: str, service: TaskService = Depends(get_task_service)):
    try:
        service.delete_task(task_id)
        return {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}
