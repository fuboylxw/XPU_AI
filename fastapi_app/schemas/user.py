"""用户认证相关Schema"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


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
    expires_in: int = 3600


class TokenData(BaseModel):
    """Token数据模型"""
    user_id: Optional[str] = None
