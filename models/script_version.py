from models.base import Base
from sqlalchemy import Column, DateTime, String, Text, ForeignKey


class ScriptVersion(Base):
    """脚本版本 - script_version"""
    __tablename__ = "script_version"

    version_id = Column(String, primary_key=True)
    script_id = Column(String, ForeignKey("script_info.script_id"))
    version = Column(String)
    content = Column(Text)
    modifier = Column(String, ForeignKey("sys_user.user_id"))
    modify_time = Column(DateTime)
    change_log = Column(String)
