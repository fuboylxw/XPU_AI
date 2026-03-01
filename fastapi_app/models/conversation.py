"""对话相关模型"""
from sqlalchemy import Column, String, Text, DateTime, SmallInteger, Integer
from sqlalchemy.sql import func
from fastapi_app.models.base import Base


class Conversation(Base):
    __tablename__ = "chat_conversation"

    id = Column(String(32), primary_key=True)
    conversation_id = Column(String(50), unique=True, index=True)
    user_id = Column(String(32), index=True)
    title = Column(String(255), nullable=True)
    created = Column(DateTime, default=func.now())
    modified = Column(DateTime, default=func.now(), onupdate=func.now())
    status = Column(SmallInteger, default=1)


class ConversationHistory(Base):
    __tablename__ = "chat_conversation_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(50), index=True)
    question = Column(Text)
    answer = Column(Text)
    created_at = Column(DateTime, default=func.now())
