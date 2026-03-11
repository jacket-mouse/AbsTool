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
        self.db.query(ScriptTemplate).filter(ScriptTemplate.template_id == template_id).delete()
        self.db.query(ScriptTemplateRel).filter(ScriptTemplateRel.template_id == template_id).delete()
        self.db.commit()

    def get_template_detail(self, template_id: str) -> TemplateDto:
        template = self.db.query(ScriptTemplate).filter(ScriptTemplate.template_id == template_id).first()
        if not template:
            raise RuntimeError("Template not found")
        return self._to_dto(template, include_scripts=True)

    def generate_python_for_template(self, template_id: str) -> str:
        from engine.python_script_generator import PythonScriptGenerator
        from services.script_service import ScriptService
        from schemas.script_editor import ScriptConfig, ScriptNode, Connection

        detail = self.get_template_detail(template_id)
        if not detail.scripts:
            raise RuntimeError("Template is empty or not found")

        script_service = ScriptService(self.db)
        gen = PythonScriptGenerator()

        merged_nodes: List[ScriptNode] = []
        merged_connections: List[Connection] = []
        prev_end_nodes: List[str] = []

        for script_dto in detail.scripts:
            script_id = script_dto.script_id
            load_res = script_service.load_script(script_id)
            if not load_res or not load_res.content:
                continue

            # load_res.content may be a dict
            content = load_res.content
            if isinstance(content, dict):
                raw_nodes = content.get("nodes", [])
                raw_conns = content.get("connections", [])
                nodes = [ScriptNode(**n) if isinstance(n, dict) else n for n in raw_nodes]
                conns = [Connection(**c) if isinstance(c, dict) else c for c in raw_conns]
            elif isinstance(content, ScriptConfig):
                nodes = content.nodes or []
                conns = content.connections or []
            else:
                continue

            if not nodes:
                continue

            in_degree = {n.id: 0 for n in nodes}
            out_degree = {n.id: 0 for n in nodes}
            for c in conns:
                out_degree[c.from_node] = out_degree.get(c.from_node, 0) + 1
                in_degree[c.to_node] = in_degree.get(c.to_node, 0) + 1

            current_start_nodes = [
                f"{script_id}_{n.id}" for n in nodes if in_degree.get(n.id, 0) == 0
            ] or [f"{script_id}_{nodes[0].id}"]

            # Link prev end nodes to current start nodes
            if prev_end_nodes:
                for prev_end in prev_end_nodes:
                    for curr_start in current_start_nodes:
                        merged_connections.append(Connection(**{"from": prev_end, "to": curr_start}))

            current_end_nodes: List[str] = []
            for n in nodes:
                old_id = n.id
                n.id = f"{script_id}_{old_id}"
                merged_nodes.append(n)
                if out_degree.get(old_id, 0) == 0:
                    current_end_nodes.append(n.id)

            for c in conns:
                c.from_node = f"{script_id}_{c.from_node}"
                c.to_node = f"{script_id}_{c.to_node}"
                merged_connections.append(c)

            prev_end_nodes = current_end_nodes

        merged_config = ScriptConfig(nodes=merged_nodes, connections=merged_connections)
        return gen.generate(merged_config)
