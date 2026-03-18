# services/template_service.py
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import asc, desc

from models.script_template import ScriptTemplate
from models.script_template_rel import ScriptTemplateRel
from schemas.template import TemplateDto, TemplateScriptDto, TemplateListResponse


class TemplateService:

    def __init__(self, db: Session):
        self.db = db

    def _to_dto(self, template: ScriptTemplate, include_scripts: bool = False) -> TemplateDto:
        dto = TemplateDto(
            templateId=template.template_id,
            name=template.name,
            description=template.description,
            creator=template.creator,
            createTime=template.create_time,
        )
        if include_scripts:
            rels = (
                self.db.query(ScriptTemplateRel)
                .filter(ScriptTemplateRel.template_id == template.template_id)
                .order_by(asc(ScriptTemplateRel.sort_order))
                .all()
            )
            dto.scripts = [
                TemplateScriptDto(scriptId=r.script_id, sortOrder=r.sort_order, isDefault=r.is_default)
                for r in rels
            ]
        return dto

    def list_templates(self, page: int, size: int, keyword: Optional[str] = None) -> TemplateListResponse:
        query = self.db.query(ScriptTemplate)
        if keyword:
            query = query.filter(ScriptTemplate.name.like(f"%{keyword}%"))
        query = query.order_by(desc(ScriptTemplate.create_time))
        total = query.count()
        records = query.offset((page - 1) * size).limit(size).all()
        return TemplateListResponse(list=[self._to_dto(t) for t in records], total=total)

    def save_template(self, dto: TemplateDto, user_id: str) -> None:
        is_new = not dto.template_id
        if is_new:
            template = ScriptTemplate()
            template.template_id = uuid.uuid4().hex
            template.create_time = datetime.now()
            template.creator = user_id
            dto.template_id = template.template_id
        else:
            template = self.db.query(ScriptTemplate).filter(ScriptTemplate.template_id == dto.template_id).first()
            if not template:
                raise RuntimeError("Template not found")

        template.name = dto.name
        template.description = dto.description

        if is_new:
            self.db.add(template)
            self.db.flush()
        else:
            # Delete old relationships
            self.db.query(ScriptTemplateRel).filter(
                ScriptTemplateRel.template_id == template.template_id
            ).delete()

        # Save new relationships
        if dto.scripts:
            for i, script_dto in enumerate(dto.scripts):
                rel = ScriptTemplateRel()
                rel.template_id = template.template_id
                rel.script_id = script_dto.script_id
                rel.sort_order = script_dto.sort_order if script_dto.sort_order is not None else i + 1
                rel.is_default = script_dto.is_default if script_dto.is_default is not None else 0
                rel.create_time = datetime.now()
                self.db.add(rel)

        self.db.commit()

    def delete_template(self, template_id: str) -> None:
        # 1. 先把主表对象查出来，加载到内存里
        template = self.db.query(ScriptTemplate).filter(ScriptTemplate.template_id == template_id).first()

        if template:
            # 2. 将对象交给 db.delete()，这会完美触发你配置的 cascade="all, delete"！
            self.db.delete(template)
            self.db.commit()

    def get_template_detail(self, template_id: str) -> TemplateDto:
        template = self.db.query(ScriptTemplate).filter(ScriptTemplate.template_id == template_id).first()
        if not template:
            raise RuntimeError("Template not found")
        return self._to_dto(template, include_scripts=True)

    def generate_python_for_template(self, template_id: str) -> str:
        return
