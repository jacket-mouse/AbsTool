import asyncio
import json
from loguru import logger
import os
import socket
import struct
from pathlib import Path
from typing import Optional

import retry
from adbutils import AdbError, Network, adb
from adbutils._adb import AdbConnection
from adbutils._device import AdbDevice
from starlette.websockets import WebSocket, WebSocketDisconnect

from uiautodev.remote.touch_controller import ScrcpyTouchController
from remote.android_input import KeyeventAction, MetaState



class ScrcpyServer:
    """
    ScrcpyServer class is responsible for managing the scrcpy server on Android devices.
    It handles the initialization, communication, and control of the scrcpy server,
    including video streaming and touch control.
    """

    def __init__(self, device: AdbDevice, version: Optional[str] = "2.7"):
        """
        Initializes the ScrcpyServer instance.

        Args:
            device (AdbDevice): The ADB device instance to use.
            version (str, optional): Scrcpy server version to use. Defaults to "2.7".
        """
        self.scrcpy_jar_path = Path(__file__).parent.joinpath(f'../binaries/scrcpy-server-v{version}.jar')
        if self.scrcpy_jar_path.exists() is False:
            raise FileNotFoundError(f"Scrcpy server JAR not found: {self.scrcpy_jar_path}")
        self.device = device
        self.version = version
        self.resolution_width = 0  # scrcpy 投屏转换宽度
        self.resolution_height = 0  # scrcpy 投屏转换高度

        self._shell_conn: AdbConnection
        self._video_conn: socket.socket
        self._control_conn: socket.socket

        self._setup_connection()

    def _setup_connection(self):
        self._shell_conn = self._start_scrcpy_server(control=True)
        self._video_conn = self._connect_scrcpy(self.device)
        self._control_conn = self._connect_scrcpy(self.device)
        self._parse_scrcpy_info(self._video_conn)
        
        self.controller = ScrcpyTouchController(self._control_conn)

    @retry.retry(exceptions=AdbError, tries=20, delay=0.1)
    def _connect_scrcpy(self, device: AdbDevice) -> socket.socket:
        return device.create_connection(Network.LOCAL_ABSTRACT, 'scrcpy')

    def _parse_scrcpy_info(self, conn: socket.socket):
        dummy_byte = conn.recv(1)
        if not dummy_byte or dummy_byte != b"\x00":
            raise ConnectionError("Did not receive Dummy Byte!")
        logger.debug('Received Dummy Byte!')
        # print('Received Dummy Byte!')
        if self.version == '3.3.3': # 临时处理一下, 3.3.3使用WebCodec来接码，前端解析分辨率
            return
        device_name = conn.recv(64).decode('utf-8').rstrip('\x00')
        logger.debug(f'Device name: {device_name}')
        codec = conn.recv(4)
        logger.debug(f'resolution_data: {codec}')
        resolution_data = conn.recv(8)
        logger.debug(f'resolution_data: {resolution_data}')
        self.resolution_width, self.resolution_height = struct.unpack(">II", resolution_data)
        logger.debug(f'Resolution: {self.resolution_width}x{self.resolution_height}')

    def close(self):
        """关闭所有连接，并杀掉设备上的 scrcpy 进程，确保下次重连时端口干净"""
        try:
            self._control_conn.close()
        except Exception:
            pass
        try:
            self._video_conn.close()
        except Exception:
            pass
        try:
            self._shell_conn.close()
        except Exception:
            pass
        # 杀掉设备端 scrcpy 进程，释放 local abstract socket
        try:
            self.device.shell('pkill -f scrcpy', check=False)
        except Exception:
            pass

    def __del__(self):
        self.close()

    def _start_scrcpy_server(self, control: bool = True) -> AdbConnection:
        """
        Pushes the scrcpy server JAR file to the Android device and starts the scrcpy server.

        Args:
            control (bool, optional): Whether to enable touch control. Defaults to True.

        Returns:
            AdbConnection
        """
        # 获取设备对象
        device = self.device

        # 杀掉所有旧的 scrcpy 进程，释放 local abstract socket 端口
        # 必须等待进程完全退出，否则新连接会接收到残留的 H.264 数据流，导致画面错位
        try:
            device.shell('pkill -9 -f scrcpy', check=False)
        except Exception:
            pass
        import time
        time.sleep(0.5)  # 等待进程退出 & socket 释放
        # 二次确认：如果还有残留进程，再杀一次
        try:
            result = device.shell('pgrep -f scrcpy', check=False)
            if result and result.strip():
                device.shell('kill -9 ' + result.strip().replace('\n', ' '), check=False)
                time.sleep(0.3)
        except Exception:
            pass

        # 推送 scrcpy 服务器到设备
        device.sync.push(self.scrcpy_jar_path, '/data/local/tmp/scrcpy_server.jar', check=True)
        logger.info('scrcpy server JAR pushed to device')

        # 构建启动 scrcpy 服务器的命令
        cmds = [
            'CLASSPATH=/data/local/tmp/scrcpy_server.jar',
            'app_process', '/',
            f'com.genymobile.scrcpy.Server', self.version,
            'log_level=info',
            'video_bit_rate=16000000', 'tunnel_forward=true',
            'send_frame_meta=true',
            f'control={"true" if control else "false"}',
            'audio=false', 'show_touches=false', 'stay_awake=false',
            'power_off_on_close=false', 'clipboard_autosync=false'
        ]
        conn = device.shell(' '.join(cmds), stream=True)
        logger.debug("scrcpy output: %s", conn.conn.recv(100))
        return conn  # type: ignore

    async def handle_unified_websocket(self, websocket: WebSocket, serial=''):
        logger.info(f"[Unified] WebSocket connection from {websocket} for serial: {serial}")

        # 先发送分辨率信息，前端用于设置画布宽高比
        await websocket.send_text(json.dumps({
            "type": "resolution",
            "width": self.resolution_width,
            "height": self.resolution_height,
        }))

        video_task = asyncio.create_task(self._stream_video_to_websocket(self._video_conn, websocket))
        control_task = asyncio.create_task(self._handle_control_websocket(websocket))

        try:
            done, pending = await asyncio.wait(
                [video_task, control_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
            # 某一端结束后，取消另一端
            for task in pending:
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass
            # 检查已完成的任务是否有异常需要记录
            for task in done:
                if task.exception() and not isinstance(task.exception(), (WebSocketDisconnect, asyncio.CancelledError)):
                    logger.warning(f"[Unified] Task ended with error: {task.exception()}")
        except Exception as e:
            logger.warning(f"[Unified] handle_unified_websocket exception: {e}")
        finally:
            for task in (video_task, control_task):
                if not task.done():
                    task.cancel()
            logger.info(f"[Unified] WebSocket closed for serial={serial}")

    async def _stream_video_to_websocket(self, conn: socket.socket, ws: WebSocket):
        # Set socket to non-blocking mode
        conn.setblocking(False)
        loop = asyncio.get_event_loop()

        try:
            while True:
                # check if ws closed
                if ws.client_state.name != "CONNECTED":
                    logger.info('WebSocket no longer connected. Exiting video stream.')
                    break
                try:
                    data = await loop.sock_recv(conn, 1024 * 1024)
                except (OSError, ConnectionError) as e:
                    logger.info(f'Video socket closed: {e}')
                    break
                if not data:
                    logger.warning('No data received, connection may be closed.')
                    break
                try:
                    await ws.send_bytes(data)
                except (WebSocketDisconnect, RuntimeError, OSError):
                    logger.info('WebSocket disconnected during video send.')
                    break
        except asyncio.CancelledError:
            pass

    async def _handle_control_websocket(self, ws: WebSocket):
        try:
            while True:
                try:
                    message = await ws.receive_text()
                except (WebSocketDisconnect, RuntimeError, OSError):
                    logger.info('Control WebSocket disconnected.')
                    break

                try:
                    logger.debug(f"[Unified] Received message: {message}")
                    message = json.loads(message)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON message: {e}")
                    continue

                try:
                    width, height = self.resolution_width, self.resolution_height
                    message_type = message.get('type')
                    if message_type == 'touchMove':
                        xP = message['xP']
                        yP = message['yP']
                        self.controller.move(int(xP * width), int(yP * height), width, height)
                    elif message_type == 'touchDown':
                        xP = message['xP']
                        yP = message['yP']
                        self.controller.down(int(xP * width), int(yP * height), width, height)
                    elif message_type == 'touchUp':
                        xP = message['xP']
                        yP = message['yP']
                        self.controller.up(int(xP * width), int(yP * height), width, height)
                    elif message_type == 'keyEvent':
                        event_number = message['data']['eventNumber']
                        # 系统导航键（返回/主页/最近任务等）通过 adb 命令发送
                        # 部分模拟器（如雷电）对 scrcpy INJECT_KEYCODE 支持不完善
                        _ADB_FALLBACK_KEYS = {3, 4, 82, 187, 224, 223}  # HOME, BACK, MENU, APP_SWITCH, WAKEUP, SLEEP
                        if event_number in _ADB_FALLBACK_KEYS:
                            self.device.shell(f'input keyevent {event_number}')
                        else:
                            self.controller.key(KeyeventAction.DOWN, event_number, 0, MetaState.NONE)
                            self.controller.key(KeyeventAction.UP, event_number, 0, MetaState.NONE)
                    elif message_type == 'text':
                        text = message['detail']
                        self.device.shell(f'am broadcast -a SONIC_KEYBOARD --es msg \'{text}\'')
                    elif message_type == 'ping':
                        await ws.send_text(json.dumps({"type": "pong"}))
                except (OSError, BrokenPipeError) as e:
                    logger.warning(f"Control socket error: {e}")
                    break
                except Exception as e:
                    logger.error(f"Unexpected error handling control message: {e}")
                    continue
        except asyncio.CancelledError:
            pass
