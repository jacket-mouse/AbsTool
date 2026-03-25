# routers/emulator_router.py
from fastapi import APIRouter

from schemas.emulator import EmulatorCreateRequest, EmulatorStopRequest, EmulatorDeleteRequest
from services.emulator_service import EmulatorService

router = APIRouter(prefix="/api/emulator", tags=["emulator"])

emulator_service = EmulatorService()


# ─── 1. GET /api/emulator/list ── 列出所有模拟器容器（含创建中的）──────────
@router.get("/list")
def list_emulators():
    try:
        emulators = emulator_service.list_emulators()
        return {"success": True, "data": emulators}
    except RuntimeError as e:
        return {"success": False, "message": str(e)}


# ─── 2. GET /api/emulator/versions ── 支持的 Android 版本 ───────────────────
@router.get("/versions")
def get_versions():
    return {"success": True, "data": emulator_service.get_available_versions()}


# ─── 3. POST /api/emulator/create ── 创建模拟器（立即返回，后台执行）────────
@router.post("/create")
def create_emulator(request: EmulatorCreateRequest):
    try:
        result = emulator_service.create_emulator(
            name=request.name,
            android_version=request.android_version,
        )
        return {"success": True, "data": result}
    except RuntimeError as e:
        return {"success": False, "message": str(e)}


# ─── 4. POST /api/emulator/start ── 启动已停止的模拟器 ──────────────────────
@router.post("/start")
def start_emulator(request: EmulatorStopRequest):
    try:
        info = emulator_service.start_emulator(request.container_id)
        return {"success": True, "data": info.model_dump(by_alias=True)}
    except RuntimeError as e:
        return {"success": False, "message": str(e)}


# ─── 5. POST /api/emulator/stop ── 停止模拟器 ──────────────────────────────
@router.post("/stop")
def stop_emulator(request: EmulatorStopRequest):
    try:
        success = emulator_service.stop_emulator(request.container_id)
        if success:
            return {"success": True}
        return {"success": False, "message": "停止模拟器失败"}
    except RuntimeError as e:
        return {"success": False, "message": str(e)}


# ─── 6. DELETE /api/emulator/delete ── 删除模拟器 ──────────────────────────
@router.delete("/delete")
def delete_emulator(request: EmulatorDeleteRequest):
    try:
        success = emulator_service.delete_emulator(request.container_id)
        if success:
            return {"success": True}
        return {"success": False, "message": "删除模拟器失败"}
    except RuntimeError as e:
        return {"success": False, "message": str(e)}
