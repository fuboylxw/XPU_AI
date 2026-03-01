"""
意图识别服务
从 ChatbotAgent 提取的意图识别相关方法
"""
import logging
import hashlib
import json
import time
import asyncio
from typing import Dict, Any, Optional, Union

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain.chains import LLMChain

logger = logging.getLogger(__name__)

INTENT_PROMPT = """
你是一个意图识别助手。
你会收到一个用户问题。你的任务是：
1. 判断该问题是否与西安工程大学相关（如校规校纪、奖学金、课程安排、学籍管理、校园生活、招生就业等）。
2. 如果是学校相关问题，识别具体意图类别，例如：
    - "Scholarship" (奖学金 / 助学金 / 评优评奖)
    - "Policy" (校规校纪 / 管理办法 / 文件制度)
    - "MajorInfo" (学院 / 专业介绍)
    - "Course" (课程安排 / 选课 / 考试 / 成绩)
    - "StudentStatus" (学籍管理 / 请假 / 转专业 / 处分)
    - "CampusLife" (宿舍 / 饮食 / 校园卡 / 网络 / 校园生活)
    - "Admission" (招生 / 报名 / 入学)
    - "Employment" (实习 / 就业 / 招聘)
    - "OtherSchool" (其他学校相关)
3. 如果不是学校相关问题，则 `is_school_related` 返回 False，`Intent_class` 填写 "非学校问题"，`Intent description` 简要描述用户的真实意图。
4. 输出必须是严格的 JSON 格式，不能有任何额外说明或文字。

输出格式示例：
{
"is_school_related": true,
"Intent_class": "Scholarship",
"Intent_description": "用户询问学校奖学金的相关信息"
}
"""


class IntentRecognitionService:
    """意图识别服务"""

    def __init__(self, intent_agent, llm, response_cache: dict = None):
        self.intent_agent = intent_agent
        self.llm = llm
        self.intent_prompt = INTENT_PROMPT
        self.response_cache = response_cache or {}

    async def recognize(self, question: str, image_data=None) -> Dict[str, Any]:
        """执行意图识别"""
        try:
            if image_data:
                return await self.intent_agent.recognize_multimodal_intent(question, image_data)
            else:
                return await self.intent_agent.recognize_text_intent(question)
        except Exception as e:
            logger.error(f"意图识别失败: {e}")
            return {
                "is_school_related": False,
                "intent_class": "Other",
                "confidence": 0.0,
                "error": str(e),
            }

    def analyze_sync(self, question: str) -> Dict[str, Any]:
        """意图分析 - 同步版本"""
        try:
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(self.intent_prompt),
                HumanMessage(content=f"用户问题: {question}"),
            ])
            chain = LLMChain(llm=self.llm, prompt=prompt, output_parser=JsonOutputParser())
            response = chain.invoke({"question": question})
            if isinstance(response, dict) and "text" in response:
                response_text = response["text"]
            elif isinstance(response, str):
                response_text = response
            else:
                response_text = str(response)
            try:
                return json.loads(response_text.strip())
            except Exception:
                return {"is_school_related": False, "Intent_class": "其他", "Intent_description": "意图分析失败"}
        except Exception as e:
            logger.error(f"意图分析失败: {e}")
            return {"is_school_related": False, "Intent_class": "其他", "Intent_description": "意图分析失败"}

    async def simple_recognition(self, question: str) -> Dict[str, Any]:
        """简化的意图识别，用于电话模式快速响应"""
        try:
            question_lower = question.lower()
            campus_keywords = ["学校", "校园", "教学楼", "图书馆", "食堂", "宿舍", "课程", "专业", "老师", "教授"]
            data_keywords = ["成绩", "学分", "课表", "选课", "考试", "分数"]

            if any(kw in question_lower for kw in campus_keywords):
                return {"intent_class": "knowledge_query", "is_school_related": True, "confidence": 0.8, "final_intent": "knowledge_query"}
            elif any(kw in question_lower for kw in data_keywords):
                return {"intent_class": "data_query", "is_school_related": True, "confidence": 0.8, "final_intent": "data_query"}
            else:
                return {"intent_class": "general_answer", "is_school_related": False, "confidence": 0.6, "final_intent": "general_answer"}
        except Exception as e:
            logger.error(f"简化意图识别失败: {e}")
            return {"intent_class": "general_answer", "is_school_related": False, "confidence": 0.5, "final_intent": "general_answer"}

    async def recognize_cached(self, question: str, image_data=None) -> Dict[str, Any]:
        """带缓存的意图识别"""
        intent_cache_key = f"intent_{hashlib.md5(question.encode()).hexdigest()}"
        if intent_cache_key in self.response_cache:
            cached_item = self.response_cache[intent_cache_key]
            if time.time() - cached_item["timestamp"] < 120:
                return cached_item["response"]

        result = await self.recognize(question, image_data)
        self.response_cache[intent_cache_key] = {"response": result, "timestamp": time.time()}
        return result

    async def recognize_redis_cached(self, question: str, image_data=None) -> Dict[str, Any]:
        """使用Redis缓存的意图识别"""
        try:
            from src.Chatbot.utils.db_utils import get_db_manager
            db_manager = get_db_manager()
            redis_conn = db_manager.get_redis_connection()

            intent_cache_key = f"intent_recognition:{hashlib.md5(question.encode()).hexdigest()}"
            loop = asyncio.get_event_loop()
            cached_result = await loop.run_in_executor(None, redis_conn.get, intent_cache_key)
            if cached_result:
                return json.loads(cached_result)

            result = await self.recognize(question, image_data)
            await loop.run_in_executor(None, redis_conn.setex, intent_cache_key, 120, json.dumps(result))
            return result
        except Exception as e:
            logger.error(f"Redis缓存意图识别失败，回退到普通缓存: {e}")
            return await self.recognize_cached(question, image_data)

    @staticmethod
    def format_intent_info(intent_result: Dict[str, Any]) -> str:
        """格式化意图信息"""
        intent_class = intent_result.get("intent_class", "unknown")
        is_school_related = intent_result.get("is_school_related", False)
        confidence = intent_result.get("confidence", 0.0)
        return f"意图类型：{intent_class}，学校相关：{is_school_related}，置信度：{confidence:.2f}"
