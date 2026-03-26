# services/log_service.py
from datetime import datetime
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from models.script_execlog import ScriptExecLog
from models.task_info import TaskInfo
from schemas.log import LogDto, LogListRequest, LogListResponse
from services.minio_service import MinioFileService
from core.user_context import get_current_user_id


class LogService:

    def __init__(self, db: Session):
        self.db = db

    def get_log_list(self, request: LogListRequest) -> LogListResponse:
        query = self.db.query(ScriptExecLog)

        # 按当前登录用户过滤（日志表无 creator 字段，通过 task_id 关联 task_info 过滤）
        user_id = get_current_user_id()
        if user_id:
            user_task_ids = [
                t.task_id for t in
                self.db.query(TaskInfo.task_id).filter(TaskInfo.creator == user_id).all()
            ]
            query = query.filter(ScriptExecLog.task_id.in_(user_task_ids))

        # 关键字模糊搜索 taskId / deviceId
        if request.keyword:
            kw = f"%{request.keyword}%"
            query = query.filter(
                or_(
                    ScriptExecLog.task_id.like(kw),
                    ScriptExecLog.device_id.like(kw),
                )
            )

        # 状态筛选（CANCELLED 同时匹配数据库中的 STOPPED）
        if request.exec_status:
            if request.exec_status == "CANCELLED":
                query = query.filter(
                    or_(
                        ScriptExecLog.exec_status == "CANCELLED",
                        ScriptExecLog.exec_status == "STOPPED",
                    )
                )
            else:
                query = query.filter(ScriptExecLog.exec_status == request.exec_status)

        # 日期范围筛选（按 start_time）
        if request.start_date:
            start_dt = datetime.strptime(request.start_date, "%Y-%m-%d")
            query = query.filter(ScriptExecLog.start_time >= start_dt)
        if request.end_date:
            end_dt = datetime.strptime(request.end_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59
            )
            query = query.filter(ScriptExecLog.start_time <= end_dt)

        total = query.count()
        records = (
            query.order_by(ScriptExecLog.start_time.desc())
            .offset((request.page - 1) * request.size)
            .limit(request.size)
            .all()
        )

        items = [self._to_dto(r) for r in records]
        return LogListResponse(list=items, total=total)

    def get_log_content(self, log_id: str) -> Optional[str]:
        record = self.db.query(ScriptExecLog).filter(ScriptExecLog.log_id == log_id).first()
        if not record or not record.log_file_url:
            return None
        minio = MinioFileService()
        return minio.get_file_content(record.log_file_url)

    def get_log_file_info(self, log_id: str) -> Optional[tuple]:
        """返回 (log_file_url, filename)，供下载使用"""
        record = self.db.query(ScriptExecLog).filter(ScriptExecLog.log_id == log_id).first()
        if not record or not record.log_file_url:
            return None
        filename = f"log_{log_id}.log"
        return record.log_file_url, filename

    def delete_log(self, log_id: str) -> bool:
        record = self.db.query(ScriptExecLog).filter(ScriptExecLog.log_id == log_id).first()
        if not record:
            return False
        # 删除 MinIO 中的日志文件
        if record.log_file_url:
            minio = MinioFileService()
            minio.delete_file(record.log_file_url)
        self.db.delete(record)
        self.db.commit()
        return True

    @staticmethod
    def _to_dto(record: ScriptExecLog) -> LogDto:
        # 将数据库中的 STOPPED 统一对外展示为 CANCELLED
        status = record.exec_status
        if status == "STOPPED":
            status = "CANCELLED"
        return LogDto(
            logId=record.log_id,
            taskId=record.task_id,
            deviceId=record.device_id,
            execStatus=status,
            logFileUrl=record.log_file_url,
            startTime=record.start_time.strftime("%Y-%m-%dT%H:%M:%S") if record.start_time else None,
            endTime=record.end_time.strftime("%Y-%m-%dT%H:%M:%S") if record.end_time else None,
        )
