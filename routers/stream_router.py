# routers/stream_router.py
from fastapi import APIRouter, WebSocket
from adbutils import adb
from remote.scrcpy import ScrcpyServer

router = APIRouter()


@router.websocket("/api/ws/device/stream")
async def device_stream(websocket: WebSocket):
    # ★ 手动 accept，跳过 origin 校验
    await websocket.accept()

    # 获取设备
    device = adb.device_list()[0]

    server = ScrcpyServer(device, version="2.7")
    try:
        await server.handle_unified_websocket(websocket)
    finally:
        server.close()