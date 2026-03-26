import subprocess
import uiautomator2 as u2
import base64
import io
from fastapi import APIRouter, HTTPException
from typing import List
import adbutils
from schemas.device import DeviceInfo, KeyEventRequest, DumpResponse, DumpRequest

router = APIRouter(prefix="/api/device", tags=["device"])

@router.get("/list", response_model=List[DeviceInfo])
async def list_devices():
    try:
        result = subprocess.run(
            [adbutils.adb_path(), "devices", "-l"],
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

        # 区分真机和模拟器
        device_type = "emulator" if serial.startswith("emulator-") else "real"
        type_label = "模拟器" if device_type == "emulator" else "真机"
        label = f"{model} ({type_label}) [{serial}]" if model else f"({type_label}) [{serial}]"

        devices.append(DeviceInfo(
            serial=serial,
            state=state,
            model=model,
            label=label,
            device_type=device_type,
        ))

    return devices


@router.post("/keyevent")
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


@router.post("/dump-ui", response_model=DumpResponse)
def dump_ui(req: DumpRequest):
    """
    处理前端的 POST 请求，抓取 UI 树和截图
    """
    if (not req.deviceSerial):
        raise HTTPException(status_code=400, detail="设备序列号不能为空")

    try:
        # 连接指定设备
        d = u2.connect(req.deviceSerial)

        # 抓取 XML (compressed=False 保证获取完整节点)
        xml_content = d.dump_hierarchy(compressed=False)

        # 抓取截图 (返回 PIL Image 对象)
        image = d.screenshot()

        # 获取设备的真实屏幕分辨率 (基于截图的宽高是最准确的，能直接用于前端 Canvas 比例计算)
        device_width = image.width
        device_height = image.height

        # 将截图转为 Base64
        buffered = io.BytesIO()
        # 注意：因为你的前端硬编码了 `data:image/png`，这里必须保存为 PNG 格式。
        # 如果觉得接口响应慢，建议前端改成 image/jpeg，这里 format="JPEG", quality=80 压缩处理
        image.save(buffered, format="PNG")

        # 获取纯 Base64 字符串 (不带 data:image 前缀，交由前端拼接)
        img_bytes = base64.b64encode(buffered.getvalue())
        img_str = img_bytes.decode("utf-8")

        return DumpResponse(
            screenshot=img_str,
            xml=xml_content,
            deviceWidth=device_width,
            deviceHeight=device_height
        )

    except Exception as e:
        # 捕获类似设备离线、u2 服务崩溃等异常
        raise HTTPException(status_code=500, detail=f"Dump UI 失败: {str(e)}")