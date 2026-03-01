"""
回答生成服务
从 ChatbotAgent 提取的回答生成相关方法
"""
import logging
import asyncio
from typing import Dict, Any, List, AsyncGenerator, Optional

from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.chains import LLMChain

logger = logging.getLogger(__name__)


class AnswerGenerationService:
    """回答生成服务"""

    def __init__(self, llm, llm_stream, prompts: Dict[str, str]):
        self.llm = llm
        self.llm_stream = llm_stream
        self.school_answer_prompt = prompts.get("school_answer_prompt", "")
        self.web_answer_prompt = prompts.get("web_answer_prompt", "")
        self.no_web_answer_prompt = prompts.get("no_web_answer_prompt", "")
        self.data_query_prompt = prompts.get("data_query_prompt", "")
        self.phone_prompt = prompts.get("phone_prompt", "")

    async def generate_streaming_response(self, messages: List[BaseMessage]) -> AsyncGenerator[str, None]:
        """生成流式响应"""
        response = await self.llm_stream.agenerate([messages])
        for chunk in response.generations[0][0].text:
            yield chunk
            await asyncio.sleep(0.01)

    async def generate_final_answer(
        self,
        search_results: str,
        intent_description: str,
        rewritten_question: str,
        is_school_related: bool,
    ) -> AsyncGenerator[str, None]:
        """生成最终回答（流式）"""
        try:
            if is_school_related:
                system_prompt = self.school_answer_prompt
                user_prompt = f"""
                改写后的用户问题：{rewritten_question}
                意图分析: {intent_description}
                知识库检索结果: {search_results}
                """
            else:
                system_prompt = self.web_answer_prompt
                user_prompt = f"""
                改写后的用户问题：{rewritten_question}
                意图分析: {intent_description}
                网络搜索结果: {search_results}
                """

            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ])
            chain = LLMChain(llm=self.llm_stream, prompt=prompt)

            previous_text = ""
            async for chunk in chain.astream({
                "rewritten_question": rewritten_question,
                "Intent_description": intent_description,
                "search_results": search_results,
            }):
                if chunk["event"] == "on_llm_new_token":
                    current_text = chunk["data"]
                    new_text = current_text[len(previous_text):]
                    if new_text:
                        yield new_text
                    previous_text = current_text

        except Exception as e:
            logger.error(f"生成最终回答时出错: {e}")
            yield f"抱歉，处理您的请求时出现错误: {str(e)}"

    async def generate_with_langchain(
        self,
        question: str,
        intent: str,
        query_result: Any,
        phone_mode: bool = False,
        phone_conversation_history: List[Dict[str, Any]] = None,
        conversation_context: str = "",
    ) -> str:
        """使用LangChain调用大模型生成最终回答"""
        try:
            context = ""
            if phone_conversation_history:
                context_parts = []
                for conv in phone_conversation_history[-5:]:
                    if conv.get("question"):
                        context_parts.append(f"用户：{conv['question']}")
                    if conv.get("answer"):
                        context_parts.append(f"助手：{conv['answer']}")
                context = "\n".join(context_parts)
            if conversation_context:
                context = (conversation_context + "\n" + context) if context else conversation_context

            content_parts = [
                f"上下文对话: {context}",
                f"当前问题: {question}",
                f"意图分析: {intent}",
                f"查询结果: {query_result}",
            ]

            prompt_template = ChatPromptTemplate.from_messages([
                SystemMessage(content=self.phone_prompt if phone_mode else self.no_web_answer_prompt),
                HumanMessage(content="\n".join(content_parts)),
            ])

            chain = prompt_template | self.llm | StrOutputParser()
            return await chain.ainvoke({})

        except Exception as e:
            logger.error(f"大模型生成回答失败: {e}")
            return f"抱歉，我无法处理您的问题。请稍后再试。错误信息：{str(e)}"

    async def synthesize_optimized(
        self,
        question: str,
        intent_result: Dict[str, Any],
        processing_result: Dict[str, Any],
        security_result: Dict[str, Any],
        phone_mode: bool = False,
        max_response_length: int = 200,
    ) -> str:
        """优化的最终回答生成"""
        try:
            result_type = processing_result.get("type", "unknown")
            result_data = processing_result.get("result", {})

            if result_type == "knowledge_query":
                answer = result_data.get("answer", "")
                if answer and answer != "无结果":
                    if phone_mode and len(answer) > max_response_length:
                        answer = answer[:max_response_length] + "..."
                    return answer
                else:
                    return "抱歉，我没有找到相关信息。" + (
                        "请联系相关部门。" if phone_mode else "您可以尝试换个方式提问，或者联系相关部门获取帮助。"
                    )
            elif result_type == "data_query":
                if result_data.get("success", False):
                    answer = result_data.get("answer", "数据查询完成。")
                    if phone_mode and len(answer) > max_response_length:
                        answer = answer[:max_response_length] + "..."
                    return answer
                else:
                    error_msg = result_data.get("error", "数据查询失败")
                    suggestion = result_data.get("suggestion", "")
                    return f"{error_msg}。{suggestion}" if suggestion else error_msg
            elif result_type == "general_answer":
                answer = result_data.get("answer", "抱歉，我无法回答这个问题。")
                if phone_mode and len(answer) > max_response_length:
                    answer = answer[:max_response_length] + "..."
                return answer
            else:
                return "抱歉，我无法理解您的问题。" if phone_mode else "抱歉，我无法理解您的问题，请尝试重新表述。"

        except Exception as e:
            logger.error(f"优化最终回答生成失败: {e}")
            return "抱歉，系统暂时繁忙，请稍后重试。"

    @staticmethod
    def format_hybrid_results(hybrid_results) -> str:
        """格式化混合检索结果"""
        if not hybrid_results:
            return "未找到相关信息"

        formatted_parts = []
        for i, result in enumerate(hybrid_results, 1):
            if isinstance(result, dict):
                content = result.get("content", result.get("text", ""))
                source = result.get("source", result.get("metadata", {}).get("source", "未知来源"))
                score = result.get("score", 0.0)
                formatted_parts.append(f"[{i}] (相关度: {score:.2f}) {content}\n来源: {source}")
            elif isinstance(result, str):
                formatted_parts.append(f"[{i}] {result}")
            else:
                formatted_parts.append(f"[{i}] {str(result)}")

        return "\n\n".join(formatted_parts)
