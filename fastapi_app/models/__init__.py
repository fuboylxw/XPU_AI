"""SQLAlchemy数据库模型 - 按领域拆分，此处重新导出所有模型保持向后兼容"""
from fastapi_app.models.base import Base
from fastapi_app.models.config import AppConfig
from fastapi_app.models.conversation import Conversation, ConversationHistory
from fastapi_app.models.user import User
from fastapi_app.models.phone import PhoneSession, PhoneConversationHistory
from fastapi_app.models.work import WorkSession, WorkTask, WorkSubTask

__all__ = [
    "Base",
    "AppConfig",
    "Conversation",
    "ConversationHistory",
    "User",
    "PhoneSession",
    "PhoneConversationHistory",
    "WorkSession",
    "WorkTask",
    "WorkSubTask",
]
