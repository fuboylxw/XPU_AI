"""
MCP客户端实现
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from src.config.settings import Settings
from src.utils.logger import setup_logger

class MCPClient:
    """MCP客户端"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = setup_logger(settings)
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.available_tools = []
    
    async def connect(self, server_command: List[str]):
        """连接到MCP服务器"""
        try:
            # 创建服务器参数
            server_params = StdioServerParameters(
                command=server_command[0],
                args=server_command[1:] if len(server_command) > 1 else [],
                env=None
            )
            
            # 建立stdio连接
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            stdio, write = stdio_transport
            
            # 创建客户端会话
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(stdio, write)
            )
            
            # 初始化会话
            await self.session.initialize()
            
            # 获取可用工具
            tools_result = await self.session.list_tools()
            self.available_tools = tools_result.tools
            
            self.logger.info(f"成功连接到MCP服务器，可用工具: {len(self.available_tools)}")
            return True
        except Exception as e:
            self.logger.error(f"连接MCP服务器失败: {e}")
            return False
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[str]:
        """调用MCP工具"""
        if not self.session:
            self.logger.error("MCP客户端未连接")
            return None
        
        try:
            result = await self.session.call_tool(tool_name, arguments)
            if result.content:
                return result.content[0].text if hasattr(result.content[0], 'text') else str(result.content[0])
            return None
        except Exception as e:
            self.logger.error(f"调用工具 {tool_name} 失败: {e}")
            return None
    
    async def search_school_info(self, query: str, category: Optional[str] = None) -> Optional[str]:
        """搜索学校信息"""
        arguments = {"query": query}
        if category:
            arguments["category"] = category
        
        return await self.call_tool("search_school_info", arguments)
    
    async def get_document_summary(self, document_type: Optional[str] = None) -> Optional[str]:
        """获取文档摘要"""
        arguments = {}
        if document_type:
            arguments["document_type"] = document_type
        
        return await self.call_tool("get_document_summary", arguments)
    
    async def add_school_document(self, content: str, title: str, category: str = "其他") -> Optional[str]:
        """添加学校文档"""
        arguments = {
            "content": content,
            "title": title,
            "category": category
        }
        
        return await self.call_tool("add_school_document", arguments)
    
    async def disconnect(self):
        """断开连接"""
        if self.session:
            await self.exit_stack.aclose()
            self.session = None
            self.logger.info("已断开MCP服务器连接")