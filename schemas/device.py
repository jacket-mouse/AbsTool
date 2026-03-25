from pydantic import BaseModel

class DeviceInfo(BaseModel):
    serial: str
    state: str              # "device" | "offline" | "unauthorized"
    model: str = ""
    label: str = ""         # 前端下拉框显示用
    device_type: str = ""   # "real" | "emulator"


# 按键事件
class KeyEventRequest(BaseModel):
    keycode: int
    serial: str = None  # 如果有多台设备，建议前端顺便把设备 serial 传过来



# 解析
class DumpRequest(BaseModel):
    deviceSerial: str
# 定义返回的数据格式
class DumpResponse(BaseModel):
    xml: str
    screenshot: str
    deviceWidth: int
    deviceHeight: int