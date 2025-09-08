"""会话管理器实现
负责管理用户会话状态和生命周期
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from .interfaces import ISessionManager
from .config import get_settings
import logging

logger = logging.getLogger(__name__)


class InMemorySessionManager(ISessionManager):
    """内存会话管理器"""
    
    def __init__(self, session_timeout: int = 3600):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.session_timeout = session_timeout
        self._cleanup_task = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """启动清理任务"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    async def _periodic_cleanup(self):
        """定期清理过期会话"""
        while True:
            try:
                await asyncio.sleep(300)  # 每5分钟清理一次
                await self.cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"会话清理任务出错: {e}")
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话"""
        session = self.sessions.get(session_id)
        if session:
            # 检查会话是否过期
            if self._is_session_expired(session):
                await self.delete_session(session_id)
                return None
            # 更新最后访问时间
            session['last_accessed'] = datetime.now()
        return session
    
    async def get_or_create_session(self, session_id: str = None) -> Dict[str, Any]:
        """获取或创建会话"""
        if session_id:
            session = await self.get_session(session_id)
            if session:
                return session
        
        # 创建新会话
        return await self.create_session(session_id)
    
    async def create_session(self, session_id: str = None) -> Dict[str, Any]:
        """创建会话"""
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        session = {
            'session_id': session_id,
            'created_at': datetime.now(),
            'last_accessed': datetime.now(),
            'messages': [],
            'context': {},
            'user_info': {},
            'metadata': {}
        }
        
        self.sessions[session_id] = session
        logger.info(f"创建新会话: {session_id}")
        return session
    
    async def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """更新会话"""
        session = await self.get_session(session_id)
        if session is None:
            return False
        
        # 更新会话数据
        for key, value in data.items():
            if key in ['messages', 'context', 'user_info', 'metadata']:
                if isinstance(value, dict) and key in session:
                    session[key].update(value)
                else:
                    session[key] = value
        
        session['last_accessed'] = datetime.now()
        return True
    
    async def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"删除会话: {session_id}")
            return True
        return False
    
    async def cleanup_expired_sessions(self) -> int:
        """清理过期会话"""
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if self._is_session_expired(session):
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            await self.delete_session(session_id)
        
        if expired_sessions:
            logger.info(f"清理了 {len(expired_sessions)} 个过期会话")
        
        return len(expired_sessions)
    
    async def add_message(self, session_id: str, message) -> bool:
        """添加消息到会话"""
        session = await self.get_session(session_id)
        if session is None:
            return False
        
        # 将消息转换为字典格式
        if hasattr(message, 'model_dump'):
            message_dict = message.model_dump()
        elif hasattr(message, 'dict'):
            message_dict = message.dict()
        else:
            message_dict = {
                'role': getattr(message, 'role', 'unknown'),
                'content': getattr(message, 'content', str(message)),
                'timestamp': getattr(message, 'timestamp', datetime.now())
            }
        
        session['messages'].append(message_dict)
        session['last_accessed'] = datetime.now()
        return True
    
    def _is_session_expired(self, session: Dict[str, Any]) -> bool:
        """检查会话是否过期"""
        last_accessed = session.get('last_accessed', session.get('created_at'))
        if last_accessed:
            return datetime.now() - last_accessed > timedelta(seconds=self.session_timeout)
        return True
    
    async def get_session_count(self) -> int:
        """获取当前会话数量"""
        return len(self.sessions)
    
    async def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """获取所有会话（调试用）"""
        return self.sessions.copy()
    
    def __del__(self):
        """析构函数，取消清理任务"""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()