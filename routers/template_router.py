# routers/template_router.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database import get_db
from core.user_context import get_current_user_id
from services.template_service import TemplateService
from schemas.template import TemplateListRequest, TemplateCreateRequest, TemplateUpdateRequest

router = APIRouter(prefix="/api/template")


def get_template_service(db: Session = Depends(get_db)):
    return TemplateService(db=db)


@router.post("/list")
def list_templates(request: TemplateListRequest, service: TemplateService = Depends(get_template_service)):
    result = service.list_templates(request.page, request.size, request.keyword)
    return {
        "success": True,
        "data": {
            "list": [t.model_dump(by_alias=True) for t in result.list],
            "total": result.total,
        },
    }


@router.get("/detail/{template_id}")
def get_detail(template_id: str, service: TemplateService = Depends(get_template_service)):
    try:
        dto = service.get_template_detail(template_id)
        return {"success": True, "data": dto.model_dump(by_alias=True)}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/create")
def create_template(request: TemplateCreateRequest, service: TemplateService = Depends(get_template_service)):
    try:
        user_id = get_current_user_id()
        service.create_template(request.name, request.description, request.scriptIds, user_id)
        return {"success": True, "data": None}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.put("/update")
def update_template(request: TemplateUpdateRequest, service: TemplateService = Depends(get_template_service)):
    try:
        service.update_template(request.templateId, request.name, request.description, request.scriptIds)
        return {"success": True, "data": None}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.delete("/delete/{template_id}")
def delete_template(template_id: str, service: TemplateService = Depends(get_template_service)):
    try:
        service.delete_template(template_id)
        return {"success": True, "data": None}
    except Exception as e:
        return {"success": False, "message": str(e)}