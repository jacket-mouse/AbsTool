# schemas/task.py
from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class TaskDto(BaseModel):
    task_id: Optional[str] = Field(default=None, alias="taskId")
    name: Optional[str] = None
    script_id: Optional[str] = Field(default=None, alias="scriptId")
    template_id: Optional[str] = Field(default=None, alias="templateId")
    trigger_type: Optional[str] = Field(default=None, alias="triggerType")
    cron_expression: Optional[str] = Field(default=None, alias="cronExpression")
    status: Optional[str] = None
    creator: Optional[str] = None
    create_time: Optional[datetime] = Field(default=None, alias="createTime")
    start_time: Optional[datetime] = Field(default=None, alias="startTime")
    end_time: Optional[datetime] = Field(default=None, alias="endTime")

    class Config:
        populate_by_name = True


class TaskListRequest(BaseModel):
    page: int = 1
    size: int = 10
    keyword: Optional[str] = None
    status: Optional[str] = None


class TaskListResponse(BaseModel):
    list: List[TaskDto]
    total: int


class TaskCreateRequest(BaseModel):
    name: str
    script_id: Optional[str] = Field(default=None, alias="scriptId")
    template_id: Optional[str] = Field(default=None, alias="templateId")
    trigger_type: Optional[str] = Field(default=None, alias="triggerType")
    cron_expression: Optional[str] = Field(default=None, alias="cronExpression")
    creator: Optional[str] = None

    class Config:
        populate_by_name = True


class TaskUpdateRequest(BaseModel):
    task_id: str = Field(alias="taskId")
    name: Optional[str] = None
    script_id: Optional[str] = Field(default=None, alias="scriptId")
    template_id: Optional[str] = Field(default=None, alias="templateId")
    trigger_type: Optional[str] = Field(default=None, alias="triggerType")
    cron_expression: Optional[str] = Field(default=None, alias="cronExpression")

    class Config:
        populate_by_name = True


class TaskStatusRequest(BaseModel):
    task_id: str = Field(alias="taskId")
    status: str

    class Config:
        populate_by_name = True
