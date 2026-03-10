from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ──────────────────────────────────────────────
# ScriptExecLog
# ──────────────────────────────────────────────
class ScriptExecLogBase(BaseModel):
    script_id: Optional[str] = None
    task_id: Optional[str] = None
    step_name: Optional[str] = None
    status: Optional[str] = None       # SUCCESS / FAIL
    error_msg: Optional[str] = None
    exec_time: Optional[datetime] = None
    duration: Optional[int] = None     # ms


class ScriptExecLogCreate(ScriptExecLogBase):
    log_id: str


class ScriptExecLogOut(ScriptExecLogBase):
    log_id: str

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# ScriptInfo
# ──────────────────────────────────────────────
class ScriptInfoBase(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None         # GENERAL / CUSTOM
    content: Optional[str] = None      # JSON 格式
    status: Optional[str] = None       # ENABLED / DISABLED
    creator: Optional[str] = None
    create_time: Optional[datetime] = None
    latest_version: Optional[str] = None


class ScriptInfoCreate(ScriptInfoBase):
    script_id: str


class ScriptInfoOut(ScriptInfoBase):
    script_id: str

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# ScriptTemplate
# ──────────────────────────────────────────────
class ScriptTemplateBase(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    creator: Optional[str] = None
    create_time: Optional[datetime] = None


class ScriptTemplateCreate(ScriptTemplateBase):
    template_id: str


class ScriptTemplateOut(ScriptTemplateBase):
    template_id: str

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# ScriptTemplateRel
# ──────────────────────────────────────────────
class ScriptTemplateRelBase(BaseModel):
    template_id: Optional[str] = None
    script_id: Optional[str] = None
    is_default: Optional[int] = None   # 1=是, 0=否
    sort_order: Optional[int] = None
    create_time: Optional[datetime] = None


class ScriptTemplateRelCreate(ScriptTemplateRelBase):
    pass


class ScriptTemplateRelOut(ScriptTemplateRelBase):
    id: int

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# ScriptVersion
# ──────────────────────────────────────────────
class ScriptVersionBase(BaseModel):
    script_id: Optional[str] = None
    version: Optional[str] = None
    content: Optional[str] = None
    modifier: Optional[str] = None     # 用户 ID
    modify_time: Optional[datetime] = None
    change_log: Optional[str] = None


class ScriptVersionCreate(ScriptVersionBase):
    version_id: str


class ScriptVersionOut(ScriptVersionBase):
    version_id: str

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# SysUser
# ──────────────────────────────────────────────
class SysUserBase(BaseModel):
    username: Optional[str] = None
    nickname: Optional[str] = None
    create_time: Optional[datetime] = None


class SysUserCreate(SysUserBase):
    user_id: str
    password: str


class SysUserOut(SysUserBase):
    user_id: str
    # password 不对外暴露

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# TaskInfo
# ──────────────────────────────────────────────
class TaskInfoBase(BaseModel):
    name: Optional[str] = None
    script_id: Optional[str] = None
    template_id: Optional[str] = None
    trigger_type: Optional[str] = None
    cron_expression: Optional[str] = None
    status: Optional[str] = None
    create_time: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    creator: Optional[str] = None


class TaskInfoCreate(TaskInfoBase):
    task_id: str


class TaskInfoOut(TaskInfoBase):
    task_id: str

    model_config = {"from_attributes": True}
