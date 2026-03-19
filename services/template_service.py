# services/template_service.py
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import asc, desc

from models.script_template import ScriptTemplate
from models.script_template_rel import ScriptTemplateRel
from schemas.template import TemplateDto, TemplateScriptDto, TemplateListDto, TemplateListResponse


class TemplateService:

    def __init__(self, db: Session):
        self.db = db

    def _to_list_dto(self, template: ScriptTemplate) -> TemplateListDto:
        """列表查询用的精简 DTO"""
        return TemplateListDto(
            templateId=template.template_id,
            name=template.name,
            description=template.description,
            createTime=template.create_time,
        )

    def _to_detail_dto(self, template: ScriptTemplate) -> TemplateDto:
        """详情查询用的完整 DTO（含关联脚本）"""
        rels = (
            self.db.query(ScriptTemplateRel)
            .filter(ScriptTemplateRel.template_id == template.template_id)
            .order_by(asc(ScriptTemplateRel.sort_order))
            .all()
        )
        return TemplateDto(
            templateId=template.template_id,
            name=template.name,
            description=template.description,
            creator=template.creator,
            createTime=template.create_time,
            scripts=[
                TemplateScriptDto(
                    scriptId=r.script_id,
                    sortOrder=r.sort_order,
                    isDefault=r.is_default,
                )
                for r in rels
            ],
        )

    def list_templates(self, page: int, size: int, keyword: Optional[str] = None) -> TemplateListResponse:
        query = self.db.query(ScriptTemplate)
        if keyword:
            query = query.filter(ScriptTemplate.name.like(f"%{keyword}%"))
        query = query.order_by(desc(ScriptTemplate.create_time))
        total = query.count()
        records = query.offset((page - 1) * size).limit(size).all()
        return TemplateListResponse(list=[self._to_list_dto(t) for t in records], total=total)

    def create_template(self, name: str, description: Optional[str], script_ids: List[str], user_id: str) -> None:
        template = ScriptTemplate()
        template.template_id = uuid.uuid4().hex
        template.name = name
        template.description = description
        template.creator = user_id
        template.create_time = datetime.now()
        self.db.add(template)
        self.db.flush()

        self._save_relations(template.template_id, script_ids)
        self.db.commit()

    def update_template(self, template_id: str, name: Optional[str], description: Optional[str],
                        script_ids: Optional[List[str]]) -> None:
        template = self.db.query(ScriptTemplate).filter(ScriptTemplate.template_id == template_id).first()
        if not template:
            raise RuntimeError("模板不存在")

        if name is not None:
            template.name = name
        if description is not None:
            template.description = description

        if script_ids is not None:
            # 先删除旧的关联关系
            self.db.query(ScriptTemplateRel).filter(
                ScriptTemplateRel.template_id == template_id
            ).delete()
            self._save_relations(template_id, script_ids)

        self.db.commit()

    def delete_template(self, template_id: str) -> None:
        template = self.db.query(ScriptTemplate).filter(ScriptTemplate.template_id == template_id).first()
        if template:
            self.db.delete(template)
            self.db.commit()

    def get_template_detail(self, template_id: str) -> TemplateDto:
        template = self.db.query(ScriptTemplate).filter(ScriptTemplate.template_id == template_id).first()
        if not template:
            raise RuntimeError("模板不存在")
        return self._to_detail_dto(template)

    def _save_relations(self, template_id: str, script_ids: List[str]) -> None:
        """按 script_ids 数组顺序写入关联表"""
        for i, script_id in enumerate(script_ids):
            rel = ScriptTemplateRel()
            rel.template_id = template_id
            rel.script_id = script_id
            rel.sort_order = i + 1
            rel.is_default = 0
            rel.create_time = datetime.now()
            self.db.add(rel)
