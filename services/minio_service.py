# services/minio_service.py
import io
import os
from minio import Minio
from minio.error import S3Error
from loguru import logger

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
if MINIO_ENDPOINT.startswith("http://"):
    MINIO_ENDPOINT = MINIO_ENDPOINT.replace("http://", "")
elif MINIO_ENDPOINT.startswith("https://"):
    MINIO_ENDPOINT = MINIO_ENDPOINT.replace("https://", "")
if MINIO_ENDPOINT.endswith("/"):
    MINIO_ENDPOINT = MINIO_ENDPOINT[:-1]

MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
MINIO_BUCKET = "abs-scripts"


class MinioFileService:

    def __init__(self):
        self.client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE,
        )
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            if not self.client.bucket_exists(MINIO_BUCKET):
                self.client.make_bucket(MINIO_BUCKET)
        except Exception as e:
            from loguru import logger
            logger.warning(f"MinIO bucket check failed: {e}")

    def upload_file(self, file_name: str, content: str, content_type: str = "application/octet-stream") -> str:
        data = content.encode("utf-8")
        self.client.put_object(
            MINIO_BUCKET,
            file_name,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return file_name

    def get_file_content(self, file_name: str) -> str:
        try:
            response = self.client.get_object(MINIO_BUCKET, file_name)
            return response.read().decode("utf-8")
        except S3Error as e:
            logger.error(f"MinIO get_object failed [{file_name}]: {e}")
            return ""
        finally:
            try:
                response.close()
                response.release_conn()
            except Exception:
                pass
