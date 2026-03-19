from models.base import Base
from sqlalchemy import Column, String, ForeignKey


class TaskInfo(Base):
    """任务信息 - task_info"""
    __tablename__ = "task_info"

    task_id = Column(String, primary_key=True)
    name = Column(String)
    template_id = Column(String, ForeignKey("script_template.template_id"))
    creator = Column(String)
    cron_expression = Column(String)
    device_id = Column(String)
    status = Column(String)
    type = Column(String)          # CRON / MANUAL
