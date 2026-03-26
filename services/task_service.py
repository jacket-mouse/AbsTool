# services/task_service.py
import uuid
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import desc

from models.task_info import TaskInfo
from schemas.task import TaskDto, TaskListRequest, TaskListResponse, TaskCreateRequest, TaskUpdateRequest
from core.user_context import get_current_user_id


class TaskService:

    def __init__(self, db: Session):
        self.db = db

    def _to_dto(self, task: TaskInfo) -> TaskDto:
        return TaskDto(
            taskId=task.task_id,
            name=task.name,
            templateId=task.template_id,
            cronExpression=task.cron_expression,
            deviceId=task.device_id,
            status=task.status,
            type=task.type,
            creator=task.creator,
        )

    def get_task_list(self, request: TaskListRequest) -> TaskListResponse:
        query = self.db.query(TaskInfo)
        # 按当前登录用户过滤
        user_id = get_current_user_id()
        if user_id:
            query = query.filter(TaskInfo.creator == user_id)
        if request.keyword:
            query = query.filter(TaskInfo.name.like(f"%{request.keyword}%"))
        if request.status:
            query = query.filter(TaskInfo.status == request.status)
        total = query.count()
        records = query.offset((request.page - 1) * request.size).limit(request.size).all()
        return TaskListResponse(list=[self._to_dto(t) for t in records], total=total)

    def create_task(self, request: TaskCreateRequest, user_id: str) -> TaskDto:
        task = TaskInfo()
        task.task_id = uuid.uuid4().hex
        task.name = request.name
        task.template_id = request.template_id
        task.cron_expression = request.cron_expression
        task.device_id = request.device_id
        task.status = "ENABLE"
        task.type = request.type
        task.creator = user_id
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return self._to_dto(task)

    def update_task(self, request: TaskUpdateRequest) -> Optional[TaskDto]:
        task = self.db.query(TaskInfo).filter(TaskInfo.task_id == request.task_id).first()
        if not task:
            return None
        if request.name is not None:
            task.name = request.name
        if request.template_id is not None:
            task.template_id = request.template_id
        if request.cron_expression is not None:
            task.cron_expression = request.cron_expression
        if request.device_id is not None:
            task.device_id = request.device_id
        if request.status is not None:
            task.status = request.status
        if request.type is not None:
            task.type = request.type
        self.db.commit()
        self.db.refresh(task)
        return self._to_dto(task)

    def delete_task(self, task_id: str) -> None:
        self.db.query(TaskInfo).filter(TaskInfo.task_id == task_id).delete()
        self.db.commit()

    def update_task_status(self, task_id: str, status: str) -> None:
        task = self.db.query(TaskInfo).filter(TaskInfo.task_id == task_id).first()
        if task:
            task.status = status
            self.db.commit()

    def get_task_detail(self, task_id: str) -> Optional[TaskDto]:
        task = self.db.query(TaskInfo).filter(TaskInfo.task_id == task_id).first()
        if not task:
            return None
        return self._to_dto(task)
