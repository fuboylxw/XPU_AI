#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据查询API路由
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.Chatbot.agents.data_query_agent import DataQueryAgent, UserRole
from fastapi_app.auth import get_current_active_user
from fastapi_app.models import User
from fastapi_app.database import get_db

router = APIRouter(prefix="/api/data", tags=["data_query"])

# 全局数据查询智能体实例
data_query_agent = DataQueryAgent()

class DataQueryRequest(BaseModel):
    """数据查询请求模型"""
    query: str
    session_token: Optional[str] = None

class DataQueryResponse(BaseModel):
    """数据查询响应模型"""
    success: bool
    query: str
    results: Any
    metadata: Optional[Dict[str, Any]] = None
    timestamp: str
    error: Optional[str] = None

def get_user_role_enum(user: User) -> UserRole:
    """将用户对象转换为UserRole枚举"""
    # 这里可以根据用户的角色字段或其他属性来确定角色
    # 暂时默认所有用户为学生角色，可以根据实际需求修改
    if hasattr(user, 'role'):
        role_mapping = {
            "student": UserRole.STUDENT,
            "teacher": UserRole.TEACHER,
            "admin": UserRole.ADMIN,
            "guest": UserRole.GUEST
        }
        return role_mapping.get(user.role.lower(), UserRole.STUDENT)
    else:
        # 如果没有角色字段，默认为学生
        return UserRole.STUDENT

@router.post("/query", response_model=DataQueryResponse)
async def query_data(
    request: DataQueryRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    执行数据查询
    
    Args:
        request: 查询请求，包含查询内容和可选的会话令牌
        current_user: 当前认证用户
        db: 数据库会话
    
    Returns:
        DataQueryResponse: 查询结果响应
    """
    try:
        # 获取用户ID和角色
        user_id = str(current_user.id)
        user_role = get_user_role_enum(current_user)
        
        # 创建或获取用户会话
        if not request.session_token:
            session_token = data_query_agent.create_user_session(user_id, user_role)
        else:
            session_token = request.session_token
        
        # 执行数据查询
        result = await data_query_agent.query_data(
            query=request.query,
            user_id=user_id,
            user_role=user_role,
            session_token=session_token
        )
        
        # 返回响应
        return DataQueryResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询执行失败: {str(e)}"
        )

@router.post("/session/create")
async def create_session(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    创建用户会话
    
    Args:
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        会话令牌
    """
    try:
        user_id = current_user.id
        user_role = get_user_role_enum(current_user)
        
        # 创建会话
        session_token = data_query_agent.create_user_session(user_id, user_role)
        
        return {
            "success": True,
            "session_token": session_token,
            "user_id": user_id,
            "user_role": user_role.value
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"会话创建失败: {str(e)}"
        )

@router.delete("/session/revoke")
async def revoke_session(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    撤销用户会话
    
    Args:
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        操作结果
    """
    try:
        user_id = current_user.id
        
        # 撤销会话
        data_query_agent.revoke_user_session(user_id)
        
        return {
            "success": True,
            "message": "会话已撤销"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"会话撤销失败: {str(e)}"
        )

@router.get("/statistics")
async def get_query_statistics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取查询统计信息
    
    Args:
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        统计信息
    """
    try:
        user_id = current_user.id
        user_role = get_user_role_enum(current_user)
        
        # 只有管理员可以查看所有统计，其他用户只能查看自己的
        if user_role == UserRole.ADMIN:
            stats = data_query_agent.get_query_statistics()
        else:
            stats = data_query_agent.get_query_statistics(user_id)
        
        return {
            "success": True,
            "statistics": stats
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取统计信息失败: {str(e)}"
        )