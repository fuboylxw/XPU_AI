"""对话相关Schema"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ConversationBase(BaseModel):
    """对话会话基础模型"""
    conversation_id: str = Field(..., max_length=50)
    user_id: str = Field(..., max_length=32)
    title: Optional[str] = Field(None, max_length=255)
    status: int = Field(default=1)


class ConversationCreate(BaseModel):
    """创建对话会话模型"""
    user_id: str = Field(..., max_length=32)
    title: Optional[str] = Field(None, max_length=255)
    status: int = Field(default=1)


class ConversationUpdate(BaseModel):
    """更新对话会话模型"""
    title: Optional[str] = Field(None, max_length=255)
    status: Optional[int] = None


class ConversationResponse(ConversationBase):
    """对话会话响应模型"""
    id: str
    created: datetime
    modified: datetime

    class Config:
        from_attributes = True


class ConversationHistoryBase(BaseModel):
    """对话历史基础模型"""
    conversation_id: str = Field(..., max_length=50)
    question: str
    answer: str


class ConversationHistoryCreate(ConversationHistoryBase):
    """创建对话历史模型"""
    pass


class ConversationHistoryResponse(ConversationHistoryBase):
    """对话历史响应模型"""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
