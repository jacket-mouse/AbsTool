# schemas/task.py
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


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
    template_id: Optional[str] = Field(default=None, alias="templateId")
    cron_expression: Optional[str] = Field(default=None, alias="cronExpression")
    device_id: Optional[str] = Field(default="local", alias="deviceId")
    type: str                      # CRON / MANUAL

    @field_validator("template_id", "cron_expression", "device_id", mode="before")
    @classmethod
    def blank_to_none(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("type", mode="before")
    @classmethod
    def normalize_type(cls, value):
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @model_validator(mode="after")
    def validate_by_type(self):
        if self.type not in {"CRON", "MANUAL"}:
            raise ValueError("type must be CRON or MANUAL")
        if not self.template_id:
            raise ValueError("templateId is required")
        if self.type == "CRON" and not self.cron_expression:
            raise ValueError("cronExpression is required when type is CRON")
        if self.type == "MANUAL" and self.cron_expression is None:
            self.cron_expression = ""
        if not self.device_id:
            self.device_id = "local"
        return self

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
