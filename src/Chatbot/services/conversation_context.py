"""
对话上下文管理服务
从 ChatbotAgent 提取的对话上下文相关方法
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ConversationContextService:
    """对话上下文管理服务"""

    def __init__(self):
        self.qa_conversations: Dict[str, List[Dict[str, Any]]] = {}

    def get_qa_context(self, conversation_id: str) -> List[str]:
        """获取对话上下文（最近5轮问题）"""
        conversation = self.qa_conversations.get(conversation_id, [])
        return [item["question"] for item in conversation[-5:]]

    def update_qa_conversation(self, conversation_id: str, question: str, answer: str):
        """更新对话历史并存储到数据库"""
        if conversation_id not in self.qa_conversations:
            self.qa_conversations[conversation_id] = []

        current_time = datetime.now().isoformat()
        self.qa_conversations[conversation_id].append(
            {"question": question, "answer": answer, "timestamp": current_time}
        )

        if len(self.qa_conversations[conversation_id]) > 50:
            self.qa_conversations[conversation_id] = self.qa_conversations[conversation_id][-25:]

        try:
            from src.Chatbot.utils.db_utils import get_db_manager
            db_manager = get_db_manager()
            db_manager.save_conversation(conversation_id, question, answer, current_time)
        except Exception as e:
            logger.error(f"存储对话记录到数据库失败: {e}")

    def update_qa_conversation_memory(self, conversation_id: str, question: str, answer: str):
        """更新内存中的对话历史（不涉及数据库操作）"""
        if conversation_id not in self.qa_conversations:
            self.qa_conversations[conversation_id] = []

        current_time = datetime.now().isoformat()
        self.qa_conversations[conversation_id].append(
            {"question": question, "answer": answer, "timestamp": current_time}
        )

        if len(self.qa_conversations[conversation_id]) > 50:
            self.qa_conversations[conversation_id] = self.qa_conversations[conversation_id][-25:]

    def save_question_to_db(self, conversation_id: str, question: str) -> Optional[int]:
        """在流式输出开始前，先保存问题到数据库"""
        try:
            from src.Chatbot.utils.db_utils import get_db_manager
            db_manager = get_db_manager()
            record_id = db_manager.save_conversation_with_id(conversation_id, question, "", "default_user")
            return record_id
        except Exception as e:
            logger.error(f"保存问题到数据库失败: {e}")
            return None

    def update_answer_in_db(self, record_id: Optional[int], answer: str):
        """在流式输出过程中实时更新答案到数据库"""
        if record_id is None:
            return
        try:
            from src.Chatbot.utils.db_utils import get_db_manager
            db_manager = get_db_manager()
            db_manager.update_conversation_answer(record_id, answer)
        except Exception as e:
            logger.error(f"更新答案到数据库失败: {e}")

    def get_conversation_context(self, conversation_id: str) -> str:
        """获取对话上下文（带Redis缓存）"""
        try:
            from src.Chatbot.utils.db_utils import get_db_manager
            db_manager = get_db_manager()
            redis_conn = db_manager.get_redis_connection()

            cache_key = f"conversation_context:{conversation_id}"
            cached_context = redis_conn.get(cache_key)
            if cached_context:
                return cached_context.decode("utf-8") if isinstance(cached_context, bytes) else cached_context

            conversation = db_manager.get_conversation_history(conversation_id, limit=5)
            if not conversation:
                memory_conversation = self.qa_conversations.get(conversation_id, [])
                if not memory_conversation:
                    return ""
                conversation = memory_conversation[-5:]

            context_parts = []
            for item in conversation:
                context_parts.append(f"用户: {item['question']}")
                if item.get("answer"):
                    context_parts.append(f"助手: {item['answer']}")

            context_str = "\n".join(context_parts)

            try:
                redis_conn.setex(cache_key, 1800, context_str)
            except Exception:
                pass

            return context_str
        except Exception as e:
            logger.error(f"获取对话上下文失败: {e}")
            memory_conversation = self.qa_conversations.get(conversation_id, [])
            if not memory_conversation:
                return ""
            context_parts = []
            for item in memory_conversation[-5:]:
                context_parts.append(f"用户: {item['question']}")
                if item.get("answer"):
                    context_parts.append(f"助手: {item['answer']}")
            return "\n".join(context_parts)

    async def get_conversation_context_async(self, conversation_id: str) -> str:
        """异步获取对话上下文"""
        return self.get_conversation_context(conversation_id)

    async def get_phone_conversation_history(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """获取用户的电话对话历史上下文"""
        try:
            from fastapi_app.database import SessionLocal
            from fastapi_app.models import PhoneSession, PhoneConversationHistory

            db = SessionLocal()
            try:
                active_session = db.query(PhoneSession).filter(
                    PhoneSession.user_id == user_id,
                    PhoneSession.status == 1
                ).first()

                if not active_session:
                    return []

                history = db.query(PhoneConversationHistory).filter(
                    PhoneConversationHistory.session_id == active_session.id
                ).order_by(PhoneConversationHistory.created_at.desc()).limit(limit).all()

                conversation_history = []
                for record in reversed(history):
                    conversation_history.append({
                        "question": record.question,
                        "answer": record.answer,
                        "timestamp": record.created_at.isoformat() if record.created_at else None,
                    })
                return conversation_history
            finally:
                db.close()
        except Exception as e:
            logger.error(f"获取电话对话历史失败: {e}")
            return []

    @staticmethod
    def format_phone_conversation_context(history: List[Dict[str, Any]]) -> str:
        """格式化电话对话上下文"""
        if not history:
            return ""
        parts = []
        for item in history:
            if item.get("question"):
                parts.append(f"用户: {item['question']}")
            if item.get("answer"):
                parts.append(f"助手: {item['answer']}")
        return "\n".join(parts)

    def clear_conversation(self, conversation_id: str):
        """清空指定对话"""
        if conversation_id in self.qa_conversations:
            del self.qa_conversations[conversation_id]

    def get_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """获取对话历史"""
        return self.qa_conversations.get(conversation_id, [])
