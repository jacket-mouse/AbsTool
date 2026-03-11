# routers/template_router.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional

from core.database import get_db
from services.template_service import TemplateService
from schemas.template import TemplateDto

router = APIRouter(prefix="/api/template")


def get_template_service(db: Session = Depends(get_db)):
    return TemplateService(db=db)


@router.post("/list")
def list_templates(body: dict, service: TemplateService = Depends(get_template_service)):
    page = int(body.get("page", 1))
    size = int(body.get("size", 10))
    keyword: Optional[str] = body.get("keyword")
    result = service.list_templates(page, size, keyword)
    return {
        "success": True,
        "data": {
            "list": [t.model_dump(by_alias=True) for t in result.list],
            "total": result.total,
        },
    }


@router.post("/save")
def save_template(dto: TemplateDto, service: TemplateService = Depends(get_template_service)):
    try:
        user_id = dto.creator or "anonymous"
        service.save_template(dto, user_id)
        return {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.delete("/delete/{template_id}")
def delete_template(template_id: str, service: TemplateService = Depends(get_template_service)):
    try:
        service.delete_template(template_id)
        return {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.get("/detail/{template_id}")
def get_detail(template_id: str, service: TemplateService = Depends(get_template_service)):
    try:
        dto = service.get_template_detail(template_id)
        return {"success": True, "data": dto.model_dump(by_alias=True)}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.get("/python/{template_id}")
def generate_python(template_id: str, service: TemplateService = Depends(get_template_service)):
    try:
        return service.generate_python_for_template(template_id)
    except Exception as e:
        return f"# Generate Error: {e}"
