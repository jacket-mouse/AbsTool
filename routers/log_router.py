# routers/log_router.py
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.database import get_db
from schemas.log import LogListRequest
from services.log_service import LogService
from services.minio_service import MinioFileService

router = APIRouter(prefix="/api/log")


def get_log_service(db: Session = Depends(get_db)):
    return LogService(db=db)


# ─── 1. POST /api/log/list ────────────────────────────────────────────────────
@router.post("/list")
def list_logs(request: LogListRequest, service: LogService = Depends(get_log_service)):
    result = service.get_log_list(request)
    return {
        "success": True,
        "data": {
            "list": [item.model_dump(by_alias=True) for item in result.list],
            "total": result.total,
        },
    }


# ─── 2. GET /api/log/content/{logId} ─────────────────────────────────────────
@router.get("/content/{log_id}")
def get_log_content(log_id: str, service: LogService = Depends(get_log_service)):
    content = service.get_log_content(log_id)
    if content is None:
        return {"success": False, "message": "日志不存在或文件为空"}
    return {"success": True, "data": content}


# ─── 3. GET /api/log/download/{logId} ────────────────────────────────────────
@router.get("/download/{log_id}")
def download_log(log_id: str, service: LogService = Depends(get_log_service)):
    info = service.get_log_file_info(log_id)
    if info is None:
        return {"success": False, "message": "日志不存在"}

    log_file_url, filename = info
    minio = MinioFileService()
    content = minio.get_file_content(log_file_url)
    if not content:
        return {"success": False, "message": "日志文件为空或不存在"}

    data = content.encode("utf-8")
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─── 4. DELETE /api/log/delete/{logId} ───────────────────────────────────────
@router.delete("/delete/{log_id}")
def delete_log(log_id: str, service: LogService = Depends(get_log_service)):
    success = service.delete_log(log_id)
    if not success:
        return {"success": False, "message": "日志不存在"}
    return {"success": True}
