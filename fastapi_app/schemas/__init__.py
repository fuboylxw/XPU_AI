"""Pydantic模型定义 - 按领域拆分，此处重新导出所有Schema保持向后兼容"""
from fastapi_app.schemas.config import (
    AppConfigBase, AppConfigCreate, AppConfigUpdate, AppConfigResponse,
    SystemStatusResponse, AppConfigFullResponse,
)
from fastapi_app.schemas.conversation import (
    ConversationBase, ConversationCreate, ConversationUpdate, ConversationResponse,
    ConversationHistoryBase, ConversationHistoryCreate, ConversationHistoryResponse,
)
from fastapi_app.schemas.user import (
    UserBase, UserCreate, UserLogin, UserResponse, LoginResponse, TokenData,
)
from fastapi_app.schemas.chat import ChatMessageRequest, ChatMessageResponse
from fastapi_app.schemas.work import (
    WorkSubTaskUpdate, WorkSubTaskResponse,
    WorkTaskBase, WorkTaskCreate, WorkTaskUpdate, WorkTaskResponse,
    WorkTaskHistoryBase, WorkTaskHistoryCreate, WorkTaskHistoryResponse, WorkTaskHistoryUpdate,
    WorkSessionCreate, WorkSessionUpdate, WorkSessionResponse,
    WorkTaskItemCreate, WorkTaskItemUpdate, WorkTaskItemResponse,
    TaskRunRequest, TaskSubmitRequest,
)

__all__ = [
    "AppConfigBase", "AppConfigCreate", "AppConfigUpdate", "AppConfigResponse",
    "SystemStatusResponse", "AppConfigFullResponse",
    "ConversationBase", "ConversationCreate", "ConversationUpdate", "ConversationResponse",
    "ConversationHistoryBase", "ConversationHistoryCreate", "ConversationHistoryResponse",
    "UserBase", "UserCreate", "UserLogin", "UserResponse", "LoginResponse", "TokenData",
    "ChatMessageRequest", "ChatMessageResponse",
    "WorkSubTaskUpdate", "WorkSubTaskResponse",
    "WorkTaskBase", "WorkTaskCreate", "WorkTaskUpdate", "WorkTaskResponse",
    "WorkTaskHistoryBase", "WorkTaskHistoryCreate", "WorkTaskHistoryResponse", "WorkTaskHistoryUpdate",
    "WorkSessionCreate", "WorkSessionUpdate", "WorkSessionResponse",
    "WorkTaskItemCreate", "WorkTaskItemUpdate", "WorkTaskItemResponse",
    "TaskRunRequest", "TaskSubmitRequest",
]
