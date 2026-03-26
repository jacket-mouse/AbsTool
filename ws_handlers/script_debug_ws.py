# websockets/script_debug_ws.py
from engine.python_script_generator import PythonScriptGenerator
from schemas.script_editor import ScriptConfig, ScriptNode, Connection

import os
import json
import subprocess
import tempfile
import asyncio
import threading
from fastapi import WebSocket, WebSocketDisconnect

import sys
PYTHON_BIN = sys.executable
python_gen = PythonScriptGenerator()


async def script_debug_ws_handler(websocket: WebSocket):
    await websocket.accept()
    print(f"[ScriptDebug] WebSocket connected")

    process: subprocess.Popen | None = None
    tmp_path: str | None = None
    loop = asyncio.get_event_loop()

    # 1. 安全终止与清理机制
    async def terminate():
        nonlocal process, tmp_path
        if process and process.poll() is None:
            try:
                process.kill()
                await asyncio.to_thread(process.wait, timeout=1.0)
            except Exception:
                pass
        process = None

        # 清理临时文件，保护硬盘
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
        tmp_path = None

    # 2. 流读取器：在线程中同步读取 pipe，通过 event loop 回调发送 WebSocket 消息
    def _read_stream_sync(stream, is_stderr, ws_send_coro_factory):
        """在后台线程中同步逐行读取子进程的 stdout/stderr"""
        try:
            for line in stream:
                text = line.decode("utf-8", errors="replace").strip()
                if not text:
                    continue
                try:
                    if is_stderr:
                        data = json.dumps({
                            "type": "log",
                            "status": "error",
                            "message": f"[系统报错] {text}"
                        }, ensure_ascii=False)
                    else:
                        data = text
                    # 从后台线程安全地调度到 event loop
                    future = asyncio.run_coroutine_threadsafe(
                        websocket.send_text(data), loop
                    )
                    future.result(timeout=5)  # 等待发送完成
                except Exception:
                    break
        except Exception:
            pass

    # 3. 进程守望者：在线程中等待进程结束
    def _wait_process_sync(p):
        p.wait()
        try:
            future = asyncio.run_coroutine_threadsafe(
                websocket.send_text(json.dumps({"type": "finished"})), loop
            )
            future.result(timeout=5)
        except Exception:
            pass
        # 触发清理
        asyncio.run_coroutine_threadsafe(terminate(), loop)

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            action = msg.get("action", "")

            if action == "start":
                await terminate()  # 杀掉可能还在运行的老进程

                # --- 组装配置 ---
                config_data = msg.get("config", {})
                nodes = [ScriptNode(**n) if isinstance(n, dict) else n for n in config_data.get("nodes", [])]

                # 精准映射前端的连线字段到后端的 Pydantic 模型
                conns = []
                for c in config_data.get("connections", []):
                    if isinstance(c, dict):
                        conns.append(Connection(
                            from_node=c.get("from", c.get("from_node", "")),
                            to_node=c.get("to", c.get("to_node", "")),
                            from_port=c.get("fromPort", c.get("from_port", "default")),
                            to_port=c.get("toPort", c.get("to_port", "default"))
                        ))
                    else:
                        conns.append(c)

                config = ScriptConfig(nodes=nodes, connections=conns)

                # --- 提取设备序列号 ---
                serial = msg.get("serial", "") or ""

                # --- 生成脚本并写入临时文件 ---
                python_code = python_gen.generate_debug(config, serial=serial)

                with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8") as f:
                    f.write(python_code)
                    tmp_path = f.name

                # --- 用 subprocess.Popen 启动进程（兼容 Windows 所有事件循环） ---
                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"
                process = subprocess.Popen(
                    [PYTHON_BIN, "-u", tmp_path],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                )

                # 用后台线程并发读取 stdout/stderr，避免死锁
                threading.Thread(
                    target=_read_stream_sync,
                    args=(process.stdout, False, None),
                    daemon=True
                ).start()
                threading.Thread(
                    target=_read_stream_sync,
                    args=(process.stderr, True, None),
                    daemon=True
                ).start()
                # 守望者线程等待进程结束
                threading.Thread(
                    target=_wait_process_sync,
                    args=(process,),
                    daemon=True
                ).start()

            elif action == "stop":
                await terminate()
                try:
                    await websocket.send_text(json.dumps({"type": "finished"}))
                except Exception:
                    pass

            # 包括 step, run, pause, 还有前面加的 overrideCode 都在这里统一透传
            elif action in ("step", "run", "pause", "keyevent"):
                if process and process.stdin and process.poll() is None:
                    try:
                        process.stdin.write((raw + "\n").encode("utf-8"))
                        process.stdin.flush()
                    except Exception as e:
                        print(f"写入子进程 stdin 失败: {e}")

    except WebSocketDisconnect:
        pass
    except ValueError as ve:
        error_msg = str(ve)
        print(f"⚠️ 脚本逻辑校验未通过，拒绝调试: {error_msg}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": error_msg
            }, ensure_ascii=False))
            await websocket.close(code=1008, reason=error_msg[:123])
        except Exception:
            pass
    except Exception as e:
        import traceback
        print(f"[ScriptDebug] 发生致命错误: {type(e).__name__}: {e}")
        traceback.print_exc()
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"服务器内部错误: {str(e)}"
            }, ensure_ascii=False))
            await websocket.close(code=1011, reason="Internal Error")
        except Exception:
            pass
    finally:
        await terminate()
        print(f"[ScriptDebug] WebSocket disconnected")
