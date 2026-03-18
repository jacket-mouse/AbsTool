from schemas.script import ScriptListResponse, UpdateRequest, UpdateResponse, ScriptListRequest, DeleteResponse
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database import get_db
from services.script_service import ScriptService
from schemas.common import Result


router = APIRouter(prefix="/api/script")

# 依赖注入
def get_script_service(db: Session = Depends(get_db)):
    return ScriptService(db=db)

@router.post("/list", response_model=Result[ScriptListResponse])
def list_scripts(request: ScriptListRequest, service: ScriptService = Depends(get_script_service)):
    return Result(data=service.get_script_list(request))


@router.delete("/delete/{script_id}", response_model=Result[DeleteResponse])
def delete_script(
        script_id: str,
        service: ScriptService = Depends(get_script_service)
) -> Result[DeleteResponse]:
    service.delete_script(script_id)
    return Result(data=DeleteResponse(success=True, message="删除成功"))


@router.put("/update", response_model=Result[UpdateResponse])
def update_script(
        body: UpdateRequest,
        service: ScriptService = Depends(get_script_service)
) -> Result[UpdateResponse]:
    service.update_script(body)
    return Result(data=UpdateResponse(success=True, message="更新成功"))