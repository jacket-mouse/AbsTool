# schemas/script_editor.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Connection(BaseModel):
    from_node: str = Field(alias="from")
    to_node: str = Field(alias="to")
    from_port: Optional[str] = Field(default=None, alias="fromPort")
    to_port: Optional[str] = Field(default=None, alias="toPort")

    class Config:
        populate_by_name = True


class ScriptNode(BaseModel):
    id: str
    type: Optional[str] = None
    title: Optional[str] = None
    desc: Optional[str] = None
    loc: Optional[str] = None
    is_group: bool = Field(default=False, alias="isGroup")
    group_key: Optional[str] = Field(default=None, alias="groupKey")
    properties: Optional[Dict[str, Any]] = None

    class Config:
        populate_by_name = True


class ScriptConfig(BaseModel):
    nodes: Optional[List[ScriptNode]] = []
    connections: Optional[List[Connection]] = []


# ── Save ──────────────────────────────────────────────────────────────────────

class SaveRequest(BaseModel):
    script_id: Optional[str] = Field(default=None, alias="scriptId")
    script_name: Optional[str] = Field(default=None, alias="scriptName")
    content: ScriptConfig
    changelog: Optional[str] = None

    class Config:
        populate_by_name = True


class SaveResponse(BaseModel):
    success: bool
    script_id: Optional[str] = Field(default=None, alias="scriptId")
    version: Optional[str] = None
    message: str

    class Config:
        populate_by_name = True


# ── Validate ──────────────────────────────────────────────────────────────────

class ValidateRequest(BaseModel):
    content: Optional[ScriptConfig] = None


class ValidateResponse(BaseModel):
    valid: bool
    errors: List[str] = []


# ── Preview ───────────────────────────────────────────────────────────────────

class PreviewRequest(BaseModel):
    content: Optional[ScriptConfig] = None


class PreviewResponse(BaseModel):
    mermaid: str


# ── Load ──────────────────────────────────────────────────────────────────────

class LoadResponse(BaseModel):
    name: str
    content: Optional[Any] = None


# ── History ───────────────────────────────────────────────────────────────────

class HistoryVersionDto(BaseModel):
    version_id: str = Field(alias="versionId")
    version: str
    modify_time: str = Field(alias="modifyTime")
    summary: str

    class Config:
        populate_by_name = True


class HistoryResponse(BaseModel):
    list: List[HistoryVersionDto] = []
