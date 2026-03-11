# services/task_service.py
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import desc

from models.task_info import TaskInfo
from schemas.task import TaskDto, TaskListRequest, TaskListResponse, TaskCreateRequest, TaskUpdateRequest


class TaskService:

    def __init__(self, db: Session):
        self.db = db

    def _to_dto(self, task: TaskInfo) -> TaskDto:
        return TaskDto(
            taskId=task.task_id,
            name=task.name,
            scriptId=task.script_id,
            templateId=task.template_id,
            triggerType=task.trigger_type,
            cronExpression=task.cron_expression,
            status=task.status,
            creator=task.creator,
            createTime=task.create_time,
            startTime=task.start_time,
            endTime=task.end_time,
        )

    def get_task_list(self, request: TaskListRequest) -> TaskListResponse:
        query = self.db.query(TaskInfo)
        if request.keyword:
            query = query.filter(TaskInfo.name.like(f"%{request.keyword}%"))
        if request.status:
            query = query.filter(TaskInfo.status == request.status)
        query = query.order_by(desc(TaskInfo.create_time))
        total = query.count()
        records = query.offset((request.page - 1) * request.size).limit(request.size).all()
        return TaskListResponse(list=[self._to_dto(t) for t in records], total=total)

    def create_task(self, request: TaskCreateRequest) -> TaskDto:
        task = TaskInfo()
        task.task_id = uuid.uuid4().hex
        task.name = request.name
        task.script_id = request.script_id
        task.template_id = request.template_id
        task.trigger_type = request.trigger_type
        task.cron_expression = request.cron_expression
        task.status = "PENDING"
        task.creator = request.creator
        task.create_time = datetime.now()
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
        if request.script_id is not None:
            task.script_id = request.script_id
        if request.template_id is not None:
            task.template_id = request.template_id
        if request.trigger_type is not None:
            task.trigger_type = request.trigger_type
        if request.cron_expression is not None:
            task.cron_expression = request.cron_expression
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
            if status == "RUNNING":
                task.start_time = datetime.now()
            elif status in ("COMPLETED", "FAILED"):
                task.end_time = datetime.now()
            self.db.commit()

    def get_task_detail(self, task_id: str) -> Optional[TaskDto]:
        task = self.db.query(TaskInfo).filter(TaskInfo.task_id == task_id).first()
        if not task:
            return None
        return self._to_dto(task)
