# schemas/template.py
from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class TemplateScriptDto(BaseModel):
    script_id: str = Field(alias="scriptId")
    sort_order: Optional[int] = Field(default=None, alias="sortOrder")
    is_default: Optional[int] = Field(default=None, alias="isDefault")

    class Config:
        populate_by_name = True


class TemplateDto(BaseModel):
    template_id: Optional[str] = Field(default=None, alias="templateId")
    name: Optional[str] = None
    description: Optional[str] = None
    creator: Optional[str] = None
    create_time: Optional[datetime] = Field(default=None, alias="createTime")
    scripts: Optional[List[TemplateScriptDto]] = None

    class Config:
        populate_by_name = True


class TemplateListDto(BaseModel):
    """列表查询时返回的精简 DTO（不含 creator 和 scripts）"""
    template_id: Optional[str] = Field(default=None, alias="templateId")
    name: Optional[str] = None
    description: Optional[str] = None
    create_time: Optional[datetime] = Field(default=None, alias="createTime")

    class Config:
        populate_by_name = True


class TemplateListResponse(BaseModel):
    list: List[TemplateListDto]
    total: int


class TemplateListRequest(BaseModel):
    page: int = 1
    size: int = 20
    keyword: Optional[str] = None


class TemplateCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    scriptIds: List[str] = []


class TemplateUpdateRequest(BaseModel):
    templateId: str
    name: Optional[str] = None
    description: Optional[str] = None
    scriptIds: Optional[List[str]] = None
