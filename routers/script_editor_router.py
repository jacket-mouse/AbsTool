# routers/script_editor_router.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database import get_db
from services.script_service import ScriptService
from schemas.script_editor import (
    SaveRequest, SaveResponse,
    ValidateRequest, ValidateResponse,
    PreviewRequest, PreviewResponse,
    LoadResponse, HistoryResponse,
)

router = APIRouter(prefix="/api/script/editor")


def get_script_service(db: Session = Depends(get_db)):
    return ScriptService(db=db)


@router.post("/save", response_model=SaveResponse)
def save_script(request: SaveRequest, service: ScriptService = Depends(get_script_service)):
    return service.save_script(request)


@router.post("/validate", response_model=ValidateResponse)
def validate_script(request: ValidateRequest, service: ScriptService = Depends(get_script_service)):
    return service.validate_script(request)


@router.post("/preview", response_model=PreviewResponse)
def preview_script(request: PreviewRequest, service: ScriptService = Depends(get_script_service)):
    return service.preview_script(request)


@router.get("/load/{script_id}", response_model=LoadResponse)
def load_script(script_id: str, service: ScriptService = Depends(get_script_service)):
    return service.load_script(script_id)


@router.get("/load/{script_id}/{version_id}", response_model=LoadResponse)
def load_script_version(script_id: str, version_id: str, service: ScriptService = Depends(get_script_service)):
    return service.load_script_version(script_id, version_id)


@router.get("/history/{script_id}", response_model=HistoryResponse)
def get_history(script_id: str, service: ScriptService = Depends(get_script_service)):
    return service.get_script_history(script_id)
