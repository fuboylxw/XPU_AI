"""
对话服务类
封装SchoolInfoAgent功能，提供API接口支持
"""

import asyncio
import uuid
from typing import Dict, Optional, AsyncGenerator, Any, List
from datetime import datetime, timedelta
from pathlib import Path
import sys
import logging

# 添加src目录到Python路径
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from src.agent.school_info_agent import SchoolInfoAgent
from src.rag.document_manager import DocumentManager
from src.config.settings import get_settings, setup_logger
from .models import (
    ChatRequest, ChatResponse, StreamChatResponse,
    DocumentUploadRequest, DocumentUploadResponse,
    DocumentSearchRequest, DocumentSearchResponse,
    DocumentSummaryResponse, ChatMessage, ApiResponse
)
from .interfaces import IChatService, ISessionManager, IDocumentManager, ILLMClient, ISchoolInfoAgent
from .session_manager import InMemorySessionManager
from .config import get_settings as get_api_settings



class ChatService(IChatService):
    """对话服务类
    
    负责管理聊天会话和处理用户消息
    使用依赖注入降低耦合度
    """
    
    def __init__(self, 
                 session_manager: ISessionManager = None,
                 document_manager: IDocumentManager = None,
                 llm_client: ILLMClient = None,
                 school_info_agent: ISchoolInfoAgent = None):
        self.settings = get_settings()
        self.api_settings = get_api_settings()
        self.logger = self._setup_logger()
        
        # 依赖注入
        self.session_manager = session_manager or InMemorySessionManager(
            session_timeout=self.api_settings.session_timeout
        )
        self.document_manager = document_manager
        self.llm_client = llm_client
        self.school_info_agent = school_info_agent
        
        # 初始化智能代理（保持向后兼容）
        self.agent = None
        
        # 启动清理任务
        self._cleanup_task = None
        self._start_cleanup_task()
        
        self.logger.info("对话服务初始化完成")

    async def initialize(self):
        """初始化服务"""
        # 优先使用新的接口
        if self.school_info_agent is not None:
            # 使用注入的school_info_agent作为agent
            self.agent = self.school_info_agent
        elif self.agent is None:
            # 确保代理已初始化（向后兼容）
            await self._initialize_agent()
        self.logger.info("对话服务异步初始化完成")

    def _setup_logger(self):
        """设置日志记录器"""
        return setup_logger(self.settings)
    
    async def _initialize_agent(self):
        """初始化智能代理"""
        if self.document_manager is None:
            from document_manager import DocumentManager
            self.document_manager = DocumentManager(self.settings)
        
        self.agent = SchoolInfoAgent(self.settings, self.document_manager)
        self.logger.info("智能代理初始化完成")
    
    async def _get_or_create_session(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """获取或创建会话"""
        return await self.session_manager.get_or_create_session(session_id)
    
    async def _get_session_context(self, session: Dict[str, Any]) -> str:
        """获取会话上下文"""
        session_data = await self.session_manager.get_session(session['session_id'])
        if not session_data or 'messages' not in session_data:
            return ""
        
        # 获取最近的几条消息作为上下文
        messages = session_data['messages'][-5:]  # 最近5条消息
        context_parts = []
        for msg in messages:
            if hasattr(msg, 'role') and hasattr(msg, 'content'):
                context_parts.append(f"{msg.role}: {msg.content}")
            elif isinstance(msg, dict):
                context_parts.append(f"{msg.get('role', 'unknown')}: {msg.get('content', '')}")
        
        return "\n".join(context_parts)
    
    async def _cleanup_expired_sessions(self):
        """清理过期会话"""
        cleaned_count = await self.session_manager.cleanup_expired_sessions()
        if cleaned_count > 0:
            self.logger.info(f"清理了 {cleaned_count} 个过期会话")
    
    async def process_message(self, message: str, session_id: Optional[str] = None, **kwargs) -> ChatResponse:
        """处理消息 (已弃用，请使用process_message_stream)"""
        try:
            # 确保代理已初始化
            if self.agent is None:
                await self._initialize_agent()
            
            # 清理过期会话
            await self._cleanup_expired_sessions()
            
            # 获取或创建会话
            session = await self._get_or_create_session(session_id)
            
            # 添加用户消息到会话历史
            await self._add_message_to_session(session['session_id'], ChatMessage(role="user", content=message))
            
            # 获取会话上下文
            context = await self._get_session_context(session)
            
            # 生成回复 - 使用支持工具调用的流式方法并收集完整响应
            response_parts = []
            async for chunk in self.agent.answer_question_with_tools_stream(message, context=context):
                if hasattr(chunk, 'content'):
                    response_parts.append(chunk.content)
                else:
                    response_parts.append(str(chunk))
            response_text = ''.join(response_parts)
            
            # 添加AI回复到会话历史
            await self._add_message_to_session(session['session_id'], ChatMessage(role="assistant", content=response_text))
            
            # 获取参考来源（如果有的话）
            sources = getattr(self.agent, 'last_sources', [])
            
            return ChatResponse(
                response=response_text,
                session_id=session['session_id'],
                timestamp=datetime.now(),
                sources=sources,
                success=True
            )
            
        except Exception as e:
            self.logger.error(f"消息处理错误: {str(e)}")
            raise
    
    async def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        try:
            return await self.session_manager.delete_session(session_id)
            
        except Exception as e:
            self.logger.error(f"删除会话错误: {str(e)}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            status = {
                'status': 'healthy',
                'timestamp': datetime.now(),
                'services': {
                    'session_manager': 'healthy',
                    'document_manager': 'healthy' if self.document_manager else 'not_initialized',
                    'agent': 'healthy' if self.agent else 'not_initialized'
                }
            }
            
            return status
            
        except Exception as e:
            self.logger.error(f"健康检查错误: {str(e)}")
            return {
                'status': 'unhealthy',
                'timestamp': datetime.now(),
                'error': str(e)
            }

    async def chat_stream(self, request: ChatRequest) -> AsyncGenerator[StreamChatResponse, None]:
        """处理流式对话请求"""
        try:
            # 清理过期会话
            await self._cleanup_expired_sessions()
            
            # 获取或创建会话
            session = await self._get_or_create_session(request.session_id)
            
            # 处理消息输入
            if request.message:
                # 单条消息模式（向后兼容）
                user_message = request.message
                await self._add_message_to_session(session['session_id'], ChatMessage(role="user", content=user_message))
            elif request.messages:
                # 多轮对话模式
                # 将新的消息列表添加到会话历史
                for msg in request.messages:
                    await self._add_message_to_session(session['session_id'], ChatMessage(role=msg.role, content=msg.content))
                # 获取最后一条用户消息作为当前查询
                user_messages = [msg for msg in request.messages if msg.role == "user"]
                if not user_messages:
                    raise ValueError("消息列表中必须包含至少一条用户消息")
                user_message = user_messages[-1].content
            else:
                raise ValueError("必须提供 message 或 messages 参数")
            
            # 构建对话上下文（包含历史消息）
            context_messages = []
            # 获取最近的对话历史（限制数量避免上下文过长）
            recent_messages = session.get('messages', [])[-10:]  # 最近10条消息
            for msg in recent_messages[:-1]:  # 排除刚添加的当前消息
                context_messages.append(f"{msg['role']}: {msg['content']}")
            
            conversation_context = "\n".join(context_messages) if context_messages else None
            
            # 合并额外上下文
            full_context = request.context
            if conversation_context:
                if full_context:
                    full_context = f"{conversation_context}\n\n{full_context}"
                else:
                    full_context = conversation_context
            
            # 生成流式回复 - 使用支持工具调用的版本
            full_response = ""
            async for chunk in self.agent.answer_question_with_tools_stream(
                question=user_message,
                context=full_context
            ):
                full_response += chunk
                yield StreamChatResponse(
                    content=chunk,
                    session_id=session['session_id'],
                    finished=False
                )
            
            # 添加完整回复到会话历史
            await self._add_message_to_session(session['session_id'], ChatMessage(role="assistant", content=full_response))
            
            # 发送完成信号
            yield StreamChatResponse(
                content="",
                session_id=session['session_id'],
                finished=True
            )
            
        except Exception as e:
            self.logger.error(f"处理流式对话请求失败: {e}")
            yield StreamChatResponse(
                content=f"抱歉，处理您的请求时出现错误: {str(e)}",
                session_id=session['session_id'] if 'session' in locals() else "error",
                finished=True
            )
    

    
    async def _get_sources(self, query: str) -> Optional[list]:
        """获取回答的参考来源"""
        try:
            search_results = await self.doc_manager.search_documents(query, top_k=3)
            if search_results:
                return [
                    {
                        "source": result["source"],
                        "category": result["category"],
                        "score": result["score"]
                    }
                    for result in search_results
                ]
            return None
        except Exception as e:
            self.logger.error(f"获取参考来源失败: {e}")
            return None
    
    async def upload_document(self, request: DocumentUploadRequest, file_content: bytes = None) -> DocumentUploadResponse:
        """上传文档"""
        try:
            if request.content:
                # 直接上传文本内容
                doc_id = await self.agent.add_document(
                    request.content, request.filename, request.category
                )
            elif file_content:
                # 上传文件内容
                doc_id = await self.agent.add_document(
                    file_content, request.filename, request.category
                )
            else:
                raise ValueError("必须提供文件内容或文本内容")
            
            return DocumentUploadResponse(
                success=True,
                document_id=doc_id,
                filename=request.filename,
                category=request.category,
                status="success",
                message=f"成功上传文档: {request.filename}"
            )
            
        except Exception as e:
            self.logger.error(f"上传文档失败: {e}")
            return DocumentUploadResponse(
                success=False,
                document_id="",
                filename=request.filename,
                category=request.category,
                status="error",
                message=f"上传文档失败: {str(e)}"
            )
    
    async def search_documents(self, request: DocumentSearchRequest) -> DocumentSearchResponse:
        """搜索文档"""
        try:
            results = await self.doc_manager.search_documents(
                query=request.query,
                category=request.category,
                top_k=request.top_k
            )
            
            return DocumentSearchResponse(
                results=results,
                total=len(results),
                query=request.query
            )
            
        except Exception as e:
            self.logger.error(f"搜索文档失败: {e}")
            return DocumentSearchResponse(
                results=[],
                total=0,
                query=request.query
            )
    
    async def get_document_summary(self, document_type: Optional[str] = None) -> DocumentSummaryResponse:
        """获取文档摘要"""
        try:
            summary = await self.agent.get_document_summary()
            
            # 统计信息
            total_docs = len(self.doc_manager.document_metadata)
            total_chunks = len(self.doc_manager.chunks_data)
            
            # 按类别统计
            categories = {}
            for doc_info in self.doc_manager.document_metadata.values():
                category = doc_info.get('category', '其他')
                categories[category] = categories.get(category, 0) + 1
            
            return DocumentSummaryResponse(
                summary=summary,
                total_documents=total_docs,
                total_chunks=total_chunks,
                categories=categories
            )
            
        except Exception as e:
            self.logger.error(f"获取文档摘要失败: {e}")
            return DocumentSummaryResponse(
                summary="获取文档摘要失败",
                total_documents=0,
                total_chunks=0,
                categories={}
            )
    
    async def get_session_info(self, session_id: str) -> Optional[Dict]:
        """获取会话信息"""
        session = await self.session_manager.get_session(session_id)
        if session is None:
            return None
        
        return {
            "session_id": session['session_id'],
            "created_at": session['created_at'],
            "last_activity": session['last_accessed'],
            "message_count": len(session.get('messages', [])),
            "is_active": True
        }
    
    async def _add_message_to_session(self, session_id: str, message: ChatMessage):
        """添加消息到会话"""
        await self.session_manager.add_message(session_id, message)
    
    def _start_cleanup_task(self):
        """启动清理任务"""
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(300)  # 每5分钟清理一次
                    await self._cleanup_expired_sessions()
                except Exception as e:
                    self.logger.error(f"清理任务出错: {e}")
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())
    
    async def close(self):
        """关闭服务"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
        await self.agent.close()
        self.logger.info("对话服务已关闭")

# 全局服务实例
chat_service = None

def get_chat_service() -> ChatService:
    """获取对话服务实例"""
    global chat_service
    if chat_service is None:
        chat_service = ChatService()
    return chat_service