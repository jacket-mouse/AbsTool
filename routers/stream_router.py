# routers/stream_router.py
from fastapi import APIRouter, WebSocket
from adbutils import adb
from remote.scrcpy import ScrcpyServer
from loguru import logger
router = APIRouter()

@router.websocket("/api/ws/device/stream")
async def device_stream(websocket: WebSocket):
    # ★ 手动 accept，跳过 origin 校验
    await websocket.accept()

    # 获取设备
    serial = websocket.query_params.get("serial")
    logger.info(f"正在推流设备: serial {serial}")
    device = adb.device(serial)

    server = ScrcpyServer(device, version="2.7")
    try:
        await server.handle_unified_websocket(websocket)
    finally:
        server.close()