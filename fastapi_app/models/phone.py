"""电话会话模型"""
from sqlalchemy import Column, String, Text, DateTime, SmallInteger, Integer
from sqlalchemy.sql import func
from fastapi_app.models.base import Base


class PhoneSession(Base):
    """电话会话模型"""
    __tablename__ = "phone_session"

    id = Column(String(32), primary_key=True)
    user_id = Column(String(32), index=True)
    session_start = Column(DateTime, default=func.now())
    session_end = Column(DateTime, nullable=True)
    status = Column(SmallInteger, default=1)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class PhoneConversationHistory(Base):
    """电话对话历史记录模型"""
    __tablename__ = "phone_conversation_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(32), index=True)
    user_id = Column(String(32), index=True)
    question = Column(Text)
    answer = Column(Text)
    question_audio_path = Column(String(255), nullable=True)
    answer_audio_path = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=func.now())
