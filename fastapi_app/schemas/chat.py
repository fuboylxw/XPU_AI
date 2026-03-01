"""聊天消息相关Schema"""
from pydantic import BaseModel, Field
from datetime import datetime


class ChatMessageRequest(BaseModel):
    """聊天消息请求模型"""
    conversation_id: str = Field(..., max_length=50)
    message: str
    user_id: str = Field(default="default_user", max_length=32)
    use_web_search: bool = False


class ChatMessageResponse(BaseModel):
    """聊天消息响应模型"""
    conversation_id: str
    message: str
    response: str
    timestamp: datetime
