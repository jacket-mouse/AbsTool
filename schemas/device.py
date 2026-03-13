from pydantic import BaseModel

class DeviceInfo(BaseModel):
    serial: str
    state: str          # "device" | "offline" | "unauthorized"
    model: str = ""
    label: str = ""     # 前端下拉框显示用


# 按键事件
class KeyEventRequest(BaseModel):
    keycode: int
    serial: str = None  # 如果有多台设备，建议前端顺便把设备 serial 传过来