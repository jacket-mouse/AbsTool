# websockets/script_debug_ws.py
from engine.python_script_generator import PythonScriptGenerator
from schemas.script_editor import ScriptConfig, ScriptNode, Connection

import os
import json
import tempfile
import asyncio
from fastapi import WebSocket, WebSocketDisconnect

PYTHON_BIN = "/Users/leeson/Documents/毕业设计/AbsTool/.venv/bin/python3"
python_gen = PythonScriptGenerator()


async def script_debug_ws_handler(websocket: WebSocket):
    await websocket.accept()
    print(f"[ScriptDebug] WebSocket connected")

    process: asyncio.subprocess.Process | None = None
    tmp_path: str | None = None

    # 1. 安全终止与清理机制
    async def terminate():
        nonlocal process, tmp_path
        if process and process.returncode is None:
            try:
                process.kill()
                # 给它 1 秒钟优雅死掉，否则强制回收
                await asyncio.wait_for(process.wait(), timeout=1.0)
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

    # 2. 流读取器（支持并发读取 stdout 和 stderr）
    async def read_stream(stream: asyncio.StreamReader, is_stderr=False):
        if not stream:
            return
        try:
            async for line in stream:
                text = line.decode("utf-8", errors="replace").strip()
                if not text:
                    continue
                try:
                    if is_stderr:
                        # Stderr 统一包装成红色的报错日志发送给前端
                        await websocket.send_text(json.dumps({
                            "type": "log",
                            "status": "error",
                            "message": f"[系统报错] {text}"
                        }, ensure_ascii=False))
                    else:
                        # Stdout 直接透传（因为底层脚本已经把它 print 成了标准 JSON 格式）
                        await websocket.send_text(text)
                except Exception:
                    break  # WebSocket 断开时停止推送
        except Exception:
            pass

    # 3. 进程守望者（等待结束并发送 finished 帧）
    async def wait_and_finish(p: asyncio.subprocess.Process):
        await p.wait()
        try:
            await websocket.send_text(json.dumps({"type": "finished"}))
        except Exception:
            pass
        await terminate()  # 执行完毕后自动擦屁股（删临时文件）

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
                            from_port=c.get("fromPort", c.get("from_port", "default")),  # 默认端口给 default
                            to_port=c.get("toPort", c.get("to_port", "default"))
                        ))
                    else:
                        conns.append(c)

                config = ScriptConfig(nodes=nodes, connections=conns)

                # --- 生成脚本并写入临时文件 ---
                python_code = python_gen.generate_debug(config)

                with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8") as f:
                    f.write(python_code)
                    tmp_path = f.name

                # --- 启动进程 (-u 参数极其关键，禁用 Python 输出缓冲，保证日志实时到达) ---
                process = await asyncio.create_subprocess_exec(
                    PYTHON_BIN, "-u", tmp_path,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                # 用 asyncio.create_task 并发读取！彻底解决死锁！
                asyncio.create_task(read_stream(process.stdout, is_stderr=False))
                asyncio.create_task(read_stream(process.stderr, is_stderr=True))
                # 派一个守望者去等它结束
                asyncio.create_task(wait_and_finish(process))

            elif action == "stop":
                await terminate()
                try:
                    await websocket.send_text(json.dumps({"type": "finished"}))
                except Exception:
                    pass

            # 包括 step, run, pause, 还有前面加的 overrideCode 都在这里统一透传
            elif action in ("step", "run", "pause", "keyevent"):
                if process and process.stdin and process.returncode is None:
                    try:
                        # 将前端的 JSON 指令原封不动地砸进 Python 子脚本的黑洞 (stdin)
                        process.stdin.write((raw + "\n").encode("utf-8"))
                        await process.stdin.drain()
                    except Exception as e:
                        print(f"写入子进程 stdin 失败: {e}")

    except WebSocketDisconnect:
        pass
    except ValueError as ve:
        error_msg = str(ve)
        print(f"⚠️ 脚本逻辑校验未通过，拒绝调试: {error_msg}")
        # 通过 WebSocket 发送错误消息，再优雅关闭连接
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": error_msg
            }, ensure_ascii=False))
            await websocket.close(code=1008, reason=error_msg[:123])
        except Exception:
            pass
    except Exception as e:
        print(f"[ScriptDebug] 发生致命错误: {e}")
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
