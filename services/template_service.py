# services/template_service.py
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from core.user_context import get_current_user_id
from models.script_info import ScriptInfo
from models.script_template import ScriptTemplate
from models.script_template_rel import ScriptTemplateRel
from schemas.template import (
    TemplateDto,
    TemplateListDto,
    TemplateListResponse,
    TemplateScriptDto,
)


class TemplateService:

    def __init__(self, db: Session):
        self.db = db

    def _to_list_dto(self, template: ScriptTemplate) -> TemplateListDto:
        return TemplateListDto(
            templateId=template.template_id,
            name=template.name,
            description=template.description,
            createTime=template.create_time,
        )

    def _to_detail_dto(self, template: ScriptTemplate) -> TemplateDto:
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
                    scriptId=rel.script_id,
                    sortOrder=rel.sort_order,
                    isDefault=rel.is_default,
                )
                for rel in rels
            ],
        )

    def list_templates(self, page: int, size: int, keyword: Optional[str] = None) -> TemplateListResponse:
        query = self.db.query(ScriptTemplate)

        user_id = get_current_user_id()
        if user_id:
            query = query.filter(ScriptTemplate.creator == user_id)
        if keyword:
            query = query.filter(ScriptTemplate.name.like(f"%{keyword}%"))

        query = query.order_by(desc(ScriptTemplate.create_time))
        total = query.count()
        records = query.offset((page - 1) * size).limit(size).all()
        return TemplateListResponse(list=[self._to_list_dto(item) for item in records], total=total)

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

    def update_template(
        self,
        template_id: str,
        name: Optional[str],
        description: Optional[str],
        script_ids: Optional[List[str]],
    ) -> None:
        template = self.db.query(ScriptTemplate).filter(ScriptTemplate.template_id == template_id).first()
        if not template:
            raise RuntimeError("模板不存在")

        if name is not None:
            template.name = name
        if description is not None:
            template.description = description

        if script_ids is not None:
            self.db.query(ScriptTemplateRel).filter(ScriptTemplateRel.template_id == template_id).delete()
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

    def build_script_paths_for_templates(self, template_ids: List[str]) -> list[str]:
        if not template_ids:
            raise RuntimeError("templateIds 不能为空")

        user_id = get_current_user_id()
        script_py_paths: list[str] = []

        for template_id in template_ids:
            template = self.db.query(ScriptTemplate).filter(ScriptTemplate.template_id == template_id).first()
            if not template:
                raise RuntimeError(f"模板不存在: {template_id}")
            if user_id and template.creator != user_id:
                raise RuntimeError(f"无权执行模板: {template_id}")

            rels = (
                self.db.query(ScriptTemplateRel)
                .filter(ScriptTemplateRel.template_id == template_id)
                .order_by(asc(ScriptTemplateRel.sort_order))
                .all()
            )
            if not rels:
                raise RuntimeError(f"模板下没有脚本: {template_id}")

            for rel in rels:
                script_info = self.db.query(ScriptInfo).filter(ScriptInfo.script_id == rel.script_id).first()
                if not script_info:
                    raise RuntimeError(f"脚本不存在: {rel.script_id}")
                if not script_info.latest_version:
                    raise RuntimeError(f"脚本缺少可执行版本: {rel.script_id}")
                script_py_paths.append(f"scripts/{script_info.script_id}/{script_info.latest_version}.py")

        return script_py_paths

    def _save_relations(self, template_id: str, script_ids: List[str]) -> None:
        for index, script_id in enumerate(script_ids):
            rel = ScriptTemplateRel()
            rel.template_id = template_id
            rel.script_id = script_id
            rel.sort_order = index + 1
            rel.is_default = 0
            rel.create_time = datetime.now()
            self.db.add(rel)
