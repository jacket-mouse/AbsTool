# services/scheduler_service.py
"""
定时任务调度服务 —— 基于 APScheduler，读取数据库中 type=CRON 且 status=ENABLE 的任务，
根据 cron_expression 自动调度执行。
"""
import asyncio
import uuid
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from sqlalchemy import asc
from sqlalchemy.orm import Session

from core.database import SessionLocal
from models.task_info import TaskInfo
from models.script_info import ScriptInfo
from models.script_template_rel import ScriptTemplateRel
from services.task_run_service import execute_task

# 全局调度器实例
scheduler: Optional[AsyncIOScheduler] = None


def _parse_cron_expression(expr: str) -> dict:
    """
    解析 cron 表达式为 APScheduler CronTrigger 参数。
    支持 5 段（分 时 日 月 周）和 6 段（秒 分 时 日 月 周）格式。
    """
    # 将 Quartz 格式的 "?" 转为 APScheduler 支持的 "*"
    expr = expr.replace("?", "*")
    parts = expr.strip().split()
    if len(parts) == 5:
        # 标准 5 段: 分 时 日 月 周
        return {
            "minute": parts[0],
            "hour": parts[1],
            "day": parts[2],
            "month": parts[3],
            "day_of_week": parts[4],
        }
    elif len(parts) == 6:
        # 6 段: 秒 分 时 日 月 周
        return {
            "second": parts[0],
            "minute": parts[1],
            "hour": parts[2],
            "day": parts[3],
            "month": parts[4],
            "day_of_week": parts[5],
        }
    elif len(parts) == 7:
        # 7 段 (Quartz 格式): 秒 分 时 日 月 周 年 → 忽略年
        return {
            "second": parts[0],
            "minute": parts[1],
            "hour": parts[2],
            "day": parts[3],
            "month": parts[4],
            "day_of_week": parts[5],
        }
    else:
        raise ValueError(f"无法解析 cron 表达式: {expr}")


def _build_script_paths(db: Session, task: TaskInfo) -> list[str]:
    """根据任务关联的模板，构建脚本文件路径列表"""
    if not task.template_id:
        return []

    rels = (
        db.query(ScriptTemplateRel)
        .filter(ScriptTemplateRel.template_id == task.template_id)
        .order_by(asc(ScriptTemplateRel.sort_order))
        .all()
    )

    paths = []
    for rel in rels:
        script_info = db.query(ScriptInfo).filter(ScriptInfo.script_id == rel.script_id).first()
        if script_info:
            paths.append(f"scripts/{script_info.script_id}/{script_info.latest_version}.py")
    return paths


async def _run_cron_task(task_id: str):
    """调度器回调：执行一个定时任务"""
    logger.info(f"[Scheduler] 定时触发任务: {task_id}")
    db = SessionLocal()
    try:
        task = db.query(TaskInfo).filter(TaskInfo.task_id == task_id).first()
        if not task:
            logger.warning(f"[Scheduler] 任务不存在: {task_id}")
            return
        if task.status != "ENABLE":
            logger.info(f"[Scheduler] 任务已禁用，跳过: {task_id}")
            return

        script_paths = _build_script_paths(db, task)
        if not script_paths:
            logger.warning(f"[Scheduler] 任务 {task_id} 没有关联脚本，跳过")
            return

        run_id = uuid.uuid4().hex[:8]
        logger.info(f"[Scheduler] 启动执行 task={task_id}, run={run_id}, scripts={len(script_paths)}")

        # 创建后台执行协程
        asyncio.create_task(
            execute_task(
                run_id=run_id,
                task_id=task_id,
                device_id=task.device_id or "local",
                script_py_paths=script_paths,
            )
        )
    except Exception as e:
        logger.error(f"[Scheduler] 执行任务 {task_id} 失败: {e}")
    finally:
        db.close()


def _add_task_job(task: TaskInfo):
    """为单个任务注册调度 job"""
    if not task.cron_expression:
        logger.warning(f"[Scheduler] 任务 {task.task_id} 没有 cron 表达式，跳过")
        return

    job_id = f"cron_task_{task.task_id}"
    try:
        cron_params = _parse_cron_expression(task.cron_expression)
        trigger = CronTrigger(**cron_params)
        scheduler.add_job(
            _run_cron_task,
            trigger=trigger,
            args=[task.task_id],
            id=job_id,
            replace_existing=True,
            name=f"定时任务: {task.name}",
        )
        logger.info(f"[Scheduler] 注册定时任务: {task.name} ({task.task_id}), cron={task.cron_expression}")
    except Exception as e:
        logger.error(f"[Scheduler] 注册任务 {task.task_id} 失败: {e}")


def init_scheduler():
    """应用启动时调用：初始化调度器，加载所有启用的 CRON 任务"""
    global scheduler
    scheduler = AsyncIOScheduler()

    db = SessionLocal()
    try:
        tasks = (
            db.query(TaskInfo)
            .filter(TaskInfo.type == "CRON", TaskInfo.status == "ENABLE")
            .all()
        )
        logger.info(f"[Scheduler] 发现 {len(tasks)} 个启用的定时任务")
        for task in tasks:
            _add_task_job(task)
    except Exception as e:
        logger.error(f"[Scheduler] 加载定时任务失败: {e}")
    finally:
        db.close()

    scheduler.start()
    logger.info("[Scheduler] 定时调度器已启动")


def shutdown_scheduler():
    """应用关闭时调用：停止调度器"""
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[Scheduler] 定时调度器已停止")


def add_or_update_job(task_id: str):
    """任务创建或更新后，刷新对应的调度 job"""
    if not scheduler:
        return

    job_id = f"cron_task_{task_id}"

    db = SessionLocal()
    try:
        task = db.query(TaskInfo).filter(TaskInfo.task_id == task_id).first()
        if not task:
            # 任务被删除，移除 job
            remove_job(task_id)
            return

        # 非 CRON 类型或已禁用 → 移除 job
        if task.type != "CRON" or task.status != "ENABLE":
            remove_job(task_id)
            return

        _add_task_job(task)
    except Exception as e:
        logger.error(f"[Scheduler] 更新任务 {task_id} 的调度失败: {e}")
    finally:
        db.close()


def remove_job(task_id: str):
    """移除某个任务的调度 job"""
    if not scheduler:
        return
    job_id = f"cron_task_{task_id}"
    try:
        scheduler.remove_job(job_id)
        logger.info(f"[Scheduler] 已移除定时任务: {task_id}")
    except Exception:
        pass  # job 不存在时忽略
