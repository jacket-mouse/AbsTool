from models.base import Base
from sqlalchemy import Column, DateTime, String



class ScriptTemplate(Base):
    """脚本模板 - script_template"""
    __tablename__ = "script_template"

    template_id = Column(String, primary_key=True, name="templateId")
    name = Column(String)
    description = Column(String)
    creator = Column(String)
    create_time = Column(DateTime, name="createTime")


