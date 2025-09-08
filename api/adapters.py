"""适配器模块
封装src目录下的组件，实现标准化接口
"""

import asyncio
from typing import Dict, Optional, AsyncGenerator, Any, List
from pathlib import Path
import sys

# 添加src目录到Python路径
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from src.agent.school_info_agent import SchoolInfoAgent
from src.rag.document_manager import DocumentManager
from src.llm.deepseek_client import DeepSeekClient
from src.config.settings import get_settings
from .interfaces import ISchoolInfoAgent, IDocumentManager, ILLMClient


class SchoolInfoAgentAdapter(ISchoolInfoAgent):
    """SchoolInfoAgent适配器
    
    将src目录下的SchoolInfoAgent封装为标准接口
    """
    
    def __init__(self, document_manager: IDocumentManager = None):
        self.settings = get_settings()
        self._agent = None
        self._document_manager = document_manager
        self._initialized = False
    
    async def _ensure_initialized(self):
        """确保Agent已初始化"""
        if not self._initialized:
            if self._document_manager is None:
                # 创建DocumentManager适配器实例
                self._document_manager = DocumentManagerAdapter()
                await self._document_manager._ensure_initialized()
            
            # 获取原始DocumentManager实例
            if hasattr(self._document_manager, '_document_manager'):
                doc_manager = self._document_manager._document_manager
            else:
                doc_manager = self._document_manager
            
            self._agent = SchoolInfoAgent(self.settings, doc_manager)
            self._initialized = True
    

    

    
    async def answer_question_with_tools_stream(self, question: str, context: Optional[str] = None, messages: Optional[List[Dict[str, str]]] = None) -> AsyncGenerator[str, None]:
        """使用工具流式回答问题"""
        await self._ensure_initialized()
        
        # 构建消息列表
        if messages is None:
            messages = []
        
        if context:
            messages.append({"role": "system", "content": context})
        
        messages.append({"role": "user", "content": question})
        
        # 使用原始Agent的带工具流式方法
        async for chunk in self._agent.answer_question_with_tools_stream(question, context, messages):
            yield chunk
    
    async def add_document(self, file_content, filename: str, category: str = "其他") -> str:
        """添加文档"""
        await self._ensure_initialized()
        
        if self._document_manager:
            return await self._document_manager.add_document(file_content, filename, category)
        else:
            raise RuntimeError("Document manager not available")
    
    async def get_document_summary(self) -> str:
        """获取文档摘要"""
        await self._ensure_initialized()
        
        if self._document_manager:
            return await self._document_manager.get_document_summary()
        else:
            return "文档管理器不可用"
    
    async def close(self):
        """关闭Agent"""
        if self._agent and hasattr(self._agent, 'close'):
            await self._agent.close()
        if self._document_manager:
            await self._document_manager.close()
        self._initialized = False


class DocumentManagerAdapter(IDocumentManager):
    """DocumentManager适配器
    
    将src目录下的DocumentManager封装为标准接口
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._document_manager = None
        self._initialized = False
    
    async def _ensure_initialized(self):
        """确保DocumentManager已初始化"""
        if not self._initialized:
            self._document_manager = DocumentManager(self.settings)
            await self.load_data()
            self._initialized = True
    
    async def add_document(self, file_content, filename: str, category: str = "其他") -> str:
        """添加文档"""
        await self._ensure_initialized()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._document_manager.add_document, file_content, filename, category)
    
    async def search_documents(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索文档"""
        await self._ensure_initialized()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._document_manager.search_documents, query, top_k)
    
    async def get_document_summary(self) -> str:
        """获取文档摘要"""
        await self._ensure_initialized()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._document_manager.get_document_summary)
    
    async def close(self):
        """关闭文档管理器"""
        if self._document_manager and hasattr(self._document_manager, 'close'):
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._document_manager.close)
        self._initialized = False
    
    async def load_data(self) -> bool:
        """加载数据"""
        if self._document_manager is None:
            self._document_manager = DocumentManager(self.settings)
        
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, self._document_manager.load_data)
            return True
        except Exception as e:
            print(f"加载数据失败: {e}")
            return False
    
    async def get_embedding_model_info(self) -> Dict[str, Any]:
        """获取嵌入模型信息"""
        await self._ensure_initialized()
        return {
            "model_name": getattr(self._document_manager, 'embedding_model_name', 'unknown'),
            "model_type": "sentence-transformers",
            "status": "loaded" if self._document_manager.embedding_model else "not_loaded"
        }
    
    async def get_vector_store_info(self) -> Dict[str, Any]:
        """获取向量存储信息"""
        await self._ensure_initialized()
        return {
            "store_type": "chroma",
            "collection_name": getattr(self._document_manager, 'collection_name', 'unknown'),
            "document_count": len(getattr(self._document_manager, 'documents', [])),
            "status": "ready" if self._document_manager.vector_store else "not_ready"
        }
    
    async def extract_text_from_file(self, file_content, filename: str) -> str:
        """从文件中提取文本"""
        await self._ensure_initialized()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._document_manager.extract_text_from_file, file_content, filename)
    
    async def chunk_text(self, text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
        """文本分块"""
        await self._ensure_initialized()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._document_manager.chunk_text, text, chunk_size, chunk_overlap)
    
    async def delete_document(self, document_id: str) -> bool:
        """删除文档"""
        await self._ensure_initialized()
        # 如果原始DocumentManager有删除方法，调用它
        if hasattr(self._document_manager, 'delete_document'):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._document_manager.delete_document, document_id)
        else:
            # 默认实现
            return False
    
    async def get_document_info(self, document_id: str) -> Optional[Dict[str, Any]]:
        """获取文档信息"""
        await self._ensure_initialized()
        # 如果原始DocumentManager有获取文档信息方法，调用它
        if hasattr(self._document_manager, 'get_document_info'):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._document_manager.get_document_info, document_id)
        else:
            # 默认实现
            return None
    



class DeepSeekClientAdapter(ILLMClient):
    """DeepSeekClient适配器
    
    将src目录下的DeepSeekClient封装为标准接口
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._client = None
        self._initialized = False
    
    async def _ensure_initialized(self):
        """确保客户端已初始化"""
        if not self._initialized:
            self._client = DeepSeekClient(self.settings)
            self._initialized = True
    
    async def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """聊天完成"""
        await self._ensure_initialized()
        return await self._client.chat_completion(messages, **kwargs)
    
    async def chat_completion_stream(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        """流式聊天完成"""
        await self._ensure_initialized()
        async for chunk in self._client.chat_completion_stream(messages, **kwargs):
            yield chunk
    
    async def chat_completion_with_tools(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """带工具的聊天完成"""
        await self._ensure_initialized()
        return await self._client.chat_completion_with_tools(messages, tools, **kwargs)
    
    async def chat_completion_with_tools_stream(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]], **kwargs) -> AsyncGenerator[str, None]:
        """带工具的流式聊天完成"""
        await self._ensure_initialized()
        async for chunk in self._client.chat_completion_with_tools_stream(messages, tools, **kwargs):
            yield chunk
    
    async def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        await self._ensure_initialized()
        return {
            "model_name": getattr(self._client, 'model', 'deepseek-chat'),
            "api_base": getattr(self._client, 'api_base', 'https://api.deepseek.com'),
            "status": "ready" if self._client else "not_ready"
        }
    
    async def close(self):
        """关闭客户端"""
        if self._client and hasattr(self._client, 'close'):
            await self._client.close()
        self._initialized = False