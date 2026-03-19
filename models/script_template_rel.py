from models.base import Base
from sqlalchemy import Column, DateTime, String, Integer, BigInteger, ForeignKey


class ScriptTemplateRel(Base):
    """脚本模板关联 - script_template_rel"""
    __tablename__ = "script_template_rel"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    template_id = Column(String, ForeignKey('script_template.template_id'))
    script_id = Column(String(255), ForeignKey('script_info.script_id'))
    is_default = Column(Integer)   # 1=是, 0=否
    sort_order = Column(Integer)
    create_time = Column(DateTime)

