# core/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os
from dotenv import load_dotenv

# 获取数据库 URL
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL is None:
    raise ValueError("DATABASE_URL 未配置，请检查 .env 文件")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# 提供数据库 Session，用完自动关闭
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()