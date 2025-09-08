"""
DeepSeek API客户端
"""

from typing import List, Dict, Any, Optional, AsyncGenerator
import httpx
import json
from src.config.settings import Settings
from src.utils.logger import setup_logger

class DeepSeekClient:
    """DeepSeek API客户端"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = setup_logger(settings)
        self.api_key = settings.deepseek_api_key
        self.api_base = settings.deepseek_api_base
        self.model = settings.model_name
        
        if not self.api_key:
            raise ValueError("DeepSeek API密钥未配置")
        
        self.client = httpx.AsyncClient(
            base_url=self.api_base,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = True
    ) -> Dict[str, Any]:
        """聊天完成API调用"""
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.settings.temperature,
            "max_tokens": max_tokens or self.settings.max_tokens,
            "stream": stream
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        # 使用新的客户端连接避免事件循环关闭问题
        async with httpx.AsyncClient(
            base_url=self.api_base,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        ) as client:
            try:
                response = await client.post("/chat/completions", json=payload)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                self.logger.error(f"DeepSeek API调用失败: {e}")
                raise
    
    async def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """流式聊天完成API调用"""
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.settings.temperature,
            "max_tokens": max_tokens or self.settings.max_tokens,
            "stream": True
        }
        
        # 使用新的客户端连接避免事件循环关闭问题
        async with httpx.AsyncClient(
            base_url=self.api_base,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        ) as client:
            try:
                async with client.stream(
                    "POST", "/chat/completions", 
                    json=payload
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        # 确保line是字符串类型
                        if isinstance(line, bytes):
                            line = line.decode('utf-8', errors='ignore')
                        
                        if line.startswith("data: "):
                            data = line[6:]  # 移除 "data: " 前缀
                            
                            if data == "[DONE]":
                                break
                            
                            try:
                                chunk = json.loads(data)
                                if "choices" in chunk and len(chunk["choices"]) > 0:
                                    delta = chunk["choices"][0].get("delta", {})
                                    if "content" in delta:
                                        content = delta["content"]
                                        # 确保内容是有效的字符串
                                        if isinstance(content, str) and content.strip():
                                            # 过滤工具调用标记符号
                                            if not self._contains_tool_markers(content):
                                                yield content
                            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                                self.logger.warning(f"解析流式数据失败: {e}")
                                continue
                                
            except httpx.HTTPError as e:
                self.logger.error(f"DeepSeek 流式API调用失败: {e}")
                raise
            except Exception as e:
                self.logger.error(f"流式处理异常: {e}")
                raise
    

    

    

    

    
    async def chat_completion_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """支持工具调用的聊天完成"""
        
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "temperature": temperature or self.settings.temperature,
            "max_tokens": max_tokens or self.settings.max_tokens
        }
        
        # 记录工具调用请求
        self.logger.info(f"发起工具调用请求，包含 {len(tools)} 个工具")
        
        # 使用新的客户端连接避免事件循环关闭问题
        async with httpx.AsyncClient(
            base_url=self.api_base,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        ) as client:
            try:
                response = await client.post("/chat/completions", json=payload)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                self.logger.error(f"工具调用API失败: {e}")
                # 打印响应内容以便调试
                if hasattr(e, 'response') and e.response:
                    self.logger.error(f"响应状态码: {e.response.status_code}")
                    self.logger.error(f"响应内容: {e.response.text}")
                raise 
    

    
    def _contains_tool_markers(self, content: str) -> bool:
        """检查内容是否包含工具调用标记符号"""
        # 只检查明确的工具调用标记符号，避免误判正常文本
        tool_markers = [
            # DeepSeek工具调用标记符号
            "<｜tool▁calls▁begin｜>",
            "<｜tool▁calls▁end｜>", 
            "<｜tool▁call▁begin｜>",
            "<｜tool▁call▁end｜>",
            "<｜tool▁sep｜>",
            # 其他明确的工具调用标记
            "<|tool",
            "|tool>"
        ]
        
        # 检查是否包含明确的工具调用标记
        content_lower = content.lower()
        for marker in tool_markers:
            if marker.lower() in content_lower:
                return True
                
        # 检查是否包含完整的JSON格式工具调用（更严格的匹配）
        import re
        # 只匹配真正的工具调用JSON格式，必须是完整的结构
        tool_call_patterns = [
            # 匹配完整的工具调用结构，必须包含function和name字段，且name是已知的工具
            r'"function"\s*:\s*\{\s*"name"\s*:\s*"(search_web|get_time_info|calculate)"\s*,\s*"arguments"',
            # 匹配tool_calls数组结构，必须包含完整的工具调用
            r'"tool_calls"\s*:\s*\[\s*\{\s*"id".*?"function"\s*:\s*\{\s*"name"\s*:\s*"(search_web|get_time_info|calculate)"',
            # 匹配简化的工具调用格式，如 search_web["query":"...","max_results":3]
            r'(search_web|get_time_info|calculate)\s*\[\s*"[^"]+"\s*:\s*"[^"]*"',
            # 匹配工具调用开始标记
            r'^\s*(search_web|get_time_info|calculate)\s*\['
        ]
        
        for pattern in tool_call_patterns:
            if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                return True
            
        return False
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()