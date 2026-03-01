"""用户模型"""
from sqlalchemy import Column, String, DateTime, SmallInteger
from sqlalchemy.sql import func
from fastapi_app.models.base import Base


class User(Base):
    """用户模型"""
    __tablename__ = "users"

    id = Column(String(32), primary_key=True)
    username = Column(String(50), unique=True, index=True, nullable=True)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255))
    nickname = Column(String(50), nullable=True)
    avatar_url = Column(String(255), nullable=True)
    is_active = Column(SmallInteger, default=1)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login = Column(DateTime, nullable=True)
