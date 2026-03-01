"""应用配置相关Schema"""
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

    class Config:
        extra = "allow"
