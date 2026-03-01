"""
问题改写服务
从 ChatbotAgent 提取的问题改写相关方法
"""
import logging
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import LLMChain

logger = logging.getLogger(__name__)

REWRITE_PROMPT = """
你是一个问题改写助手。
你会收到用户的原始问题和对话上下文。
你的任务是：
    1. 在保持语义不变的前提下，将用户的问题改写为更清晰、简洁、完整的形式。
    2. 衔接上下文，补全必要的省略信息。
    3. 不要改变问题意图，不要加入额外解释或答案。
    4. 输出时只给出改写后的问题，不要包含其他多余文字。
    5. 保持问题的简洁性，不要添加不必要的前缀或修饰词。
    6. 保持问题的语言风格与用户原始问题一致（如中文或英文）。
    7. 只修改问题，不做回复
示例：
    输入：网信处处长是谁
    输出：西安工程大学网络与信息化管理处处长是谁
    输入：近期国家有什么大事
    输出：在近期我国（中国）有什么重大事件或新闻发生
# 输出格式
请直接输出最终改写后的问题，不要添加解释或标签等其他任何内容。
"""


class QuestionRewriteService:
    """问题改写服务"""

    def __init__(self, llm):
        self.llm = llm
        self.rewrite_prompt = REWRITE_PROMPT

    def rewrite_sync(self, question: str, chat_history: str = "") -> str:
        """问题改写 - 同步版本"""
        try:
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content=self.rewrite_prompt),
                HumanMessage(content=f"对话上下文：\n{chat_history}\n\n用户问题：{question}"),
            ])
            chain = LLMChain(llm=self.llm, prompt=prompt)
            response = chain.invoke({"question": question})
            if isinstance(response, dict) and "text" in response:
                response_text = response["text"]
            elif isinstance(response, str):
                response_text = response
            else:
                response_text = str(response)
            return response_text.strip()
        except Exception as e:
            logger.error(f"问题改写失败: {e}")
            return question

    async def rewrite(self, question: str, conversation_context: str = "") -> str:
        """异步方法：结合上下文对问题进行改写"""
        try:
            if not conversation_context:
                return question
            return self.rewrite_sync(question, conversation_context)
        except Exception as e:
            logger.error(f"问题改写失败: {e}")
            return question
