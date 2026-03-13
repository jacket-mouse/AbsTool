# websockets/script_debug_ws.py
import asyncio
import json
import tempfile
import os

from fastapi import WebSocket, WebSocketDisconnect

from engine.python_script_generator import PythonScriptGenerator
from schemas.script_editor import ScriptConfig, ScriptNode, Connection

PYTHON_BIN = "/Users/leeson/Documents/毕业设计/AbsTool/.venv/bin/python3"

python_gen = PythonScriptGenerator()


async def script_debug_ws_handler(websocket: WebSocket):
    await websocket.accept()
    print(f"[ScriptDebug] WebSocket connected")

    process: asyncio.subprocess.Process | None = None
    tmp_path: str | None = None

    async def terminate():
        nonlocal process, tmp_path
        if process and process.returncode is None:
            process.kill()
            try:
                await process.wait()
            except Exception:
                pass
        process = None
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
        tmp_path = None

    async def stream_output():
        """读取 stdout / stderr 并推送给前端，完成后发 finished 帧。"""
        try:
            async for line in process.stdout:
                text = line.decode("utf-8", errors="replace").rstrip()
                try:
                    await websocket.send_text(text)
                except Exception:
                    return
        except Exception:
            pass

        # 读取 stderr
        try:
            async for line in process.stderr:
                text = line.decode("utf-8", errors="replace").rstrip()
                try:
                    await websocket.send_text(
                        json.dumps({"type": "log", "status": "error", "message": f"Stderr: {text}"}, ensure_ascii=False)
                    )
                except Exception:
                    return
        except Exception:
            pass

        try:
            await websocket.send_text(json.dumps({"type": "finished"}))
        except Exception:
            pass

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            action = msg.get("action", "")

            if action == "start":
                await terminate()

                # 解析 config 并生成调试脚本
                config_data = msg.get("config", {})
                nodes = [ScriptNode(**n) if isinstance(n, dict) else n for n in config_data.get("nodes", [])]
                conns = []
                for c in config_data.get("connections", []):
                    if isinstance(c, dict):
                        conns.append(Connection(**{"from": c.get("from", c.get("from_node", "")), "to": c.get("to", c.get("to_node", "")), "fromPort": c.get("fromPort", c.get("from_port")), "toPort": c.get("toPort", c.get("to_port"))}))
                    else:
                        conns.append(c)
                config = ScriptConfig(nodes=nodes, connections=conns)
                python_code = python_gen.generate_debug(config)

                with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8") as f:
                    f.write(python_code)
                    tmp_path = f.name

                process = await asyncio.create_subprocess_exec(
                    PYTHON_BIN, "-u", tmp_path,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                # 启动后台 IO 推流任务
                asyncio.create_task(stream_output())

            elif action == "stop":
                await terminate()

            elif action in ("step", "run", "pause", "update_node"):
                if process and process.stdin and process.returncode is None:
                    try:
                        process.stdin.write((raw + "\n").encode("utf-8"))
                        await process.stdin.drain()
                    except Exception:
                        pass

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[ScriptDebug] Error: {e}")
    finally:
        await terminate()
        print(f"[ScriptDebug] WebSocket disconnected")
