# routers/emulator_router.py
from fastapi import APIRouter

from schemas.emulator import EmulatorStartRequest, EmulatorStopRequest
from services.emulator_service import EmulatorService

router = APIRouter(prefix="/api/emulator", tags=["emulator"])

emulator_service = EmulatorService()


# ─── 1. GET /api/emulator/list ── 列出所有已安装的 AVD ──────────────────────
@router.get("/list")
def list_avds():
    try:
        avds = emulator_service.list_avds()
        return {
            "success": True,
            "data": [avd.model_dump() for avd in avds],
        }
    except RuntimeError as e:
        return {"success": False, "message": str(e)}


# ─── 2. POST /api/emulator/start ── 启动模拟器 ─────────────────────────────
@router.post("/start")
async def start_avd(request: EmulatorStartRequest):
    try:
        serial = await emulator_service.start_avd(
            avd_name=request.avd_name,
            no_window=request.no_window,
            gpu=request.gpu,
        )
        return {"success": True, "data": {"serial": serial}}
    except RuntimeError as e:
        return {"success": False, "message": str(e)}


# ─── 3. POST /api/emulator/stop ── 关闭模拟器 ──────────────────────────────
@router.post("/stop")
def stop_avd(request: EmulatorStopRequest):
    success = emulator_service.stop_emulator(request.serial)
    if success:
        return {"success": True}
    else:
        return {"success": False, "message": f"关闭模拟器 {request.serial} 失败"}
