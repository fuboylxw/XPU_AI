"""服务工厂模式，统一管理依赖注入"""

import asyncio
from typing import Optional, Dict, Any
from functools import lru_cache

from .interfaces import (
    IChatService, ISessionManager, IDocumentManager, 
    ILLMClient, IWebSearchTool, IMCPClient, ISchoolInfoAgent
)
from .chat_service import ChatService
from .session_manager import InMemorySessionManager
from .config import get_settings as get_api_settings
from src.config.settings import get_settings
from .adapters import SchoolInfoAgentAdapter, DocumentManagerAdapter, DeepSeekClientAdapter
from src.utils.web_search import WebSearchTool
from src.mcp.client import MCPClient


class ServiceFactory:
    """服务工厂类，负责创建和管理所有服务实例"""
    
    def __init__(self):
        self._instances: Dict[str, Any] = {}
        self._settings = None
        self._api_settings = None
        self._initialized = False
    
    async def initialize(self):
        """初始化工厂"""
        if self._initialized:
            return
        
        self._settings = get_settings()
        self._api_settings = get_api_settings()
        self._initialized = True
    
    @property
    def settings(self):
        """获取主配置"""
        if not self._settings:
            self._settings = get_settings()
        return self._settings
    
    @property
    def api_settings(self):
        """获取API配置"""
        if not self._api_settings:
            self._api_settings = get_api_settings()
        return self._api_settings
    
    def get_session_manager(self, manager_type: str = "memory") -> ISessionManager:
        """获取会话管理器实例"""
        cache_key = f"session_manager_{manager_type}"
        
        if cache_key not in self._instances:
            if manager_type == "memory":
                self._instances[cache_key] = InMemorySessionManager(
                    session_timeout=self.api_settings.session_timeout
                )
            elif manager_type == "redis":
                # TODO: 实现Redis会话管理器
                raise NotImplementedError("Redis会话管理器尚未实现")
            else:
                raise ValueError(f"不支持的会话管理器类型: {manager_type}")
        
        return self._instances[cache_key]
    
    def get_document_manager(self) -> IDocumentManager:
        """获取文档管理器实例"""
        cache_key = "document_manager"
        
        if cache_key not in self._instances:
            self._instances[cache_key] = DocumentManagerAdapter()
        
        return self._instances[cache_key]
    
    def get_llm_client(self, client_type: str = "deepseek") -> ILLMClient:
        """获取LLM客户端实例"""
        cache_key = f"llm_client_{client_type}"
        
        if cache_key not in self._instances:
            if client_type == "deepseek":
                self._instances[cache_key] = DeepSeekClientAdapter()
            else:
                raise ValueError(f"不支持的LLM客户端类型: {client_type}")
        
        return self._instances[cache_key]
    
    async def get_school_info_agent(self) -> ISchoolInfoAgent:
        """获取学校信息Agent实例"""
        cache_key = "school_info_agent"
        
        if cache_key not in self._instances:
            document_manager = self.get_document_manager()
            self._instances[cache_key] = SchoolInfoAgentAdapter(document_manager)
        
        return self._instances[cache_key]
    
    def get_web_search_tool(self) -> IWebSearchTool:
        """获取网络搜索工具实例"""
        cache_key = "web_search_tool"
        
        if cache_key not in self._instances:
            self._instances[cache_key] = WebSearchTool()
        
        return self._instances[cache_key]
    
    def get_mcp_client(self) -> IMCPClient:
        """获取MCP客户端实例"""
        cache_key = "mcp_client"
        
        if cache_key not in self._instances:
            self._instances[cache_key] = MCPClient(
                server_path=self.settings.mcp_server_path,
                server_args=self.settings.mcp_server_args
            )
        
        return self._instances[cache_key]
    
    async def get_chat_service(
        self,
        session_manager_type: str = "memory",
        llm_client_type: str = "deepseek"
    ) -> IChatService:
        """获取聊天服务实例"""
        cache_key = f"chat_service_{session_manager_type}_{llm_client_type}"
        
        if cache_key not in self._instances:
            # 确保工厂已初始化
            await self.initialize()
            
            # 获取依赖服务
            session_manager = self.get_session_manager(session_manager_type)
            document_manager = self.get_document_manager()
            llm_client = self.get_llm_client(llm_client_type)
            school_info_agent = await self.get_school_info_agent()
            
            # 创建聊天服务
            chat_service = ChatService(
                session_manager=session_manager,
                document_manager=document_manager,
                llm_client=llm_client,
                school_info_agent=school_info_agent
            )
            
            # 初始化服务
            await chat_service.initialize()
            
            self._instances[cache_key] = chat_service
        
        return self._instances[cache_key]
    
    async def cleanup(self):
        """清理所有服务实例"""
        cleanup_tasks = []
        
        for instance in self._instances.values():
            if hasattr(instance, 'cleanup'):
                cleanup_tasks.append(instance.cleanup())
            elif hasattr(instance, 'close'):
                cleanup_tasks.append(instance.close())
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        self._instances.clear()
        self._initialized = False
    
    def reset_instance(self, service_type: str):
        """重置特定服务实例"""
        keys_to_remove = [key for key in self._instances.keys() if key.startswith(service_type)]
        for key in keys_to_remove:
            instance = self._instances.pop(key, None)
            if instance and hasattr(instance, 'cleanup'):
                asyncio.create_task(instance.cleanup())
    
    def get_service_status(self) -> Dict[str, Any]:
        """获取所有服务状态"""
        return {
            "initialized": self._initialized,
            "active_services": list(self._instances.keys()),
            "service_count": len(self._instances)
        }


# 全局服务工厂实例
_service_factory: Optional[ServiceFactory] = None


@lru_cache(maxsize=1)
def get_service_factory() -> ServiceFactory:
    """获取全局服务工厂实例"""
    global _service_factory
    if _service_factory is None:
        _service_factory = ServiceFactory()
    return _service_factory


async def initialize_services():
    """初始化所有服务"""
    factory = get_service_factory()
    await factory.initialize()


async def cleanup_services():
    """清理所有服务"""
    global _service_factory
    if _service_factory:
        await _service_factory.cleanup()
        _service_factory = None


# 便捷函数
async def get_chat_service(
    session_manager_type: str = "memory",
    llm_client_type: str = "deepseek"
) -> IChatService:
    """获取聊天服务实例的便捷函数"""
    factory = get_service_factory()
    return await factory.get_chat_service(session_manager_type, llm_client_type)


def get_session_manager(manager_type: str = "memory") -> ISessionManager:
    """获取会话管理器实例的便捷函数"""
    factory = get_service_factory()
    return factory.get_session_manager(manager_type)


def get_document_manager() -> IDocumentManager:
    """获取文档管理器实例的便捷函数"""
    factory = get_service_factory()
    return factory.get_document_manager()