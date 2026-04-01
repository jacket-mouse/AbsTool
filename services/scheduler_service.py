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
        # 标准 Linux cron：分 时 日 月 周
        # 例如 "0 8 * * *" → 每天 8:00
        return {
            "minute": parts[0],
            "hour": parts[1],
            "day": parts[2],
            "month": parts[3],
            "day_of_week": parts[4],
        }
    elif len(parts) == 6:
        # 带秒的格式：秒 分 时 日 月 周
        # 例如 "30 0 8 * * *" → 每天 8:00:30
        return {
            "second": parts[0],
            "minute": parts[1],
            "hour": parts[2],
            "day": parts[3],
            "month": parts[4],
            "day_of_week": parts[5],
        }
    elif len(parts) == 7:
        # Quartz 7 段格式：秒 分 时 日 月 周 年
        # 例如 "0 0 8 * * ? 2026" → 忽略年份
        return {
            "second": parts[0],
            "minute": parts[1],
            "hour": parts[2],
            "day": parts[3],
            "month": parts[4],
            "day_of_week": parts[5],
            # parts[6] 是年份，APScheduler 不支持，直接忽略
        }
    else:
        raise ValueError(f"无法解析 cron 表达式: {expr}")


def _build_script_paths(db: Session, task: TaskInfo) -> list[str]:
    """根据任务关联的模板，构建脚本文件路径列表"""
    if not task.template_id:
        return []
    # 查询模板关联的所有脚本，按 sort_order 排序
    rels = (
        db.query(ScriptTemplateRel)
        .filter(ScriptTemplateRel.template_id == task.template_id)
        .order_by(asc(ScriptTemplateRel.sort_order))
        .all()
    )
    # 拼装每个脚本的 MinIO 存储路径
    paths = []
    for rel in rels:
        script_info = db.query(ScriptInfo).filter(ScriptInfo.script_id == rel.script_id).first()
        if script_info:
            paths.append(f"scripts/{script_info.script_id}/{script_info.latest_version}.py")
    return paths


async def _run_cron_task(task_id: str):
    """调度器回调：执行一个定时任务"""
    logger.info(f"[Scheduler] 定时触发任务: {task_id}")
    # 每次执行都新建 DB session（因为调度器回调不在 FastAPI 请求上下文中）
    db = SessionLocal()
    try:
        # 再次查库确认任务最新状态（防止注册后被禁用/删除）
        task = db.query(TaskInfo).filter(TaskInfo.task_id == task_id).first()
        if not task:
            logger.warning(f"[Scheduler] 任务不存在: {task_id}")
            return
        if task.status != "ENABLE":
            # 任务被禁用了，但 job 还没来得及移除（比如刚禁用还没调 remove_job）
            logger.info(f"[Scheduler] 任务已禁用，跳过: {task_id}")
            return
        # 构建脚本路径列表（和手动执行 task_router.py 里做的事一样）
        script_paths = _build_script_paths(db, task)
        if not script_paths:
            logger.warning(f"[Scheduler] 任务 {task_id} 没有关联脚本，跳过")
            return
        # 生成本次执行的唯一 ID
        run_id = uuid.uuid4().hex[:8]
        logger.info(f"[Scheduler] 启动执行 task={task_id}, run={run_id}, scripts={len(script_paths)}")

        # 创建后台执行协程
        # 启动后台协程执行（和手动点"运行"按钮走的是同一个函数）
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
        # APScheduler 的 CronTrigger 不直接接收 cron 字符串
        # 例如 "0 8 * * *" → {"minute": "0", "hour": "8", "day": "*", "month": "*", "day_of_week": "*"
        cron_params = _parse_cron_expression(task.cron_expression)
        # 用参数创建 CronTrigger（APScheduler 的触发器对象）
        trigger = CronTrigger(**cron_params)
        scheduler.add_job(
            _run_cron_task, # 到时间要调用的函数
            trigger=trigger, # 触发器（决定何时调用）
            args=[task.task_id], # 传给上述调用函数的参数
            id=job_id, # 唯一标识
            replace_existing=True, # 如果job_id已存在，覆盖旧的
            name=f"定时任务: {task.name}",
        )
        logger.info(f"[Scheduler] 注册定时任务: {task.name} ({task.task_id}), cron={task.cron_expression}")
    except Exception as e:
        logger.error(f"[Scheduler] 注册任务 {task.task_id} 失败: {e}")


def init_scheduler():
    """应用启动时调用：初始化调度器，加载所有启用的 CRON 任务"""
    global scheduler
    scheduler = AsyncIOScheduler()

    # 从数据库加载所有需要定时执行的任务
    db = SessionLocal()
    try:
        tasks = (
            db.query(TaskInfo)
            .filter(TaskInfo.type == "CRON", TaskInfo.status == "ENABLE") # 定时任务&已启用
            .all()
        )
        logger.info(f"[Scheduler] 发现 {len(tasks)} 个启用的定时任务")
        for task in tasks:
            _add_task_job(task)
    except Exception as e:
        logger.error(f"[Scheduler] 加载定时任务失败: {e}")
    finally:
        db.close()
    # 启动调度器
    scheduler.start()
    logger.info("[Scheduler] 定时调度器已启动")


def shutdown_scheduler():
    """应用关闭时调用：停止调度器"""
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False) # 不等待正在执行的任务完成，立即停止
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
            # 任务已被删除 → 确保 job 也被移除
            remove_job(task_id)
            return

        # 非 CRON 类型或已禁用 → 移除 job
        if task.type != "CRON" or task.status != "ENABLE":
            remove_job(task_id)
            return
        # 是启用的定时任务 → 注册/更新 job
        _add_task_job(task)
        # replace_existing=True 确保如果已存在，直接覆盖
        # 比如用户改了 cron 从 "每天8点" 改成 "每天9点"
        # 旧的 job 被覆盖，新的 cron 立即生效
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
