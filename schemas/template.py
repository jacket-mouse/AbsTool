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


class TemplateListResponse(BaseModel):
    list: List[TemplateDto]
    total: int
