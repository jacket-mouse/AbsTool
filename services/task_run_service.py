# services/task_run_service.py
"""
任务运行服务 —— 根据任务关联的模板，按顺序执行其中的脚本，收集日志，上传到 MinIO，写入日志表
"""
import asyncio
import json
import os
import tempfile
import uuid
from datetime import datetime
from typing import Dict, Optional

from services.minio_service import MinioFileService

PYTHON_BIN = "/Users/leeson/Documents/毕业设计/AbsTool/.venv/bin/python3"

# ─── 全局运行实例注册表 ─────────────────────────────────────────────────────
_run_queues: Dict[str, asyncio.Queue] = {}        # run_id → SSE 日志队列
_run_processes: Dict[str, asyncio.subprocess.Process] = {}  # run_id → 当前子进程
_run_cancelled: Dict[str, bool] = {}              # run_id → 是否已被取消


def get_run_queue(run_id: str) -> asyncio.Queue | None:
    return _run_queues.get(run_id)


def stop_run(run_id: str) -> bool:
    """
    停止运行中的任务。返回 True 表示成功发起停止，False 表示实例不存在。
    """
    if run_id not in _run_queues:
        return False
    _run_cancelled[run_id] = True
    # 杀掉当前正在运行的子进程
    proc = _run_processes.get(run_id)
    if proc and proc.returncode is None:
        try:
            proc.kill()
        except Exception:
            pass
    return True


async def execute_task(
    run_id: str,
    task_id: str,
    device_id: str,
    script_py_paths: list[str],
):
    """
    后台协程：按顺序执行任务关联模板中的脚本，并将日志推送到 Queue。
    """
    queue = asyncio.Queue()
    _run_queues[run_id] = queue
    _run_cancelled[run_id] = False
    minio = MinioFileService()

    all_logs: list[str] = []
    has_error = False
    was_stopped = False
    start_time = datetime.now()

    async def push(log_type: str, message: str, **extra):
        """向队列推送一条 SSE 日志事件（type: info/success/warning/error）"""
        payload = {"type": log_type, "message": message, **extra}
        line = json.dumps(payload, ensure_ascii=False)
        all_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] [{log_type.upper()}] {message}")
        await queue.put(line)

    try:
        await push("info", f"▶ 开始运行任务 {task_id}，共 {len(script_py_paths)} 个脚本")

        for idx, py_path in enumerate(script_py_paths, start=1):
            # 检查是否已被取消
            if _run_cancelled.get(run_id):
                was_stopped = True
                await push("warning", "⏹ 任务已被用户手动停止")
                break

            await push("info", f"── 正在执行第 {idx}/{len(script_py_paths)} 个脚本: {py_path}")

            # 1. 从 MinIO 拉取 Python 脚本内容
            try:
                py_content = minio.get_file_content(py_path)
                if not py_content:
                    await push("error", f"脚本文件为空或不存在: {py_path}")
                    has_error = True
                    continue
            except Exception as e:
                await push("error", f"从 MinIO 获取脚本失败: {e}")
                has_error = True
                continue

            # 2. 写入临时文件
            tmp_file = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8") as f:
                    f.write(py_content)
                    tmp_file = f.name

                # 3. 启动子进程执行（-u 禁用缓冲，保证实时输出）
                process = await asyncio.create_subprocess_exec(
                    PYTHON_BIN, "-u", tmp_file,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                _run_processes[run_id] = process

                # 并发读取 stdout 和 stderr
                async def read_stdout():
                    async for line in process.stdout:
                        text = line.decode("utf-8", errors="replace").rstrip()
                        if text:
                            try:
                                node = json.loads(text)
                                if isinstance(node, dict) and node.get("type") == "log":
                                    status = node.get("status", "success")
                                    msg = node.get("message", text)
                                    await push(status, msg)
                                else:
                                    await push("info", text)
                            except json.JSONDecodeError:
                                await push("info", text)

                async def read_stderr():
                    nonlocal has_error
                    async for line in process.stderr:
                        text = line.decode("utf-8", errors="replace").rstrip()
                        if text:
                            has_error = True
                            await push("error", f"[stderr] {text}")

                await asyncio.gather(read_stdout(), read_stderr())
                await process.wait()

                # 进程结束后清除引用
                _run_processes.pop(run_id, None)

                # 检查是否是被 kill 掉的
                if _run_cancelled.get(run_id):
                    was_stopped = True
                    await push("warning", "⏹ 任务已被用户手动停止")
                    break

                exit_code = process.returncode
                if exit_code != 0:
                    has_error = True
                    await push("error", f"脚本退出码: {exit_code}")
                else:
                    await push("success", f"脚本 {idx} 执行完毕 ✓")

            finally:
                if tmp_file and os.path.exists(tmp_file):
                    os.unlink(tmp_file)

        # ─── 所有脚本执行完毕（或被取消） ──────────────────────────────────
        end_time = datetime.now()
        if was_stopped:
            exec_status = "STOPPED"
        elif has_error:
            exec_status = "FAILED"
        else:
            exec_status = "SUCCESS"

        await push("info", f"◼ 任务运行结束，状态: {exec_status}")

        # 4. 将完整日志上传到 MinIO
        log_text = "\n".join(all_logs)
        log_file_path = f"logs/tasks/{task_id}/{run_id}.log"
        try:
            minio.upload_file(log_file_path, log_text, "text/plain")
        except Exception as e:
            print(f"[TaskRun] 上传日志到 MinIO 失败: {e}")
            log_file_path = ""

        # 5. 写入 script_exec_log 日志表
        try:
            from core.database import SessionLocal
            from models.script_execlog import ScriptExecLog
            db = SessionLocal()
            try:
                log_record = ScriptExecLog()
                log_record.log_id = run_id
                log_record.task_id = task_id
                log_record.device_id = device_id
                log_record.exec_status = exec_status
                log_record.log_file_url = log_file_path
                log_record.start_time = start_time
                log_record.end_time = end_time
                db.add(log_record)
                db.commit()
            finally:
                db.close()
        except Exception as e:
            print(f"[TaskRun] 写入日志表失败: {e}")

    except Exception as e:
        await push("error", f"任务运行发生致命错误: {e}")
    finally:
        # 发送 finished 信号（前端收到后关闭 SSE 连接）
        finished_payload = json.dumps({"type": "finished", "message": "运行已结束"}, ensure_ascii=False)
        await queue.put(finished_payload)

        # 延迟清理（给 SSE 消费者时间消费 finished 事件）
        await asyncio.sleep(5)
        _run_queues.pop(run_id, None)
        _run_processes.pop(run_id, None)
        _run_cancelled.pop(run_id, None)
