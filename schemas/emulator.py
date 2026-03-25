# schemas/emulator.py
from typing import Optional
from pydantic import BaseModel, Field


class EmulatorInfo(BaseModel):
    """模拟器容器信息"""
    container_id: str = Field(alias="containerId")          # Docker 容器 ID（短）
    name: str                                                # 容器名称
    android_version: str = Field(alias="androidVersion")     # Android 版本，如 "12.0"
    status: str                                              # running / stopped / creating / pulling / booting
    adb_serial: Optional[str] = Field(default=None, alias="adbSerial")  # ADB 连接地址，如 "127.0.0.1:5556"
    adb_port: Optional[int] = Field(default=None, alias="adbPort")      # 映射的 ADB 端口

    class Config:
        populate_by_name = True


class EmulatorCreateRequest(BaseModel):
    name: str                                                # 容器名称（用户自定义）
    android_version: str = Field(default="12.0", alias="androidVersion")  # 可选 Android 版本

    class Config:
        populate_by_name = True


class EmulatorStopRequest(BaseModel):
    container_id: str = Field(alias="containerId")

    class Config:
        populate_by_name = True


class EmulatorDeleteRequest(BaseModel):
    container_id: str = Field(alias="containerId")

    class Config:
        populate_by_name = True
