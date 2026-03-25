# services/emulator_service.py
import re
import subprocess
import threading
import time
from typing import List, Dict

import docker
from docker.errors import NotFound
from loguru import logger

from schemas.emulator import EmulatorInfo

# Docker 镜像：budtmo/docker-android 提供开箱即用的 Android 模拟器
ANDROID_IMAGE_MAP = {
    "9.0":  "budtmo/docker-android:emulator_9.0",
    "10.0": "budtmo/docker-android:emulator_10.0",
    "11.0": "budtmo/docker-android:emulator_11.0",
    "12.0": "budtmo/docker-android:emulator_12.0",
    "13.0": "budtmo/docker-android:emulator_13.0",
    "14.0": "budtmo/docker-android:emulator_14.0",
}

CONTAINER_PREFIX = "abstool-emu-"
ADB_PORT_START = 5556


class EmulatorService:
    """基于 Docker 容器的 Android 模拟器管理"""

    # 正在创建中的容器名称 → 进度信息
    _creating: Dict[str, dict] = {}

    def __init__(self):
        try:
            self.client = docker.from_env()
            self.client.ping()
        except Exception as e:
            logger.warning(f"Docker 连接失败: {e}")
            self.client = None

    def _ensure_docker(self):
        if not self.client:
            raise RuntimeError("无法连接 Docker，请确认 Docker Desktop 已启动")

    def _find_available_port(self) -> int:
        used_ports = set()
        containers = self.client.containers.list(all=True, filters={"name": CONTAINER_PREFIX})
        for c in containers:
            ports = c.attrs.get("NetworkSettings", {}).get("Ports", {}) or {}
            mapping = ports.get("5555/tcp")
            if mapping:
                used_ports.add(int(mapping[0]["HostPort"]))
        port = ADB_PORT_START
        while port in used_ports:
            port += 1
        return port

    def _container_to_info(self, container) -> EmulatorInfo:
        labels = container.labels or {}
        android_version = labels.get("abstool.android_version", "unknown")

        adb_port = None
        adb_serial = None
        ports = container.attrs.get("NetworkSettings", {}).get("Ports", {}) or {}
        mapping = ports.get("5555/tcp")
        if mapping:
            adb_port = int(mapping[0]["HostPort"])
            adb_serial = f"127.0.0.1:{adb_port}"

        docker_status = container.status
        if docker_status == "running":
            # 检查 ADB 是否已经就绪
            if adb_port and not self._is_adb_ready(adb_serial):
                status = "booting"
            else:
                status = "running"
        elif docker_status in ("exited", "dead"):
            status = "stopped"
        else:
            status = "creating"

        return EmulatorInfo(
            containerId=container.short_id,
            name=container.name.removeprefix(CONTAINER_PREFIX),
            androidVersion=android_version,
            status=status,
            adbSerial=adb_serial,
            adbPort=adb_port,
        )

    @staticmethod
    def _is_adb_ready(serial: str) -> bool:
        """检查 ADB 设备是否已完成开机"""
        try:
            result = subprocess.run(
                ["adb", "-s", serial, "shell", "getprop", "sys.boot_completed"],
                capture_output=True, text=True, timeout=3
            )
            return result.stdout.strip() == "1"
        except Exception:
            return False

    def list_emulators(self) -> List[dict]:
        """列出所有模拟器容器 + 正在创建中的占位项"""
        self._ensure_docker()

        result = []

        # 已创建的容器
        containers = self.client.containers.list(all=True, filters={"name": CONTAINER_PREFIX})
        existing_names = set()
        for c in containers:
            info = self._container_to_info(c)
            item = info.model_dump(by_alias=True)
            # 如果该容器仍在 _creating 中，附加后台线程的进度信息
            creating_info = self._creating.get(c.name)
            if creating_info:
                item["pullProgress"] = creating_info.get("progress", "")
            elif item.get("status") == "booting":
                # _creating 已清除但 ADB 仍未就绪，给一个默认提示
                item["pullProgress"] = "系统启动中，等待 ADB 就绪..."
            result.append(item)
            existing_names.add(c.name)

        # 正在拉取镜像、尚未创建出容器的任务
        for container_name, info in self._creating.items():
            if container_name not in existing_names:
                result.append({
                    "containerId": "",
                    "name": info.get("display_name", container_name.removeprefix(CONTAINER_PREFIX)),
                    "androidVersion": info.get("android_version", ""),
                    "status": info.get("stage", "pulling"),
                    "adbSerial": None,
                    "adbPort": None,
                    "pullProgress": info.get("progress", ""),
                })

        return result

    def get_available_versions(self) -> List[str]:
        return list(ANDROID_IMAGE_MAP.keys())

    def create_emulator(self, name: str, android_version: str = "12.0") -> dict:
        """
        立即返回，后台线程执行：拉取镜像 → 创建容器 → 启动 → 等待 ADB。
        前端通过轮询 /list 查看进度。
        """
        self._ensure_docker()

        image = ANDROID_IMAGE_MAP.get(android_version)
        if not image:
            raise RuntimeError(f"不支持的 Android 版本: {android_version}，可选: {list(ANDROID_IMAGE_MAP.keys())}")

        # Docker 容器名只允许 [a-zA-Z0-9_.-]，将不合法字符替换为 '-'
        safe_name = re.sub(r'[^a-zA-Z0-9_.-]', '-', name).strip('-')
        if not safe_name:
            raise RuntimeError("模拟器名称不合法，请使用英文、数字、下划线或短横线")
        container_name = f"{CONTAINER_PREFIX}{safe_name}"

        # 检查是否已存在
        try:
            existing = self.client.containers.get(container_name)
            if existing.status == "running":
                return {"status": "already_running"}
            existing.start()
            existing.reload()
            self._adb_connect(existing)
            return {"status": "started"}
        except NotFound:
            pass

        # 检查是否正在创建中
        if container_name in self._creating:
            return {"status": "creating"}

        # 标记为创建中，启动后台线程
        self._creating[container_name] = {
            "android_version": android_version,
            "display_name": name,
            "stage": "pulling",
            "progress": "准备拉取镜像...",
        }

        thread = threading.Thread(
            target=self._bg_create,
            args=(container_name, image, android_version),
            daemon=True,
        )
        thread.start()

        return {"status": "creating"}

    def _update_progress(self, container_name: str, stage: str, progress: str):
        """更新创建进度（线程安全：单写多读，GIL 保护）"""
        if container_name in self._creating:
            self._creating[container_name]["stage"] = stage
            self._creating[container_name]["progress"] = progress

    def _bg_create(self, container_name: str, image: str, android_version: str):
        """后台线程：拉取镜像 + 创建容器 + 等待 ADB"""
        try:
            # 1. 拉取镜像（带进度追踪）
            try:
                self.client.images.get(image)
                logger.info(f"镜像 {image} 已存在，跳过拉取")
                self._update_progress(container_name, "pulling", "镜像已存在，跳过拉取")
            except Exception:
                logger.info(f"开始拉取镜像: {image}")
                self._update_progress(container_name, "pulling", "开始拉取镜像...")
                self._pull_image_with_progress(container_name, image)
                logger.info(f"镜像 {image} 拉取完成")

            # 2. 分配端口 & 创建容器
            self._update_progress(container_name, "creating", "正在创建容器...")
            adb_port = self._find_available_port()
            logger.info(f"创建容器: {container_name}, ADB port {adb_port}")

            container = self.client.containers.run(
                image=image,
                name=container_name,
                detach=True,
                privileged=True,
                ports={"5555/tcp": adb_port},
                environment={
                    "EMULATOR_DEVICE": "Samsung Galaxy S10",
                    "WEB_VNC": "false",
                },
                labels={
                    "abstool.managed": "true",
                    "abstool.android_version": android_version,
                },
            )

            # 3. 等待 ADB 可连接
            self._update_progress(container_name, "booting", "容器已启动，等待模拟器开机...")
            self._wait_for_adb_with_progress(container_name, adb_port, timeout=180)
            self._adb_connect_port(adb_port)

            logger.info(f"模拟器 {container_name} 创建完成")
        except Exception as e:
            logger.error(f"后台创建模拟器 {container_name} 失败: {e}")
            self._update_progress(container_name, "pulling", f"创建失败: {e}")
            time.sleep(5)  # 让前端有时间看到错误信息
        finally:
            # 无论成功失败，移除创建中标记
            self._creating.pop(container_name, None)

    def _pull_image_with_progress(self, container_name: str, image: str):
        """流式拉取 Docker 镜像，实时更新进度"""
        repo, tag = image.rsplit(":", 1) if ":" in image else (image, "latest")

        # 下载阶段追踪
        dl_layer_totals = {}     # layer_id → total bytes (下载)
        dl_layer_currents = {}   # layer_id → current bytes (下载)
        downloaded_layers = set()  # 下载完成的层
        # 解压阶段追踪
        ext_layer_totals = {}    # layer_id → total bytes (解压)
        ext_layer_currents = {}  # layer_id → current bytes (解压)
        extracted_layers = set()   # 解压完成的层 (Pull complete)
        # 所有层
        all_layers = set()
        already_exists = set()     # 本地已存在的层

        for event in self.client.api.pull(repo, tag=tag, stream=True, decode=True):
            status = event.get("status", "")
            layer_id = event.get("id", "")

            if not layer_id:
                continue

            if status in ("Pulling fs layer", "Downloading", "Extracting", "Pull complete",
                          "Verifying Checksum", "Download complete", "Already exists"):
                all_layers.add(layer_id)

            detail = event.get("progressDetail", {})

            if status == "Already exists":
                already_exists.add(layer_id)
                downloaded_layers.add(layer_id)
                extracted_layers.add(layer_id)

            elif status == "Downloading":
                current = detail.get("current", 0)
                total = detail.get("total", 0)
                if total > 0:
                    dl_layer_totals[layer_id] = total
                    dl_layer_currents[layer_id] = current

            elif status == "Download complete":
                downloaded_layers.add(layer_id)
                dl_layer_currents.pop(layer_id, None)
                dl_layer_totals.pop(layer_id, None)

            elif status == "Extracting":
                current = detail.get("current", 0)
                total = detail.get("total", 0)
                if total > 0:
                    ext_layer_totals[layer_id] = total
                    ext_layer_currents[layer_id] = current

            elif status == "Pull complete":
                extracted_layers.add(layer_id)
                ext_layer_currents.pop(layer_id, None)
                ext_layer_totals.pop(layer_id, None)

            # ── 构建进度文本 ──
            total_count = len(all_layers) if all_layers else 1
            dl_done = len(downloaded_layers)
            ext_done = len(extracted_layers)
            all_downloaded = (dl_done >= total_count)

            if not all_downloaded:
                # 阶段 1：下载中
                dl_current_bytes = sum(dl_layer_currents.values())
                dl_total_bytes = sum(dl_layer_totals.values())
                if dl_total_bytes > 0:
                    pct = dl_current_bytes / dl_total_bytes * 100
                    cur_mb = dl_current_bytes / (1024 * 1024)
                    tot_mb = dl_total_bytes / (1024 * 1024)
                    progress_text = (
                        f"下载中 {dl_done}/{total_count} 层 | "
                        f"{cur_mb:.0f}/{tot_mb:.0f} MB ({pct:.0f}%)"
                    )
                elif dl_done > 0:
                    progress_text = f"下载中 {dl_done}/{total_count} 层"
                else:
                    progress_text = f"正在准备下载 ({total_count} 层)..."
            else:
                # 阶段 2：解压中
                ext_current_bytes = sum(ext_layer_currents.values())
                ext_total_bytes = sum(ext_layer_totals.values())
                need_extract = total_count - len(already_exists)
                ext_real_done = ext_done - len(already_exists)
                if ext_total_bytes > 0:
                    pct = ext_current_bytes / ext_total_bytes * 100
                    progress_text = (
                        f"下载完成 | 解压中 {ext_real_done}/{need_extract} 层 ({pct:.0f}%)"
                    )
                elif need_extract > 0:
                    progress_text = f"下载完成 | 解压中 {ext_real_done}/{need_extract} 层"
                else:
                    progress_text = "即将完成..."

            self._update_progress(container_name, "pulling", progress_text)

        self._update_progress(container_name, "pulling", "镜像拉取完成")

    def start_emulator(self, container_id: str) -> EmulatorInfo:
        self._ensure_docker()
        try:
            container = self.client.containers.get(container_id)
        except NotFound:
            raise RuntimeError(f"容器 {container_id} 不存在")

        if container.status != "running":
            container.start()
            container.reload()
            # 后台等待 ADB，不阻塞接口
            threading.Thread(
                target=self._bg_wait_and_connect,
                args=(container,),
                daemon=True,
            ).start()

        return self._container_to_info(container)

    def _bg_wait_and_connect(self, container):
        """后台等待容器内 ADB 就绪并连接"""
        try:
            container.reload()
            ports = container.attrs.get("NetworkSettings", {}).get("Ports", {}) or {}
            mapping = ports.get("5555/tcp")
            if mapping:
                port = int(mapping[0]["HostPort"])
                self._wait_for_adb(port, timeout=180)
                self._adb_connect_port(port)
        except Exception as e:
            logger.error(f"后台连接 ADB 失败: {e}")

    def stop_emulator(self, container_id: str) -> bool:
        self._ensure_docker()
        try:
            container = self.client.containers.get(container_id)
            info = self._container_to_info(container)
            if info.adb_serial:
                self._adb_disconnect(info.adb_serial)
            container.stop(timeout=10)
            logger.info(f"模拟器容器 {container_id} 已停止")
            return True
        except NotFound:
            raise RuntimeError(f"容器 {container_id} 不存在")
        except Exception as e:
            logger.error(f"停止容器 {container_id} 失败: {e}")
            return False

    def delete_emulator(self, container_id: str) -> bool:
        self._ensure_docker()
        try:
            container = self.client.containers.get(container_id)
            info = self._container_to_info(container)
            if info.adb_serial:
                self._adb_disconnect(info.adb_serial)
            container.remove(force=True)
            logger.info(f"模拟器容器 {container_id} 已删除")
            return True
        except NotFound:
            raise RuntimeError(f"容器 {container_id} 不存在")
        except Exception as e:
            logger.error(f"删除容器 {container_id} 失败: {e}")
            return False

    # ─── ADB 工具方法 ──────────────────────────────────────────────────────────

    def _adb_connect(self, container):
        ports = container.attrs.get("NetworkSettings", {}).get("Ports", {}) or {}
        mapping = ports.get("5555/tcp")
        if mapping:
            port = int(mapping[0]["HostPort"])
            self._adb_connect_port(port)

    @staticmethod
    def _adb_connect_port(port: int):
        serial = f"127.0.0.1:{port}"
        try:
            subprocess.run(["adb", "connect", serial], capture_output=True, text=True, timeout=10)
            logger.info(f"ADB 已连接: {serial}")
        except Exception as e:
            logger.warning(f"ADB connect {serial} 失败: {e}")

    @staticmethod
    def _adb_disconnect(serial: str):
        try:
            subprocess.run(["adb", "disconnect", serial], capture_output=True, text=True, timeout=5)
        except Exception:
            pass

    @staticmethod
    def _wait_for_adb(port: int, timeout: int = 180):
        serial = f"127.0.0.1:{port}"
        start = time.time()
        while time.time() - start < timeout:
            try:
                result = subprocess.run(
                    ["adb", "connect", serial], capture_output=True, text=True, timeout=5
                )
                output = result.stdout.strip()
                if "connected" in output and "unable" not in output.lower():
                    boot_result = subprocess.run(
                        ["adb", "-s", serial, "shell", "getprop", "sys.boot_completed"],
                        capture_output=True, text=True, timeout=5
                    )
                    if boot_result.stdout.strip() == "1":
                        logger.info(f"模拟器 {serial} 启动完成")
                        return
            except Exception:
                pass
            time.sleep(3)
        logger.warning(f"等待模拟器 {serial} 启动超时（{timeout}秒）")

    def _wait_for_adb_with_progress(self, container_name: str, port: int, timeout: int = 180):
        """等待 ADB 就绪，同时更新进度信息"""
        serial = f"127.0.0.1:{port}"
        start = time.time()
        adb_connected = False
        attempt = 0

        while time.time() - start < timeout:
            attempt += 1
            elapsed = int(time.time() - start)

            try:
                result = subprocess.run(
                    ["adb", "connect", serial], capture_output=True, text=True, timeout=5
                )
                output = result.stdout.strip()
                if "connected" in output and "unable" not in output.lower():
                    if not adb_connected:
                        adb_connected = True
                        self._update_progress(
                            container_name, "booting",
                            f"ADB 已连接，等待系统启动完成... ({elapsed}s)"
                        )

                    boot_result = subprocess.run(
                        ["adb", "-s", serial, "shell", "getprop", "sys.boot_completed"],
                        capture_output=True, text=True, timeout=5
                    )
                    if boot_result.stdout.strip() == "1":
                        self._update_progress(container_name, "booting", "模拟器启动完成")
                        logger.info(f"模拟器 {serial} 启动完成")
                        return
                    else:
                        self._update_progress(
                            container_name, "booting",
                            f"系统启动中，请耐心等待... ({elapsed}s)"
                        )
                else:
                    self._update_progress(
                        container_name, "booting",
                        f"等待 ADB 连接... ({elapsed}s)"
                    )
            except Exception:
                self._update_progress(
                    container_name, "booting",
                    f"等待模拟器响应... ({elapsed}s)"
                )

            time.sleep(3)

        self._update_progress(container_name, "booting", f"开机超时 ({timeout}s)")
        logger.warning(f"等待模拟器 {serial} 启动超时（{timeout}秒）")
