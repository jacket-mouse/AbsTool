from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class ScriptListItem(BaseModel):
    script_id: str = Field(alias="scriptId", description="脚本ID")
    name: str = Field(description="脚本名称")
    type: str = Field(description="脚本类型")
    status: str = Field(description="状态")
    creator: str = Field(description="创建者")
    create_time: datetime = Field(alias="createTime", description="创建时间")
    update_time: str = Field(alias="updateTime", description="更新时间")
    latest_version: str = Field(alias="latestVersion", description="最新版本")

    class Config:
        populate_by_name = True


class ScriptListRequest(BaseModel):
    page: int = Field(default=1, description="当前页码")
    size: int = Field(default=10, description="每页条数")
    keyword: Optional[str] = Field(default=None, description="搜索关键字")
    type: Optional[str] = Field(default=None, description="脚本类型")

class ScriptListResponse(BaseModel):
    list: List[ScriptListItem] = Field(description="脚本列表")
    total: int = Field(description="总条数")


class DeleteResponse(BaseModel):
    success: bool = Field(description="是否成功")
    message: str = Field(description="提示信息")


class UpdateRequest(BaseModel):
    script_id: str = Field(alias="scriptId", description="脚本ID")
    name: str = Field(description="脚本名称")
    type: str = Field(description="脚本类型")

    class Config:
        populate_by_name = True

class UpdateResponse(BaseModel):
    success: bool = Field(description="是否成功")
    message: str = Field(description="提示信息")

