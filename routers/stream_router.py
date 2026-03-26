# routers/stream_router.py
import json

from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect
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

    server = None
    try:
        device = adb.device(serial)
        server = ScrcpyServer(device, version="2.7")
        await server.handle_unified_websocket(websocket)
    except WebSocketDisconnect:
        logger.info(f"推流 WebSocket 正常断开: serial={serial}")
    except Exception as e:
        logger.error(f"推流异常: {e}")
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
            await websocket.close(1011, str(e)[:100])
        except Exception:
            pass
    finally:
        if server:
            server.close()
        # 确保 WebSocket 关闭，避免遗留连接
        try:
            await websocket.close()
        except Exception:
            pass