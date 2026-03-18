# services/script_service.py

import json
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from models.script_info import ScriptInfo
from models.script_version import ScriptVersion
from schemas.script import (
    ScriptListRequest, ScriptListResponse, ScriptListItem,
    DeleteResponse, UpdateRequest, UpdateResponse,
)
from schemas.script_editor import (
    SaveRequest, SaveResponse,
    ValidateRequest, ValidateResponse,
    LoadResponse,
    HistoryResponse, HistoryVersionDto,
)
from core.user_context import get_current_user_id
from services.minio_service import MinioFileService
from engine.python_script_generator import PythonScriptGenerator


class ScriptService:

    def __init__(self, db: Session):
        self.db = db
        self.minio = MinioFileService()
        self.python_gen = PythonScriptGenerator()

    # ─── 保存脚本 ────────────────────────────────────────────────────────────

    def save_script(self, request: SaveRequest) -> SaveResponse:
        db = self.db
        script_id = request.script_id
        content = request.content
        current_user = get_current_user_id()
        is_new = False

        script_info: Optional[ScriptInfo] = None
        if script_id:
            script_info = db.query(ScriptInfo).filter(ScriptInfo.script_id == script_id).first()

        if script_info is None:
            is_new = True
            script_info = ScriptInfo()

            # 自增 script_id
            max_id = db.query(ScriptInfo).count()
            all_scripts = db.query(ScriptInfo).all()
            max_num = 0
            for s in all_scripts:
                try:
                    num = int(s.script_id)
                    if num > max_num:
                        max_num = num
                except (ValueError, TypeError):
                    pass
            script_id = str(max_num + 1)

            script_info.script_id = script_id
            script_info.create_time = datetime.now()
            script_info.latest_version = "1"
            script_info.creator = current_user
            script_info.name = request.script_name if request.script_name else f"脚本-{script_id}"
            script_info.type = "GENERAL"
            script_info.status = "ENABLED"

        # 计算新版本号
        current_version = script_info.latest_version or "0"
        if not current_version or current_version.startswith("V"):
            current_version = "0"

        new_version = "1"
        try:
            new_version = str(int(current_version) + 1)
        except ValueError:
            pass

        if is_new:
            new_version = "1"

        try:
            content_json = json.dumps(content.dict(), ensure_ascii=False)

            # 1. 上传 JSON 配置到 MinIO
            file_name = f"scripts/{script_id}/{new_version}.json"
            self.minio.upload_file(file_name, content_json, "application/json")

            # 2. 生成并上传 Python 脚本
            try:
                python_code = self.python_gen.generate(content)
                py_file = f"scripts/{script_id}/{new_version}.py"
                self.minio.upload_file(py_file, python_code, "text/x-python")
                print(f"成功生成并存储 Python 脚本至: {py_file}")
            except ValueError as ve:
                error_msg = str(ve)
                print(f"⚠️ 脚本逻辑校验未通过，拒绝保存: {error_msg}")
                # 向前端抛出 400 Bad Request，告诉用户是他画的图有问题
                raise HTTPException(status_code=400, detail=error_msg)
            except Exception as e:
                print(f"自动生成 Python 脚本失败: {e}")

            # 3. 生成并上传 XML 测试用例
            try:
                xml_code = self.xml_gen.generate(content)
                xml_file = f"scripts/{script_id}/{new_version}.xml"
                self.minio.upload_file(xml_file, xml_code, "application/xml")
                print(f"成功生成并存储 XML 脚本至: {xml_file}")
            except Exception as e:
                print(f"自动生成 XML 脚本失败: {e}")

            # 更新 ScriptInfo
            script_info.content = file_name
            script_info.latest_version = new_version
            if request.script_name:
                script_info.name = request.script_name

            if is_new:
                db.add(script_info)
            db.flush()

            # 插入 ScriptVersion，自增 version_id
            all_versions = db.query(ScriptVersion).all()
            max_vid = 0
            for v in all_versions:
                try:
                    num = int(v.version_id)
                    if num > max_vid:
                        max_vid = num
                except (ValueError, TypeError):
                    pass

            version = ScriptVersion(
                version_id=str(max_vid + 1),
                script_id=script_id,
                version=new_version,
                content=file_name,
                modify_time=datetime.now(),
                modifier=current_user,
                change_log=request.changelog,
            )
            db.add(version)
            db.commit()

            return SaveResponse(success=True, script_id=script_id, version=new_version, message="保存成功")

        except Exception as e:
            db.rollback()
            print(f"保存脚本异常: {e}")
            return SaveResponse(success=False, script_id=script_id, version=current_version, message=f"Error: {e}")



    # ─── 加载最新版本 ────────────────────────────────────────────────────────

    def load_script(self, script_id: str) -> LoadResponse:
        print(f"Loading script: {script_id}")
        info = self.db.query(ScriptInfo).filter(ScriptInfo.script_id == script_id).first()
        if not info:
            return LoadResponse(name="", content=None)

        config = None
        try:
            latest = (
                self.db.query(ScriptVersion)
                .filter(ScriptVersion.script_id == script_id)
                .order_by(desc(ScriptVersion.modify_time))
                .first()
            )
            if latest and latest.content:
                json_str = self.minio.get_file_content(latest.content)
                if json_str:
                    config = json.loads(json_str)
        except Exception as e:
            print(f"Error loading script: {e}")

        return LoadResponse(name=info.name, content=config or {"nodes": [], "connections": []})

    # ─── 加载指定版本 ────────────────────────────────────────────────────────

    def load_script_version(self, script_id: str, version_id: str) -> LoadResponse:
        info = self.db.query(ScriptInfo).filter(ScriptInfo.script_id == script_id).first()
        if not info:
            return LoadResponse(name="", content=None)

        config = None
        try:
            v = (
                self.db.query(ScriptVersion)
                .filter(
                    ScriptVersion.script_id == script_id,
                    ScriptVersion.version_id == version_id,
                )
                .first()
            )
            if v and v.content:
                json_str = self.minio.get_file_content(v.content)
                if json_str:
                    config = json.loads(json_str)
        except Exception as e:
            print(f"Error loading version: {e}")

        return LoadResponse(name=info.name, content=config or {"nodes": [], "connections": []})

    # ─── 历史版本列表 ────────────────────────────────────────────────────────

    def get_script_history(self, script_id: str) -> HistoryResponse:
        versions = (
            self.db.query(ScriptVersion)
            .filter(ScriptVersion.script_id == script_id)
            .order_by(desc(ScriptVersion.modify_time))
            .all()
        )
        fmt = "%Y-%m-%d %H:%M:%S"
        items = [
            HistoryVersionDto(
                version_id=v.version_id,
                version=v.version,
                modify_time=v.modify_time.strftime(fmt) if v.modify_time else "",
                summary=v.change_log if v.change_log else "无提要",
            )
            for v in versions
        ]
        return HistoryResponse(list=items)

    # ─── 脚本列表（分页） ────────────────────────────────────────────────────

    def get_script_list(self, request: ScriptListRequest) -> ScriptListResponse:
        db = self.db
        query = db.query(ScriptInfo)

        user_id = get_current_user_id()
        if user_id:
            query = query.filter(ScriptInfo.creator == user_id)
        if request.keyword:
            query = query.filter(ScriptInfo.name.like(f"%{request.keyword}%"))
        if request.type:
            query = query.filter(ScriptInfo.type == request.type)

        query = query.order_by(desc(ScriptInfo.create_time))

        total = query.count()
        records = query.offset((request.page - 1) * request.size).limit(request.size).all()

        items = [
            ScriptListItem(
                script_id=s.script_id,
                name=s.name,
                type=s.type,
                status=s.status,
                creator=s.creator,
                create_time=s.create_time,
                update_time="",
                latest_version=s.latest_version,
            )
            for s in records
        ]
        return ScriptListResponse(list=items, total=total)

    # ─── 删除脚本 ────────────────────────────────────────────────────────────

    def delete_script(self, script_id: str) -> DeleteResponse:
        try:
            self.db.query(ScriptVersion).filter(ScriptVersion.script_id == script_id).delete()
            rows = self.db.query(ScriptInfo).filter(ScriptInfo.script_id == script_id).delete()
            self.db.commit()

            if rows > 0:
                return DeleteResponse(success=True, message="删除成功")
            return DeleteResponse(success=False, message="脚本不存在或已删除")
        except Exception as e:
            self.db.rollback()
            return DeleteResponse(success=False, message=f"删除失败: {e}")

    # ─── 更新脚本元信息 ──────────────────────────────────────────────────────

    def update_script(self, request: UpdateRequest) -> UpdateResponse:
        try:
            info = self.db.query(ScriptInfo).filter(ScriptInfo.script_id == request.script_id).first()
            if info:
                if request.name:
                    info.name = request.name
                if request.status:
                    info.status = request.status
                self.db.commit()
                return UpdateResponse(success=True, message="更新成功")
            return UpdateResponse(success=False, message="脚本未找到")
        except Exception as e:
            self.db.rollback()
            return UpdateResponse(success=False, message=f"更新失败: {e}")