from models.base import Base
from sqlalchemy import Column, DateTime, String


class TaskInfo(Base):
    """任务信息 - task_info"""
    __tablename__ = "task_info"

    task_id = Column(String, primary_key=True)
    name = Column(String)
    script_id = Column(String)
    template_id = Column(String)
    trigger_type = Column(String)
    cron_expression = Column(String)
    status = Column(String)
    create_time = Column(DateTime)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    creator = Column(String)
