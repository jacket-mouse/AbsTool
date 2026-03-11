# scheduler/task_scheduler.py
import json
import os
import tempfile
import uuid
from datetime import datetime
from typing import Dict

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

PYTHON_BIN = "/Users/leeson/Documents/毕业设计/AbsTool/venv/bin/python3"


class TaskSchedulerManager:

    def __init__(self):
        self._scheduler = BackgroundScheduler()
        self._scheduler.start()

    def init_from_db(self):
        """启动时从数据库加载所有 SCHEDULED 类型的任务并注册。"""
        from core.database import SessionLocal
        from models.task_info import TaskInfo
        db = SessionLocal()
        try:
            tasks = db.query(TaskInfo).filter(
                TaskInfo.trigger_type == "SCHEDULED",
                TaskInfo.cron_expression.isnot(None),
            ).all()
            for task in tasks:
                self.schedule_task(task.task_id, task.cron_expression)
        finally:
            db.close()

    def schedule_task(self, task_id: str, cron: str) -> None:
        """注册或更新一个定时任务。"""
        self.cancel_task(task_id)
        if not cron or not cron.strip():
            return
        try:
            self._scheduler.add_job(
                self._execute_background,
                trigger=CronTrigger.from_crontab(cron),
                id=task_id,
                args=[task_id],
                replace_existing=True,
            )
            print(f"[Scheduler] Scheduled task {task_id} with cron: {cron}")
        except Exception as e:
            print(f"[Scheduler] Failed to schedule task {task_id}: {e}")

    def cancel_task(self, task_id: str) -> None:
        """取消一个定时任务。"""
        try:
            self._scheduler.remove_job(task_id)
            print(f"[Scheduler] Canceled task {task_id}")
        except Exception:
            pass

    def shutdown(self) -> None:
        self._scheduler.shutdown(wait=False)

    def _execute_background(self, task_id: str) -> None:
        """后台执行任务：生成 Python 脚本 → 运行子进程 → 写执行日志。"""
        import subprocess
        print(f"[Scheduler] Executing task {task_id}")

        from core.database import SessionLocal
        from models.task_info import TaskInfo
        from models.script_execlog import ScriptExecLog
        from services.script_service import ScriptService
        from services.template_service import TemplateService
        from engine.python_script_generator import PythonScriptGenerator
        from schemas.script_editor import ScriptConfig

        db = SessionLocal()
        try:
            task = db.query(TaskInfo).filter(TaskInfo.task_id == task_id).first()
            if not task:
                return

            # 更新状态为 RUNNING
            task.status = "RUNNING"
            task.start_time = datetime.now()
            db.commit()

            # 生成 Python 代码
            python_code = ""
            try:
                if task.template_id:
                    template_svc = TemplateService(db)
                    python_code = template_svc.generate_python_for_template(task.template_id)
                elif task.script_id:
                    script_svc = ScriptService(db)
                    load_res = script_svc.load_script(task.script_id)
                    gen = PythonScriptGenerator()
                    content = load_res.content
                    if isinstance(content, dict):
                        from schemas.script_editor import ScriptNode, Connection
                        sc = ScriptConfig(
                            nodes=[ScriptNode(**n) if isinstance(n, dict) else n for n in content.get("nodes", [])],
                            connections=[Connection(**c) if isinstance(c, dict) else c for c in content.get("connections", [])],
                        )
                    else:
                        sc = content
                    python_code = gen.generate(sc)
                else:
                    raise RuntimeError("No script or template configured.")
            except Exception as e:
                task.status = "FAILED"
                task.end_time = datetime.now()
                db.commit()
                log = ScriptExecLog()
                log.log_id = uuid.uuid4().hex
                log.task_id = task_id
                log.step_name = "Script Compilation"
                log.status = "FAIL"
                log.error_msg = str(e)
                log.exec_time = datetime.now()
                db.add(log)
                db.commit()
                return

            # 写临时文件并运行
            with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8") as f:
                f.write(python_code)
                tmp_path = f.name

            has_error = False
            try:
                proc = subprocess.Popen(
                    [PYTHON_BIN, "-u", tmp_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                for line in proc.stdout:
                    line = line.strip()
                    try:
                        node = json.loads(line)
                        if node.get("type") == "log":
                            status = node.get("status", "success")
                            msg = node.get("message", "")
                            step_name = node.get("action", "Execution Step")
                            log = ScriptExecLog()
                            log.log_id = uuid.uuid4().hex
                            log.task_id = task_id
                            log.script_id = task.script_id
                            log.step_name = step_name
                            log.status = "FAIL" if status == "error" else "SUCCESS"
                            log.error_msg = msg if status == "error" else None
                            log.exec_time = datetime.now()
                            log.duration = 100
                            db.add(log)
                            db.commit()
                    except Exception:
                        pass

                for line in proc.stderr:
                    has_error = True
                    log = ScriptExecLog()
                    log.log_id = uuid.uuid4().hex
                    log.task_id = task_id
                    log.step_name = "System Error"
                    log.status = "FAIL"
                    log.error_msg = line.strip()
                    log.exec_time = datetime.now()
                    db.add(log)
                    db.commit()

                exit_code = proc.wait()
                final_status = "FAILED" if (has_error or exit_code != 0) else "COMPLETED"
            finally:
                os.unlink(tmp_path)

            task.status = final_status
            task.end_time = datetime.now()
            db.commit()

        except Exception as e:
            print(f"[Scheduler] Task {task_id} exception: {e}")
            try:
                task = db.query(TaskInfo).filter(TaskInfo.task_id == task_id).first()
                if task:
                    task.status = "FAILED"
                    task.end_time = datetime.now()
                    db.commit()
            except Exception:
                pass
        finally:
            db.close()


# 全局单例
task_scheduler_manager = TaskSchedulerManager()
