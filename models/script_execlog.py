from models.base import Base
from sqlalchemy import Column, DateTime, String


class ScriptExecLog(Base):
    """脚本执行日志 - script_exec_log"""
    __tablename__ = "script_exec_log"

    log_id = Column(String, primary_key=True)
    task_id = Column(String)
    device_id = Column(String)
    exec_status = Column(String)
    log_file_url = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
