# websockets/task_execute_ws.py
import asyncio
import json
import os
import tempfile
import time
import uuid
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect

from engine.python_script_generator import PythonScriptGenerator
from schemas.script_editor import ScriptConfig, ScriptNode, Connection

PYTHON_BIN = "/Users/leeson/Documents/毕业设计/AbsTool/.venv/bin/python3"

python_gen = PythonScriptGenerator()


async def task_execute_ws_handler(websocket: WebSocket):
    await websocket.accept()
    print(f"[TaskExecute] WebSocket connected")

    process: asyncio.subprocess.Process | None = None
    tmp_path: str | None = None
    current_task_id: str | None = None
    start_ts: float = 0.0

    async def terminate(mark_failed: bool = False):
        nonlocal process, tmp_path, current_task_id
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

        if mark_failed and current_task_id:
            try:
                from core.database import SessionLocal
                from services.task_service import TaskService
                db = SessionLocal()
                try:
                    svc = TaskService(db)
                    svc.update_task_status(current_task_id, "FAILED")
                finally:
                    db.close()
            except Exception:
                pass
        current_task_id = None

    async def stream_output(task_id: str, script_id: str | None):
        """读取 stdout/stderr，写执行日志，推流给前端，最后更新任务状态。"""
        from core.database import SessionLocal
        from models.script_execlog import ScriptExecLog
        from services.task_service import TaskService

        has_error = False

        try:
            async for line in process.stdout:
                text = line.decode("utf-8", errors="replace").rstrip()
                try:
                    await websocket.send_text(text)
                except Exception:
                    return

                # 写执行日志
                try:
                    node = json.loads(text)
                    if node.get("type") == "log":
                        status = node.get("status", "success")
                        msg = node.get("message", "")
                        step_name = node.get("action", "Execution Step")
                        db = SessionLocal()
                        try:
                            log = ScriptExecLog()
                            log.log_id = uuid.uuid4().hex
                            log.task_id = task_id
                            log.script_id = script_id
                            log.step_name = step_name
                            log.status = "FAIL" if status == "error" else "SUCCESS"
                            log.error_msg = msg if status == "error" else None
                            log.exec_time = datetime.now()
                            log.duration = 100
                            db.add(log)
                            db.commit()
                        finally:
                            db.close()
                except Exception:
                    pass
        except Exception:
            pass

        # stderr
        try:
            async for line in process.stderr:
                has_error = True
                text = line.decode("utf-8", errors="replace").rstrip()
                try:
                    await websocket.send_text(
                        json.dumps({"type": "log", "status": "error", "message": f"Stderr: {text}"}, ensure_ascii=False)
                    )
                except Exception:
                    return
                try:
                    db = SessionLocal()
                    try:
                        from models.script_execlog import ScriptExecLog
                        log = ScriptExecLog()
                        log.log_id = uuid.uuid4().hex
                        log.task_id = task_id
                        log.step_name = "System Error"
                        log.status = "FAIL"
                        log.error_msg = text
                        log.exec_time = datetime.now()
                        db.add(log)
                        db.commit()
                    finally:
                        db.close()
                except Exception:
                    pass
        except Exception:
            pass

        # 更新任务状态
        final_status = "FAILED" if has_error else "COMPLETED"
        try:
            db = SessionLocal()
            try:
                svc = TaskService(db)
                svc.update_task_status(task_id, final_status)
            finally:
                db.close()
        except Exception:
            pass

        # 发送 report + finished
        duration_ms = int((time.time() - start_ts) * 1000)
        try:
            await websocket.send_text(
                json.dumps({"type": "report", "duration": duration_ms, "success": not has_error})
            )
            await websocket.send_text(json.dumps({"type": "finished"}))
        except Exception:
            pass

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            action = msg.get("action", "")
            task_id = msg.get("taskId", "")

            if action == "start" and task_id:
                await terminate(mark_failed=False)
                current_task_id = task_id
                start_ts = time.time()

                from core.database import SessionLocal
                from services.task_service import TaskService
                from services.script_service import ScriptService
                from services.template_service import TemplateService

                db = SessionLocal()
                try:
                    task_svc = TaskService(db)
                    task_svc.update_task_status(task_id, "RUNNING")
                    task_dto = task_svc.get_task_detail(task_id)

                    python_code = ""
                    script_id = task_dto.script_id if task_dto else None
                    try:
                        if task_dto and task_dto.template_id:
                            tmpl_svc = TemplateService(db)
                            python_code = tmpl_svc.generate_python_for_template(task_dto.template_id)
                        elif task_dto and task_dto.script_id:
                            script_svc = ScriptService(db)
                            load_res = script_svc.load_script(task_dto.script_id)
                            content = load_res.content
                            if isinstance(content, dict):
                                sc = ScriptConfig(
                                    nodes=[ScriptNode(**n) if isinstance(n, dict) else n for n in content.get("nodes", [])],
                                    connections=[Connection(**{"from": c.get("from", ""), "to": c.get("to", "")}) if isinstance(c, dict) else c for c in content.get("connections", [])],
                                )
                            else:
                                sc = content
                            python_code = python_gen.generate(sc)
                        else:
                            raise RuntimeError("Task has no script or template configured.")
                    except Exception as e:
                        task_svc.update_task_status(task_id, "FAILED")
                        await websocket.send_text(
                            json.dumps({"type": "log", "status": "error", "message": f"Failed to compile script: {e}"}, ensure_ascii=False)
                        )
                        current_task_id = None
                        continue
                finally:
                    db.close()

                with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8") as f:
                    f.write(python_code)
                    tmp_path = f.name

                process = await asyncio.create_subprocess_exec(
                    PYTHON_BIN, "-u", tmp_path,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                asyncio.create_task(stream_output(task_id, script_id))

            elif action == "stop":
                tid = task_id or current_task_id
                await terminate(mark_failed=False)
                if tid:
                    from core.database import SessionLocal
                    from services.task_service import TaskService
                    db = SessionLocal()
                    try:
                        TaskService(db).update_task_status(tid, "FAILED")
                    finally:
                        db.close()

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[TaskExecute] Error: {e}")
    finally:
        await terminate(mark_failed=True)
        print(f"[TaskExecute] WebSocket disconnected")
