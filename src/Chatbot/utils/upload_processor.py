#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件上传处理器
处理前端上传的文本和图片文件，使用TTS智能体进行处理
"""

import os
import uuid
import base64
import logging
from typing import Optional, Dict, Any, Union
from pathlib import Path
import asyncio

# 导入TTS智能体和内存存储
from ..agents.text_to_speech_agent import TextToSpeechAgent
from .memory_storage import memory_storage, UploadedContent

logger = logging.getLogger(__name__)


class UploadProcessor:
    """文件上传处理器"""
    
    def __init__(self):
        """初始化上传处理器"""
        self.tts_agent = TextToSpeechAgent()
        logger.info("文件上传处理器初始化完成")
    
    async def process_text_upload(self, 
                                conversation_id: str, 
                                text_content: str, 
                                filename: Optional[str] = None) -> Dict[str, Any]:
        """
        处理文本上传
        
        Args:
            conversation_id: 会话ID
            text_content: 文本内容
            filename: 原始文件名
            
        Returns:
            处理结果字典
        """
        try:
            # 生成唯一内容ID
            content_id = str(uuid.uuid4())
            
            # 使用TTS智能体处理文本（这里主要是为了验证文本格式和内容）
            # 注意：我们不需要实际生成语音，只是利用TTS智能体的文本处理能力
            processed_text = await self._process_text_with_tts(text_content)
            
            # 创建上传内容对象
            uploaded_content = UploadedContent(
                content_id=content_id,
                content_type="text",
                content=processed_text,
                original_filename=filename,
                processed_by_tts=True
            )
            
            # 存储到内存
            memory_storage.store_content(conversation_id, uploaded_content)
            
            logger.info(f"文本上传处理完成: {content_id}")
            
            return {
                "success": True,
                "content_id": content_id,
                "content_type": "text",
                "processed_content": processed_text[:200] + "..." if len(processed_text) > 200 else processed_text,
                "message": "文本上传并处理成功"
            }
            
        except Exception as e:
            logger.error(f"文本上传处理失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "文本上传处理失败"
            }
    
    async def process_image_upload(self, 
                                 conversation_id: str, 
                                 image_data: Union[str, bytes], 
                                 filename: Optional[str] = None) -> Dict[str, Any]:
        """
        处理图片上传
        
        Args:
            conversation_id: 会话ID
            image_data: 图片数据（base64字符串或字节）
            filename: 原始文件名
            
        Returns:
            处理结果字典
        """
        try:
            # 生成唯一内容ID
            content_id = str(uuid.uuid4())
            
            # 处理图片数据
            if isinstance(image_data, str):
                # 如果是base64字符串，解码为字节
                try:
                    image_bytes = base64.b64decode(image_data)
                except Exception:
                    # 如果不是base64，可能是直接的文本描述
                    image_description = image_data
            else:
                # 如果是字节数据，这里可以集成OCR或图像识别
                # 暂时使用简单的描述
                image_description = f"上传的图片文件: {filename or '未知文件名'}"
            
            # 使用TTS智能体处理图片描述
            processed_description = await self._process_text_with_tts(image_description)
            
            # 创建上传内容对象
            uploaded_content = UploadedContent(
                content_id=content_id,
                content_type="image",
                content=processed_description,
                original_filename=filename,
                processed_by_tts=True
            )
            
            # 存储到内存
            memory_storage.store_content(conversation_id, uploaded_content)
            
            logger.info(f"图片上传处理完成: {content_id}")
            
            return {
                "success": True,
                "content_id": content_id,
                "content_type": "image",
                "processed_content": processed_description,
                "message": "图片上传并处理成功"
            }
            
        except Exception as e:
            logger.error(f"图片上传处理失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "图片上传处理失败"
            }
    
    async def _process_text_with_tts(self, text: str) -> str:
        """
        使用TTS智能体处理文本
        
        Args:
            text: 输入文本
            
        Returns:
            处理后的文本
        """
        try:
            # 这里我们不需要实际生成语音，只是利用TTS智能体的文本处理能力
            # 可以进行文本清理、格式化等操作
            
            # 简单的文本清理
            processed_text = text.strip()
            
            # 移除多余的空白字符
            processed_text = ' '.join(processed_text.split())
            
            # 如果文本太长，可以进行摘要处理
            if len(processed_text) > 2000:
                # 简单截取前2000字符，实际应用中可以使用更智能的摘要算法
                processed_text = processed_text[:2000] + "...[内容已截取]"
            
            return processed_text
            
        except Exception as e:
            logger.error(f"TTS文本处理失败: {str(e)}")
            return text  # 如果处理失败，返回原文本
    
    def get_uploaded_contents(self, conversation_id: str) -> Dict[str, Any]:
        """
        获取指定会话的上传内容
        
        Args:
            conversation_id: 会话ID
            
        Returns:
            上传内容信息
        """
        contents = memory_storage.get_contents(conversation_id)
        
        return {
            "conversation_id": conversation_id,
            "total_contents": len(contents),
            "contents": [
                {
                    "content_id": content.content_id,
                    "content_type": content.content_type,
                    "filename": content.original_filename,
                    "upload_time": content.upload_time,
                    "content_preview": content.content[:100] + "..." if len(content.content) > 100 else content.content
                }
                for content in contents
            ]
        }
    
    def clear_conversation_uploads(self, conversation_id: str) -> Dict[str, Any]:
        """
        清除指定会话的上传内容
        
        Args:
            conversation_id: 会话ID
            
        Returns:
            清除结果
        """
        contents_before = len(memory_storage.get_contents(conversation_id))
        memory_storage.clear_conversation(conversation_id)
        
        logger.info(f"清除会话 {conversation_id} 的 {contents_before} 个上传内容")
        
        return {
            "success": True,
            "conversation_id": conversation_id,
            "cleared_count": contents_before,
            "message": f"已清除 {contents_before} 个上传内容"
        }


# 全局上传处理器实例
upload_processor = UploadProcessor()