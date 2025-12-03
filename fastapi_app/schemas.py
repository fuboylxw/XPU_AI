"""
Pydantic模型定义
"""
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from datetime import datetime


class AppConfigBase(BaseModel):
    """应用配置基础模型"""
    key: str = Field(..., max_length=100)
    value: str
    description: Optional[str] = Field(None, max_length=255)


class AppConfigCreate(AppConfigBase):
    """创建应用配置模型"""
    pass


class AppConfigUpdate(BaseModel):
    """更新应用配置模型"""
    value: Optional[str] = None
    description: Optional[str] = None


class AppConfigResponse(AppConfigBase):
    """应用配置响应模型"""
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class WorkSubTaskUpdate(BaseModel):
    sub_task_name: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = None
    result: Optional[str] = None


class WorkSubTaskResponse(BaseModel):
    id: int
    session_id: str
    task_id: int
    sub_task_name: Optional[str] = None
    order: Optional[int] = 0
    status: Optional[str] = "waiting"
    result: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


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


class SystemStatusResponse(BaseModel):
    """系统状态响应模型"""
    llm_status: str
    memory_status: str
    tools_status: Dict[str, Any]
    agents_status: Dict[str, Any]
    last_update: str
    uptime: int


class AppConfigFullResponse(BaseModel):
    """完整应用配置响应模型"""
    system_status: SystemStatusResponse
    current_model: Optional[str] = None
    current_temperature: Optional[float] = None
    current_max_tokens: Optional[int] = None
    # 其他配置项可以动态添加
    
    class Config:
        extra = "allow"  # 允许额外字段


# 用户认证相关模型
class UserBase(BaseModel):
    """用户基础模型"""
    username: Optional[str] = Field(None, max_length=50)
    email: str = Field(..., max_length=100, description="邮箱地址（必填）")
    nickname: Optional[str] = Field(None, max_length=50)
    avatar_url: Optional[str] = Field(None, max_length=255)


class UserCreate(BaseModel):
    """用户创建模型"""
    username: Optional[str] = Field(None, max_length=50)
    email: str = Field(..., max_length=100, description="邮箱地址（必填）")
    password: str = Field(..., min_length=6, max_length=50)
    nickname: Optional[str] = Field(None, max_length=50)


class UserLogin(BaseModel):
    """用户登录模型"""
    username_or_email: str = Field(..., max_length=100, description="用户名或邮箱地址")
    password: str = Field(..., min_length=6, max_length=50)


class UserResponse(UserBase):
    """用户响应模型"""
    id: str
    is_active: int
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """登录响应模型"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    expires_in: int = 3600  # token过期时间（秒）


class TokenData(BaseModel):
    """Token数据模型"""
    user_id: Optional[str] = None


class WorkTaskBase(BaseModel):
    conversation_id: str = Field(..., max_length=50)
    user_id: str = Field(..., max_length=32)
    title: str = Field(..., max_length=255)
    status: Optional[str] = Field(default="loading", max_length=32)


class WorkTaskCreate(BaseModel):
    conversation_id: str = Field(..., max_length=50)
    user_id: str = Field(..., max_length=32)
    title: str = Field(..., max_length=255)
    status: Optional[str] = Field(default="loading", max_length=32)


class WorkTaskUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = Field(None, max_length=32)


class WorkTaskResponse(WorkTaskBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class WorkTaskHistoryBase(BaseModel):
    task_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None
    result: Optional[str] = None


class WorkTaskHistoryCreate(WorkTaskHistoryBase):
    pass


class WorkTaskHistoryResponse(WorkTaskHistoryBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class WorkTaskHistoryUpdate(BaseModel):
    task_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None
    result: Optional[str] = None


# 工作模式（Session/Task）相关模型，适配 routers/tasks.py 使用

class WorkSessionCreate(BaseModel):
    session_id: str = Field(..., max_length=50)
    user_id: str = Field(..., max_length=32)
    title: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = Field(default="loading", max_length=32)


class WorkSessionUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = Field(None, max_length=32)


class WorkSessionResponse(BaseModel):
    id: int
    session_id: str
    user_id: str
    title: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class WorkTaskItemCreate(BaseModel):
    task_name: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = None
    result: Optional[str] = None


class WorkTaskItemUpdate(BaseModel):
    task_name: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = None
    result: Optional[str] = None


class WorkTaskItemResponse(BaseModel):
    id: int
    session_id: str
    task_name: Optional[str]
    status: Optional[str]
    result: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TaskRunRequest(BaseModel):
    task_id: int = Field(..., description="任务ID")
    user_id: str = Field(..., description="用户ID")

class TaskSubmitRequest(BaseModel):
    session_id: str
    question: str
    user_id: str = "guest"
    user_role: str = "guest"
    session_token: Optional[str] = None
    
    class Config:
        from_attributes = True
