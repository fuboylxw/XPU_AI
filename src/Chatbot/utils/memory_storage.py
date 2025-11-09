#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内存存储管理器
用于临时存储上传的文本和图片信息，支持按会话ID管理
"""

import time
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class UploadedContent:
    """上传内容数据结构"""
    content_id: str
    content_type: str  # 'text' 或 'image'
    content: str  # 文本内容或图片描述
    original_filename: Optional[str] = None
    upload_time: float = None
    processed_by_tts: bool = False
    
    def __post_init__(self):
        if self.upload_time is None:
            self.upload_time = time.time()


class MemoryStorage:
    """内存存储管理器"""
    
    def __init__(self):
        """初始化内存存储"""
        self._storage: Dict[str, List[UploadedContent]] = {}
        self._lock = threading.RLock()
        logger.info("内存存储管理器初始化完成")
    
    def store_content(self, conversation_id: str, content: UploadedContent) -> None:
        """存储内容到指定会话"""
        with self._lock:
            if conversation_id not in self._storage:
                self._storage[conversation_id] = []
            
            self._storage[conversation_id].append(content)
            logger.info(f"存储内容到会话 {conversation_id}: {content.content_type} - {content.content_id}")
    
    def get_contents(self, conversation_id: str) -> List[UploadedContent]:
        """获取指定会话的所有内容"""
        with self._lock:
            return self._storage.get(conversation_id, []).copy()
    
    def search_relevant_content(self, conversation_id: str, query: str, max_results: int = 3) -> List[UploadedContent]:
        """根据查询搜索相关内容"""
        contents = self.get_contents(conversation_id)
        if not contents:
            return []
        
        # 简单的关键词匹配搜索
        relevant_contents = []
        query_lower = query.lower()
        
        for content in contents:
            content_lower = content.content.lower()
            # 计算相关性得分（简单的关键词匹配）
            score = 0
            for word in query_lower.split():
                if word in content_lower:
                    score += 1
            
            if score > 0:
                relevant_contents.append((content, score))
        
        # 按相关性得分排序
        relevant_contents.sort(key=lambda x: x[1], reverse=True)
        
        # 返回最相关的内容
        result = [content for content, _ in relevant_contents[:max_results]]
        logger.info(f"为查询 '{query}' 找到 {len(result)} 个相关内容")
        return result
    
    def clear_conversation(self, conversation_id: str) -> None:
        """清除指定会话的所有内容"""
        with self._lock:
            if conversation_id in self._storage:
                count = len(self._storage[conversation_id])
                del self._storage[conversation_id]
                logger.info(f"清除会话 {conversation_id} 的 {count} 个内容")
    
    def clear_all(self) -> None:
        """清除所有内容"""
        with self._lock:
            total_conversations = len(self._storage)
            total_contents = sum(len(contents) for contents in self._storage.values())
            self._storage.clear()
            logger.info(f"清除所有内容: {total_conversations} 个会话, {total_contents} 个内容")
    
    def get_storage_info(self) -> Dict[str, Any]:
        """获取存储信息"""
        with self._lock:
            info = {
                "total_conversations": len(self._storage),
                "total_contents": sum(len(contents) for contents in self._storage.values()),
                "conversations": {}
            }
            
            for conv_id, contents in self._storage.items():
                info["conversations"][conv_id] = {
                    "content_count": len(contents),
                    "content_types": [c.content_type for c in contents]
                }
            
            return info


# 全局内存存储实例
memory_storage = MemoryStorage()