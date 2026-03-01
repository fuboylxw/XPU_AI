"""
LLMClient - 大模型调用客户端
提供正常输出和流式输出两种调用方式
"""

from typing import List, Dict, Any, Optional, AsyncGenerator, Union
import asyncio
import logging
import os
from config.settings import settings
from langchain_core.messages import BaseMessage

# 配置日志
logger = logging.getLogger(__name__)


class LLMClient:
    """大模型调用客户端，支持正常输出和流式输出"""

    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        base_url: str = None,
        temperature: float = None,
        max_tokens: int = None,
    ):
        """
        初始化LLM客户端

        Args:
            api_key: API密钥
            model: 模型名称
            base_url: API基础URL
            temperature: 温度参数
            max_tokens: 最大token数
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL
        self.base_url = base_url or settings.OPENAI_MODEL_BASE_URL
        self.temperature = temperature if temperature is not None else settings.OPENAI_TEMPERATURE
        self.max_tokens = max_tokens or settings.OPENAI_MAX_TOKENS

        # 初始化LLM
        # self.llm = ChatOpenAI(
        #     api_key=self.api_key,
        #     model=self.model,
        #     base_url=self.base_url,
        #     temperature=self.temperature,
        #     max_tokens=self.max_tokens
        # )

    def update_config(
        self, model: str = None, temperature: float = None, max_tokens: int = None
    ):
        """
        更新LLM配置

        Args:
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
        """
        if model:
            self.model = model
        if temperature is not None:
            self.temperature = temperature
        if max_tokens:
            self.max_tokens = max_tokens

    def invoke(self, messages: List[BaseMessage]) -> str:
        """
        同步调用LLM

        Args:
            messages: 消息列表

        Returns:
            LLM回复内容
        """
        try:
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            return f"抱歉，调用大模型时出现错误: {str(e)}"

    def invoke_with_prompt(self, prompt_template: str, **kwargs) -> str:
        """
        使用提示词模板同步调用LLM

        Args:
            prompt_template: 提示词模板
            **kwargs: 模板变量

        Returns:
            LLM回复内容
        """
        try:
            prompt = PromptTemplate.from_template(prompt_template)
            formatted_prompt = prompt.format(**kwargs)
            messages = [HumanMessage(content=formatted_prompt)]
            return self.invoke(messages)
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            return f"抱歉，调用大模型时出现错误: {str(e)}"

    def invoke_with_system(self, system_prompt: str, user_prompt: str) -> str:
        """
        使用系统提示词和用户提示词同步调用LLM

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词

        Returns:
            LLM回复内容
        """
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
            return self.invoke(messages)
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            return f"抱歉，调用大模型时出现错误: {str(e)}"

    async def ainvoke(self, messages: List[BaseMessage]) -> str:
        """
        异步调用LLM

        Args:
            messages: 消息列表

        Returns:
            LLM回复内容
        """
        try:
            response = await self.llm.ainvoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"LLM异步调用失败: {e}")
            return f"抱歉，调用大模型时出现错误: {str(e)}"

    async def ainvoke_with_prompt(self, prompt_template: str, **kwargs) -> str:
        """
        使用提示词模板异步调用LLM

        Args:
            prompt_template: 提示词模板
            **kwargs: 模板变量

        Returns:
            LLM回复内容
        """
        try:
            prompt = PromptTemplate.from_template(prompt_template)
            formatted_prompt = prompt.format(**kwargs)
            messages = [HumanMessage(content=formatted_prompt)]
            return await self.ainvoke(messages)
        except Exception as e:
            logger.error(f"LLM异步调用失败: {e}")
            return f"抱歉，调用大模型时出现错误: {str(e)}"

    async def ainvoke_with_system(self, system_prompt: str, user_prompt: str) -> str:
        """
        使用系统提示词和用户提示词异步调用LLM

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词

        Returns:
            LLM回复内容
        """
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
            return await self.ainvoke(messages)
        except Exception as e:
            logger.error(f"LLM异步调用失败: {e}")
            return f"抱歉，调用大模型时出现错误: {str(e)}"

    async def astream(self, messages: List[BaseMessage]) -> AsyncGenerator[str, None]:
        """
        流式异步调用LLM

        Args:
            messages: 消息列表

        Yields:
            LLM回复内容片段
        """
        try:
            async for chunk in self.llm.astream(messages):
                if hasattr(chunk, "content") and chunk.content:
                    yield chunk.content
        except Exception as e:
            logger.error(f"LLM流式调用失败: {e}")
            yield f"抱歉，调用大模型时出现错误: {str(e)}"

    async def astream_with_prompt(
        self, prompt_template: str, **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        使用提示词模板流式异步调用LLM

        Args:
            prompt_template: 提示词模板
            **kwargs: 模板变量

        Yields:
            LLM回复内容片段
        """
        try:
            prompt = PromptTemplate.from_template(prompt_template)
            formatted_prompt = prompt.format(**kwargs)
            messages = [HumanMessage(content=formatted_prompt)]
            async for chunk in self.astream(messages):
                yield chunk
        except Exception as e:
            logger.error(f"LLM流式调用失败: {e}")
            yield f"抱歉，调用大模型时出现错误: {str(e)}"

    async def astream_with_system(
        self, system_prompt: str, user_prompt: str
    ) -> AsyncGenerator[str, None]:
        """
        使用系统提示词和用户提示词流式异步调用LLM

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词

        Yields:
            LLM回复内容片段
        """
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
            async for chunk in self.astream(messages):
                yield chunk
        except Exception as e:
            logger.error(f"LLM流式调用失败: {e}")
            yield f"抱歉，调用大模型时出现错误: {str(e)}"
