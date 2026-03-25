# services/emulator_service.py
import os
import subprocess
import asyncio
from typing import List, Dict

from loguru import logger
from schemas.emulator import AvdInfo

# Android SDK 路径（macOS 默认安装位置）
ANDROID_SDK = os.getenv("ANDROID_HOME", os.path.expanduser("~/Library/Android/sdk"))
EMULATOR_BIN = os.path.join(ANDROID_SDK, "emulator", "emulator")
ADB_BIN = os.path.join(ANDROID_SDK, "platform-tools", "adb")


class EmulatorService:
    """Android 模拟器（AVD）生命周期管理"""

    # 记录由本服务启动的模拟器子进程，key=avd_name
    _processes: Dict[str, asyncio.subprocess.Process] = {}

    @staticmethod
    def _get_running_emulators() -> Dict[str, str]:
        """
        获取当前所有运行中的模拟器，返回 {serial: avd_name} 的映射。
        通过 'adb -s <serial> emu avd name' 获取每个 emulator 的 AVD 名称。
        """
        mapping: Dict[str, str] = {}
        try:
            result = subprocess.run(
                [ADB_BIN, "devices"], capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.strip().splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 2 and parts[0].startswith("emulator-") and parts[1] == "device":
                    serial = parts[0]
                    try:
                        avd_result = subprocess.run(
                            [ADB_BIN, "-s", serial, "emu", "avd", "name"],
                            capture_output=True, text=True, timeout=5
                        )
                        avd_name = avd_result.stdout.strip().splitlines()[0] if avd_result.stdout.strip() else ""
                        if avd_name:
                            mapping[serial] = avd_name
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"获取运行中模拟器失败: {e}")
        return mapping

    def list_avds(self) -> List[AvdInfo]:
        """列出本机已安装的所有 AVD，并标记哪些正在运行"""
        # 1. 获取已安装的 AVD 列表
        try:
            result = subprocess.run(
                [EMULATOR_BIN, "-list-avds"], capture_output=True, text=True, timeout=10
            )
            avd_names = [name.strip() for name in result.stdout.strip().splitlines() if name.strip()]
        except FileNotFoundError:
            raise RuntimeError(
                f"未找到 emulator 命令（路径: {EMULATOR_BIN}），"
                f"请安装 Android Studio 或设置 ANDROID_HOME 环境变量"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("列出 AVD 超时")

        # 2. 获取正在运行的模拟器 {serial: avd_name}
        running = self._get_running_emulators()
        # 反转为 {avd_name: serial}
        running_by_name = {v: k for k, v in running.items()}

        # 3. 组装结果
        avds = []
        for name in avd_names:
            serial = running_by_name.get(name)
            avds.append(AvdInfo(
                name=name,
                running=serial is not None,
                serial=serial,
            ))
        return avds

    async def start_avd(self, avd_name: str, no_window: bool = True, gpu: str = "auto") -> str:
        """
        启动指定 AVD，返回模拟器 serial。
        使用 asyncio 子进程后台启动，不阻塞主线程。
        """
        # 检查是否已经在运行
        running = self._get_running_emulators()
        running_by_name = {v: k for k, v in running.items()}
        if avd_name in running_by_name:
            return running_by_name[avd_name]

        # 构建启动命令
        cmd = [EMULATOR_BIN, "-avd", avd_name, "-gpu", gpu, "-no-audio"]
        if no_window:
            cmd.append("-no-window")

        logger.info(f"启动模拟器: {' '.join(cmd)}")

        # 后台启动，不等待完成
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        self._processes[avd_name] = process

        # 等待模拟器上线（轮询 adb devices，最多等 60 秒）
        serial = await self._wait_for_boot(avd_name, timeout=60)
        if not serial:
            # 超时则杀掉进程
            process.kill()
            self._processes.pop(avd_name, None)
            raise RuntimeError(f"模拟器 {avd_name} 启动超时（60秒），请检查 AVD 配置")

        logger.info(f"模拟器 {avd_name} 已上线: {serial}")
        return serial

    async def _wait_for_boot(self, avd_name: str, timeout: int = 60) -> str:
        """轮询等待模拟器在 adb devices 中出现并完成启动"""
        elapsed = 0
        while elapsed < timeout:
            await asyncio.sleep(2)
            elapsed += 2
            running = self._get_running_emulators()
            running_by_name = {v: k for k, v in running.items()}
            if avd_name in running_by_name:
                serial = running_by_name[avd_name]
                # 检查 boot 是否完成
                try:
                    result = subprocess.run(
                        [ADB_BIN, "-s", serial, "shell", "getprop", "sys.boot_completed"],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.stdout.strip() == "1":
                        return serial
                except Exception:
                    pass
        return ""

    @staticmethod
    def stop_emulator(serial: str) -> bool:
        """通过 adb emu kill 关闭指定模拟器"""
        try:
            subprocess.run(
                [ADB_BIN, "-s", serial, "emu", "kill"],
                capture_output=True, text=True, timeout=10
            )
            logger.info(f"模拟器 {serial} 已关闭")
            return True
        except Exception as e:
            logger.error(f"关闭模拟器 {serial} 失败: {e}")
            return False
