"""工作会话/任务模型"""
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from fastapi_app.models.base import Base


class WorkSession(Base):
    __tablename__ = "work_sessions"
    __table_args__ = (
        UniqueConstraint("session_id", name="uq_work_sessions_session_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), index=True, nullable=False)
    user_id = Column(String(32), index=True)
    title = Column(String(255))
    status = Column(String(32), default="loading")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class WorkTask(Base):
    __tablename__ = "work_tasks"

    task_id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), ForeignKey("work_sessions.session_id"), index=True)
    task_name = Column(String(255), nullable=True)
    status = Column(String(32), nullable=True)
    result = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class WorkSubTask(Base):
    __tablename__ = "work_sub_tasks"

    task_sub_id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), index=True)
    task_id = Column(Integer, ForeignKey("work_tasks.task_id"), index=True)
    sub_task_name = Column(String(255), nullable=True)
    order = Column(Integer)
    status = Column(String(32), nullable=True)
    result = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
