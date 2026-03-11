from models.base import Base
from sqlalchemy import Column, DateTime, String, Integer


class ScriptExecLog(Base):
    """脚本执行日志 - script_exec_log"""
    __tablename__ = "script_exec_log"

    log_id = Column(String, primary_key=True)
    script_id = Column(String)
    task_id = Column(String)
    step_name = Column(String)
    status = Column(String)        # SUCCESS / FAIL
    error_msg = Column(String)
    exec_time = Column(DateTime)
    duration = Column(Integer)     # ms
