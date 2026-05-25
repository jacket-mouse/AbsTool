# routers/template_router.py
import asyncio
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy.orm import Session

from core.database import get_db
from core.user_context import get_current_user_id
from schemas.template import (
    TemplateBatchRunRequest,
    TemplateBatchRunResponse,
    TemplateCreateRequest,
    TemplateListRequest,
    TemplateUpdateRequest,
)
from services.task_run_service import execute_task
from services.template_service import TemplateService

router = APIRouter(prefix="/api/template")


def get_template_service(db: Session = Depends(get_db)):
    return TemplateService(db=db)


@router.post("/list")
def list_templates(request: TemplateListRequest, service: TemplateService = Depends(get_template_service)):
    result = service.list_templates(request.page, request.size, request.keyword)
    return {
        "success": True,
        "data": {
            "list": [item.model_dump(by_alias=True) for item in result.list],
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
    except ValueError as e:
        logger.warning(f"Delete template failed: {e}")
        return JSONResponse(status_code=404, content={"success": False, "message": str(e)})
    except RuntimeError as e:
        logger.warning(f"Delete template failed: {e}")
        return JSONResponse(status_code=409, content={"success": False, "message": str(e)})
    except Exception as e:
        logger.exception("Delete template failed")
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})


# 前端请求参数示例:
# {
#   "templateIds": ["templateId-1", "templateId-2"],
#   "deviceId": "emulator-5554"
# }
# 说明:
# 1. templateIds 必传, 按数组顺序依次执行多个模板.
# 2. deviceId 可选, 不传时默认使用 local.
# 3. 返回 runId 后, 前端可继续复用 GET /api/task/run/logs/{runId} 订阅执行日志.
@router.post("/run/batch")
async def run_template_batch(
    request: TemplateBatchRunRequest,
    service: TemplateService = Depends(get_template_service),
):
    try:
        script_py_paths = service.build_script_paths_for_templates(request.templateIds)
        run_id = uuid.uuid4().hex
        virtual_task_id = f"template_batch_{run_id}"

        asyncio.create_task(
            execute_task(
                run_id=run_id,
                task_id=virtual_task_id,
                device_id=request.deviceId or "local",
                script_py_paths=script_py_paths,
            )
        )

        response = TemplateBatchRunResponse(
            runId=run_id,
            templateCount=len(request.templateIds),
            scriptCount=len(script_py_paths),
        )
        return {"success": True, "data": response.model_dump(by_alias=True)}
    except Exception as e:
        return {"success": False, "message": str(e)}
