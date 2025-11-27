"""
数据库配置和连接
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config.settings import settings

# 数据库配置（统一从settings读取）
DATABASE_URL = settings.DATABASE_URL

# 创建数据库引擎
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False  # 设置为True可以看到SQL语句
    )
elif DATABASE_URL.startswith("mysql"):
    # MySQL数据库配置
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,  # 1小时回收连接
        pool_size=10,       # 连接池大小
        max_overflow=20,    # 最大溢出连接数
        echo=False,         # 设置为True可以看到SQL语句
        connect_args={
            "charset": "utf8mb4",
            "autocommit": False,  # 修改为False，让SQLAlchemy管理事务
            "connect_timeout": 60,  # 连接超时时间
            "read_timeout": 30,     # 读取超时时间
            "write_timeout": 30     # 写入超时时间
        }
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=False  # 设置为True可以看到SQL语句
    )

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基础模型类
Base = declarative_base()

# 依赖注入：获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()