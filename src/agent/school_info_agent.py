"""
学校信息问答Agent
集成MCP、DeepSeek和RAG功能
"""

import asyncio
from typing import List, Dict, Any, Optional
from src.config.settings import Settings
from src.llm.deepseek_client import DeepSeekClient
from src.rag.document_manager import DocumentManager
from src.mcp.client import MCPClient
from src.utils.logger import setup_logger

class SchoolInfoAgent:
    """学校信息问答Agent"""
    
    def __init__(self, settings: Settings, doc_manager: DocumentManager = None):
        self.settings = settings
        self.logger = setup_logger(settings)
        
        # 初始化组件
        self.llm_client = DeepSeekClient(settings)
        self.doc_manager = doc_manager or DocumentManager(settings)
        self.mcp_client = MCPClient(settings)
        
        # 系统提示词
        self.system_prompt = """
你是一个专业的学校信息助手，专门为新生解答关于学校的各种问题。

你的职责包括：
1. 回答关于学校专业、课程、设施、政策等方面的问题
2. 提供准确、有用、友好的信息
3. 当信息不足时，建议用户上传相关文档或联系相关部门
4. 保持专业和耐心的态度

回答时请注意：
- 基于提供的上下文信息给出准确回答
- 如果信息不确定，请明确说明
- 提供具体、可操作的建议
- 使用友好、易懂的语言
"""
    
    async def answer_question(self, question: str, context: Optional[str] = None) -> str:
        """回答问题"""
        try:
            # 如果没有提供上下文，则通过RAG检索
            if not context:
                context = await self._retrieve_context(question)
            
            # 使用DeepSeek生成回答
            response = await self.llm_client.generate_response(
                prompt=question,
                context=context,
                system_message=self.system_prompt
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"回答问题失败: {e}")
            return "抱歉，我现在无法回答您的问题，请稍后再试。"
    
    async def answer_question_stream(self, question: str, context: Optional[str] = None):
        """流式回答问题"""
        try:
            # 如果没有提供上下文，则通过RAG检索
            if not context:
                context = await self._retrieve_context(question)
            
            # 使用DeepSeek生成流式回答
            async for chunk in self.llm_client.generate_response_stream(
                prompt=question,
                context=context,
                system_message=self.system_prompt
            ):
                yield chunk
                
        except Exception as e:
            self.logger.error(f"流式回答问题失败: {e}")
            yield "抱歉，我现在无法回答您的问题，请稍后再试。"
    
    async def _retrieve_context(self, question: str) -> str:
        """检索相关上下文"""
        try:
            # 使用RAG检索相关文档
            search_results = await self.doc_manager.search_documents(question)
            
            if not search_results:
                return "暂无相关信息，建议上传相关文档或联系学校相关部门。"
            
            # 构建上下文
            context = "相关信息：\n\n"
            for i, result in enumerate(search_results[:3], 1):  # 只使用前3个结果
                context += f"{i}. {result['content']}\n"
                context += f"   来源: {result['source']}\n\n"
            
            return context
            
        except Exception as e:
            self.logger.error(f"检索上下文失败: {e}")
            return "检索信息时出现错误。"
    
    async def add_document(self, file_content, filename: str, category: str = "其他") -> str:
        """添加文档"""
        try:
            doc_id = await self.doc_manager.add_document(file_content, filename, category)
            return f"成功添加文档: {filename}"
        except Exception as e:
            self.logger.error(f"添加文档失败: {e}")
            return f"添加文档失败: {str(e)}"
    
    async def get_document_summary(self) -> str:
        """获取文档摘要"""
        return await self.doc_manager.get_documents_summary()
    
    async def close(self):
        """关闭Agent"""
        await self.llm_client.close()
        await self.mcp_client.disconnect()