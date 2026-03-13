import subprocess
from fastapi import APIRouter, HTTPException
from typing import List
import adbutils
from schemas.device import DeviceInfo, KeyEventRequest
router = APIRouter(prefix="/api/device", tags=["device"])

@router.get("/list", response_model=List[DeviceInfo])
async def list_devices():
    try:
        result = subprocess.run(
            ["adb", "devices", "-l"],
            capture_output=True,
            text=True,
            timeout=10
        )
    except FileNotFoundError:
        # adb 不在 PATH
        return []
    except subprocess.TimeoutExpired:
        return []

    devices: List[DeviceInfo] = []
    lines = result.stdout.strip().splitlines()

    # 第一行是 "List of devices attached"，跳过
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue

        parts = line.split()
        if len(parts) < 2:
            continue

        serial = parts[0]
        state  = parts[1]

        # -l 额外信息：model:Pixel_6 product:oriole transport_id:1
        model = ""
        for part in parts[2:]:
            if part.startswith("model:"):
                model = part.removeprefix("model:").replace("_", " ")
                break

        label = f"{model}  [{serial}]" if model else serial

        devices.append(DeviceInfo(
            serial=serial,
            state=state,
            model=model,
            label=label,
        ))

    return devices


@router.get("/keyevent")
async def trigger_keyevent(req: KeyEventRequest):
    try:
        # 2. 获取设备实例
        if req.serial:
            device = adbutils.adb.device(req.serial)
        else:
            # 如果没传 serial，默认连第一台设备
            device = adbutils.adb.device_list()[0]

        # 3. 核心执行逻辑：通过 ADB 发送按键事件
        # 4 是返回，3 是主页，187 是最近任务
        device.shell(f"input keyevent {req.keycode}")

        return {"success": True, "message": f"成功发送按键 {req.keycode}"}

    except IndexError:
        raise HTTPException(status_code=400, detail="未检测到任何在线设备")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"按键执行失败: {str(e)}")