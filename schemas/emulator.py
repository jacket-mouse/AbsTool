# schemas/emulator.py
from typing import Optional
from pydantic import BaseModel, Field


class AvdInfo(BaseModel):
    """已安装的 AVD（Android Virtual Device）信息"""
    name: str                                   # AVD 名称，如 "Pixel_7_API_34"
    running: bool = False                       # 是否正在运行
    serial: Optional[str] = None                # 运行中时对应的 serial，如 "emulator-5554"


class EmulatorStartRequest(BaseModel):
    avd_name: str = Field(alias="avdName")      # 要启动的 AVD 名称
    no_window: bool = Field(default=True, alias="noWindow")     # 是否无窗口模式
    gpu: str = "auto"                           # GPU 模式: auto / host / swiftshader_indirect

    class Config:
        populate_by_name = True


class EmulatorStopRequest(BaseModel):
    serial: str                                 # 要关闭的模拟器 serial，如 "emulator-5554"
