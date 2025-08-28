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
        stream: bool = False
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
        
        try:
            response = await self.client.post("/chat/completions", json=payload)
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
        
        try:
            async with self.client.stream(
                "POST", "/chat/completions", 
                json=payload
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # 移除 "data: " 前缀
                        
                        if data == "[DONE]":
                            break
                        
                        try:
                            chunk = json.loads(data)
                            if "choices" in chunk and len(chunk["choices"]) > 0:
                                delta = chunk["choices"][0].get("delta", {})
                                if "content" in delta:
                                    yield delta["content"]
                        except json.JSONDecodeError:
                            continue
                            
        except httpx.HTTPError as e:
            self.logger.error(f"DeepSeek 流式API调用失败: {e}")
            raise
    
    async def generate_response(
        self,
        prompt: str,
        context: Optional[str] = None,
        system_message: Optional[str] = None
    ) -> str:
        """生成回复"""
        
        messages = []
        
        # 系统消息
        if system_message:
            messages.append({"role": "system", "content": system_message})
        else:
            messages.append({
                "role": "system",
                "content": "你是一个专业的学校信息助手，专门为新生解答关于学校的各种问题。请基于提供的上下文信息给出准确、有用的回答。"
            })
        
        # 上下文信息
        if context:
            messages.append({
                "role": "user",
                "content": f"参考信息：\n{context}\n\n问题：{prompt}"
            })
        else:
            messages.append({"role": "user", "content": prompt})
        
        try:
            response = await self.chat_completion(messages)
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            self.logger.error(f"生成回复失败: {e}")
            return "抱歉，我现在无法回答您的问题，请稍后再试。"
    
    async def generate_response_stream(
        self,
        prompt: str,
        context: Optional[str] = None,
        system_message: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """生成流式回复"""
        
        messages = []
        
        # 系统消息
        if system_message:
            messages.append({"role": "system", "content": system_message})
        else:
            messages.append({
                "role": "system",
                "content": "你是一个专业的学校信息助手，专门为新生解答关于学校的各种问题。请基于提供的上下文信息给出准确、有用的回答。"
            })
        
        # 上下文信息
        if context:
            messages.append({
                "role": "user",
                "content": f"参考信息：\n{context}\n\n问题：{prompt}"
            })
        else:
            messages.append({"role": "user", "content": prompt})
        
        try:
            async for chunk in self.chat_completion_stream(messages):
                yield chunk
        except Exception as e:
            self.logger.error(f"生成流式回复失败: {e}")
            yield "抱歉，我现在无法回答您的问题，请稍后再试。"
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()