from models.base import Base
from sqlalchemy import Column, DateTime, String, Text, ForeignKey

class ScriptInfo(Base):
    """脚本信息 - script_info"""
    __tablename__ = "script_info"

    script_id = Column(String, primary_key=True)
    name = Column(String)
    type = Column(String)          # GENERAL / CUSTOM
    content = Column(Text)
    status = Column(String)        # ENABLED / DISABLED
    creator = Column(String, ForeignKey("sys_user.user_id"))
    create_time = Column(DateTime)
    latest_version = Column(String)
