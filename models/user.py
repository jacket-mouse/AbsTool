from models.base import Base
from sqlalchemy import Column, DateTime, String


class SysUser(Base):
    """系统用户 - sys_user"""
    __tablename__ = "sys_user"

    user_id = Column(String, primary_key=True)
    username = Column(String)
    password = Column(String)
    nickname = Column(String)
    create_time = Column(DateTime)