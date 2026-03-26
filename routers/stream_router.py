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

    server = None
    try:
        server = ScrcpyServer(device, version="2.7")
        await server.handle_unified_websocket(websocket)
    except Exception as e:
        logger.error(f"设备连接失败: {str(e)}")
        error_msg = str(e)
        if "unauthorized" in error_msg.lower():
            error_msg = "设备未授权 USB 调试，请在手机屏幕上点击「允许」后再试。"
        try:
            import json
            await websocket.send_text(json.dumps({"type": "error", "message": error_msg}))
            await websocket.close(1011, error_msg[:100])
        except Exception:
            pass
    finally:
        if server:
            server.close()