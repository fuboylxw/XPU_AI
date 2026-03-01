"""
安全审核服务
从 ChatbotAgent 提取的安全审核相关方法
"""
import logging
import hashlib
import json
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

logger = logging.getLogger(__name__)


class SecurityAuditService:
    """安全审核服务"""

    def __init__(self, security_agent, llm, response_cache: dict = None):
        self.security_agent = security_agent
        self.llm = llm
        self.response_cache = response_cache or {}

    async def perform_audit(self, question: str, context: List[str]) -> Dict[str, Any]:
        """执行安全审核"""
        try:
            audit_result = await self.security_agent.audit_content(question, context)
            return audit_result
        except Exception as e:
            logger.error(f"安全审核失败: {e}")
            return {"is_safe": False, "risk_level": "high", "error": str(e)}

    async def perform_audit_strict(self, question: str, context_list: List[str]) -> Dict[str, Any]:
        """严格安全审核"""
        try:
            keyword_result = self.security_agent._check_sensitive_keywords(question)
            content_prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content="你是一个严格且专业的内容安全审核助手，负责检测文本中的安全与合规风险。仅返回合法JSON。"),
                HumanMessage(content="{content}")
            ])
            parser = JsonOutputParser()
            ai_result = await (content_prompt | self.llm | parser).ainvoke({"content": question})
            ai_result["method"] = "ai_audit"

            context_result = None
            if context_list:
                context_str = "\n".join(context_list[-5:])
                context_prompt = ChatPromptTemplate.from_messages([
                    SystemMessage(content="你是一个专业的对话上下文安全审核助手，仅返回合法JSON。"),
                    HumanMessage(content="历史对话:\n{context}\n当前内容:\n{content}")
                ])
                context_result = await (context_prompt | self.llm | parser).ainvoke(
                    {"content": question, "context": context_str}
                )
                context_result["method"] = "context_audit"

            violations = []
            if keyword_result.get("violations"):
                violations.extend(keyword_result["violations"])
            if ai_result.get("violations"):
                violations.extend(ai_result["violations"])

            is_safe = keyword_result.get("is_safe", True) and ai_result.get("is_safe", True)
            risk_levels = [keyword_result.get("risk_level", "low"), ai_result.get("risk_level", "low")]
            if context_result:
                is_safe = is_safe and context_result.get("is_safe", True)
                risk_levels.append(context_result.get("context_risk", "low"))

            if "high" in risk_levels:
                final_risk = "high"
            elif "medium" in risk_levels:
                final_risk = "medium"
            else:
                final_risk = "low"

            return {
                "is_safe": is_safe,
                "risk_level": final_risk,
                "violations": violations,
                "audit_methods": {
                    "keyword_check": keyword_result,
                    "ai_audit": ai_result,
                    "context_audit": context_result,
                },
                "filtered_content": question if is_safe else self.security_agent._filter_content_by_keywords(question),
                "suggestions": "" if is_safe else "请遵守校纪校规，不请求不当内容。",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"严格安全审核失败: {e}")
            return {"is_safe": True, "risk_level": "low", "violations": [], "suggestions": "", "timestamp": datetime.now().isoformat()}

    async def perform_audit_cached(self, question: str, context: List[str]) -> Dict[str, Any]:
        """带缓存的安全审核"""
        audit_cache_key = f"security_{hashlib.md5(question.encode()).hexdigest()}"
        if audit_cache_key in self.response_cache:
            cached_item = self.response_cache[audit_cache_key]
            if time.time() - cached_item["timestamp"] < 60:
                return cached_item["response"]

        result = await self.perform_audit(question, context)
        self.response_cache[audit_cache_key] = {"response": result, "timestamp": time.time()}
        return result

    async def perform_audit_redis_cached(self, question: str, context: List[str]) -> Dict[str, Any]:
        """使用Redis缓存的安全审核"""
        try:
            from src.Chatbot.utils.db_utils import get_db_manager
            db_manager = get_db_manager()
            redis_conn = db_manager.get_redis_connection()

            audit_cache_key = f"security_audit:{hashlib.md5(question.encode()).hexdigest()}"
            loop = asyncio.get_event_loop()
            cached_result = await loop.run_in_executor(None, redis_conn.get, audit_cache_key)
            if cached_result:
                return json.loads(cached_result)

            result = await self.perform_audit(question, context)
            await loop.run_in_executor(None, redis_conn.setex, audit_cache_key, 60, json.dumps(result))
            return result
        except Exception as e:
            logger.error(f"Redis缓存安全审核失败，回退到普通缓存: {e}")
            return await self.perform_audit_cached(question, context)

    @staticmethod
    async def handle_security_block(question: str, security_result: Dict[str, Any]) -> Dict[str, Any]:
        """处理安全阻止的情况"""
        violations = security_result.get("violations", [])
        risk_level = security_result.get("risk_level", "unknown")

        if risk_level == "high":
            message = "您的问题包含不当内容，无法处理。请确保问题内容符合校园规范。"
        elif risk_level == "medium":
            message = "您的问题可能包含敏感内容，建议重新表述后再次提问。"
        else:
            message = "您的问题需要进一步审核，请稍后重试或联系相关部门。"

        if violations:
            violation_types = [v.get("type", "未知") for v in violations]
            message += f"\n检测到的问题类型：{', '.join(set(violation_types))}"

        return {
            "success": False,
            "question": question,
            "answer": message,
            "blocked": True,
            "security_result": security_result,
            "timestamp": datetime.now().isoformat(),
        }
