# schemas/task.py
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


class TaskDto(BaseModel):
    task_id: Optional[str] = Field(default=None, alias="taskId")
    name: Optional[str] = None
    template_id: Optional[str] = Field(default=None, alias="templateId")
    cron_expression: Optional[str] = Field(default=None, alias="cronExpression")
    device_id: Optional[str] = Field(default=None, alias="deviceId")
    status: Optional[str] = None
    type: Optional[str] = None     # CRON / MANUAL
    creator: Optional[str] = None

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
    template_id: str = Field(alias="templateId")
    cron_expression: str = Field(alias="cronExpression")
    device_id: str = Field(alias="deviceId")
    type: str                      # CRON / MANUAL

    class Config:
        populate_by_name = True


class TaskUpdateRequest(BaseModel):
    task_id: str = Field(alias="taskId")
    name: Optional[str] = None
    template_id: Optional[str] = Field(default=None, alias="templateId")
    cron_expression: Optional[str] = Field(default=None, alias="cronExpression")
    device_id: Optional[str] = Field(default=None, alias="deviceId")
    status: Optional[str] = None
    type: Optional[str] = None     # CRON / MANUAL

    class Config:
        populate_by_name = True


class TaskStatusRequest(BaseModel):
    task_id: str = Field(alias="taskId")
    status: str

    class Config:
        populate_by_name = True
