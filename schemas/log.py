# schemas/log.py
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


class LogDto(BaseModel):
    log_id: Optional[str] = Field(default=None, alias="logId")
    task_id: Optional[str] = Field(default=None, alias="taskId")
    device_id: Optional[str] = Field(default=None, alias="deviceId")
    exec_status: Optional[str] = Field(default=None, alias="execStatus")
    log_file_url: Optional[str] = Field(default=None, alias="logFileUrl")
    start_time: Optional[str] = Field(default=None, alias="startTime")
    end_time: Optional[str] = Field(default=None, alias="endTime")

    class Config:
        populate_by_name = True


class LogListRequest(BaseModel):
    page: int = 1
    size: int = 20
    keyword: Optional[str] = None       # 模糊搜索 taskId / deviceId
    exec_status: Optional[str] = Field(default=None, alias="execStatus")  # SUCCESS / FAILED / RUNNING / CANCELLED
    start_date: Optional[str] = Field(default=None, alias="startDate")    # YYYY-MM-DD
    end_date: Optional[str] = Field(default=None, alias="endDate")        # YYYY-MM-DD

    class Config:
        populate_by_name = True


class LogListResponse(BaseModel):
    list: List[LogDto]
    total: int
