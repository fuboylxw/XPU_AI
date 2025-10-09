"""接口定义模块
定义服务层的抽象接口，降低组件间耦合度
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator
from .models import ChatMessage, ChatResponse, DocumentInfo, SearchResult


class IDocumentManager(ABC):
    """文档管理器接口"""
    

    
    @abstractmethod
    async def search_documents(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """搜索文档"""
        pass
    
    @abstractmethod
    async def get_document_info(self, document_id: str) -> Optional[DocumentInfo]:
        """获取文档信息"""
        pass
    
    @abstractmethod
    async def delete_document(self, document_id: str) -> bool:
        """删除文档"""
        pass
    
    @abstractmethod
    async def add_document(self, file_content, filename: str, category: str = "其他") -> str:
        """添加文档"""
        pass
    
    @abstractmethod
    async def get_document_summary(self) -> str:
        """获取文档摘要"""
        pass
    
    @abstractmethod
    async def close(self):
        """关闭文档管理器"""
        pass
    
    @abstractmethod
    async def load_data(self) -> bool:
        """加载数据"""
        pass
    
    @abstractmethod
    async def get_embedding_model_info(self) -> Dict[str, Any]:
        """获取嵌入模型信息"""
        pass
    
    @abstractmethod
    async def get_vector_store_info(self) -> Dict[str, Any]:
        """获取向量存储信息"""
        pass
    
    @abstractmethod
    async def extract_text_from_file(self, file_content, filename: str) -> str:
        """从文件中提取文本"""
        pass
    
    @abstractmethod
    async def chunk_text(self, text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
        """文本分块"""
        pass


class ILLMClient(ABC):
    """LLM客户端接口"""
    
    @abstractmethod
    async def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """聊天完成"""
        pass
    
    @abstractmethod
    async def chat_completion_stream(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        """流式聊天完成"""
        pass
    
    @abstractmethod
    async def chat_completion_with_tools(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """带工具的聊天完成"""
        pass
    
    @abstractmethod
    async def chat_completion_with_tools_stream(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]], **kwargs) -> AsyncGenerator[str, None]:
        """带工具的流式聊天完成"""
        pass
    
    @abstractmethod
    async def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        pass
    
    @abstractmethod
    async def close(self):
        """关闭客户端"""
        pass


class IWebSearchTool(ABC):
    """网络搜索工具接口"""
    
    @abstractmethod
    async def search(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """执行网络搜索"""
        pass


class IMCPClient(ABC):
    """MCP客户端接口"""
    
    @abstractmethod
    async def connect(self) -> bool:
        """连接MCP服务器"""
        pass
    
    @abstractmethod
    async def get_tools(self) -> List[Dict[str, Any]]:
        """获取可用工具"""
        pass
    
    @abstractmethod
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用工具"""
        pass


class ISchoolInfoAgent(ABC):
    """学校信息问答Agent接口"""
    

    
    @abstractmethod
    async def answer_question_with_tools_stream(self, question: str, context: Optional[str] = None, messages: Optional[List[Dict[str, str]]] = None) -> AsyncGenerator[str, None]:
        """使用工具流式回答问题 (推荐使用的唯一对话接口)"""
        pass
    
    @abstractmethod
    async def add_document(self, file_content, filename: str, category: str = "其他") -> str:
        """添加文档"""
        pass
    
    @abstractmethod
    async def get_document_summary(self) -> str:
        """获取文档摘要"""
        pass
    
    @abstractmethod
    async def close(self):
        """关闭Agent"""
        pass


class ISessionManager(ABC):
    """会话管理器接口"""
    
    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话"""
        pass
    
    @abstractmethod
    async def create_session(self, session_id: str) -> Dict[str, Any]:
        """创建会话"""
        pass
    
    @abstractmethod
    async def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """更新会话"""
        pass
    
    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        pass
    
    @abstractmethod
    async def cleanup_expired_sessions(self) -> int:
        """清理过期会话"""
        pass


class IChatService(ABC):
    """聊天服务接口"""
    
    @abstractmethod
    async def process_message(self, message: str, session_id: Optional[str] = None, **kwargs) -> ChatResponse:
        """处理消息"""
        pass
    

    
    @abstractmethod
    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息"""
        pass