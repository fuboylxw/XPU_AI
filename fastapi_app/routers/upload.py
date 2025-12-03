#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件上传API路由
支持文本和图片文件上传，使用TTS智能体处理并临时存储
"""

import os
import uuid
import base64
import logging
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# 导入上传处理器
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.Chatbot.utils.upload_processor import upload_processor
from src.Chatbot.utils.memory_storage import memory_storage

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/upload", tags=["upload"])


class TextUploadRequest(BaseModel):
    """文本上传请求模型"""
    conversation_id: str
    text_content: str
    filename: Optional[str] = None


class UploadResponse(BaseModel):
    """上传响应模型"""
    success: bool
    content_id: Optional[str] = None
    content_type: Optional[str] = None
    processed_content: Optional[str] = None
    message: str
    error: Optional[str] = None


class ContentListResponse(BaseModel):
    """内容列表响应模型"""
    conversation_id: str
    total_contents: int
    contents: List[dict]


@router.post("/text", response_model=UploadResponse)
async def upload_text(request: TextUploadRequest):
    """
    上传文本内容
    
    Args:
        request: 文本上传请求
        
    Returns:
        上传处理结果
    """
    try:
        logger.info(f"接收到文本上传请求: 会话ID={request.conversation_id}")
        
        # 验证输入
        if not request.conversation_id or not request.text_content:
            raise HTTPException(status_code=400, detail="会话ID和文本内容不能为空")
        
        if len(request.text_content) > 10000:  # 限制文本长度
            raise HTTPException(status_code=400, detail="文本内容过长，最大支持10000字符")
        
        # 使用上传处理器处理文本
        result = await upload_processor.process_text_upload(
            conversation_id=request.conversation_id,
            text_content=request.text_content,
            filename=request.filename
        )
        
        if result["success"]:
            return UploadResponse(**result)
        else:
            raise HTTPException(status_code=500, detail=result.get("message", "文本处理失败"))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文本上传处理异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")


@router.post("/file", response_model=UploadResponse)
async def upload_file(
    conversation_id: str = Form(...),
    file: UploadFile = File(...)
):
    """
    上传文件（支持文本文件和图片文件）
    
    Args:
        conversation_id: 会话ID
        file: 上传的文件
        
    Returns:
        上传处理结果
    """
    try:
        logger.info(f"接收到文件上传请求: 会话ID={conversation_id}, 文件名={file.filename}")
        
        # 验证输入
        if not conversation_id:
            raise HTTPException(status_code=400, detail="会话ID不能为空")
        
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        
        # 检查文件大小（限制为5MB）
        file_content = await file.read()
        if len(file_content) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="文件大小不能超过5MB")
        
        # 获取文件扩展名
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        # 支持的文本文件类型
        text_extensions = ['.txt', '.md', '.json', '.csv', '.log', '.py', '.js', '.html', '.css']
        # 支持的图片文件类型
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        
        if file_extension in text_extensions or file.content_type.startswith('text/'):
            # 处理文本文件
            try:
                text_content = file_content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    text_content = file_content.decode('gbk')
                except UnicodeDecodeError:
                    raise HTTPException(status_code=400, detail="无法解码文本文件，请确保文件编码为UTF-8或GBK")
            
            result = await upload_processor.process_text_upload(
                conversation_id=conversation_id,
                text_content=text_content,
                filename=file.filename
            )
            
        elif file_extension in image_extensions or file.content_type.startswith('image/'):
            # 处理图片文件
            # 将图片转换为base64字符串
            image_base64 = base64.b64encode(file_content).decode('utf-8')
            
            result = await upload_processor.process_image_upload(
                conversation_id=conversation_id,
                image_data=image_base64,
                filename=file.filename
            )
            
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件类型: {file_extension}。支持的类型: {text_extensions + image_extensions}"
            )
        
        if result["success"]:
            return UploadResponse(**result)
        else:
            raise HTTPException(status_code=500, detail=result.get("message", "文件处理失败"))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传处理异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")


@router.get("/contents/{conversation_id}", response_model=ContentListResponse)
async def get_uploaded_contents(conversation_id: str):
    """
    获取指定会话的上传内容列表
    
    Args:
        conversation_id: 会话ID
        
    Returns:
        上传内容列表
    """
    try:
        logger.info(f"获取会话 {conversation_id} 的上传内容列表")
        
        if not conversation_id:
            raise HTTPException(status_code=400, detail="会话ID不能为空")
        
        result = upload_processor.get_uploaded_contents(conversation_id)
        return ContentListResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取上传内容列表异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")


@router.delete("/contents/{conversation_id}")
async def clear_uploaded_contents(conversation_id: str):
    """
    清除指定会话的上传内容
    
    Args:
        conversation_id: 会话ID
        
    Returns:
        清除结果
    """
    try:
        logger.info(f"清除会话 {conversation_id} 的上传内容")
        
        if not conversation_id:
            raise HTTPException(status_code=400, detail="会话ID不能为空")
        
        result = upload_processor.clear_conversation_uploads(conversation_id)
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清除上传内容异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")


@router.get("/storage/info")
async def get_storage_info():
    """
    获取内存存储信息
    
    Returns:
        存储信息统计
    """
    try:
        info = memory_storage.get_storage_info()
        return JSONResponse(content=info)
        
    except Exception as e:
        logger.error(f"获取存储信息异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")


@router.delete("/storage/clear")
async def clear_all_storage():
    """
    清除所有存储内容（管理员功能）
    
    Returns:
        清除结果
    """
    try:
        logger.warning("执行清除所有存储内容操作")
        memory_storage.clear_all()
        return JSONResponse(content={
            "success": True,
            "message": "已清除所有存储内容"
        })
        
    except Exception as e:
        logger.error(f"清除所有存储内容异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")