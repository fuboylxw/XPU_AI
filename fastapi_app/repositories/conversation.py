"""
对话数据访问层
封装所有 Conversation / ConversationHistory 的数据库操作
"""
import uuid
import time
import hashlib
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from fastapi_app.models import Conversation, ConversationHistory


class ConversationRepository:
    """对话 Repository"""

    def __init__(self, db: Session):
        self.db = db

    # ── Conversation ──

    def get_by_conversation_id(self, conversation_id: str) -> Optional[Conversation]:
        return self.db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id
        ).first()

    def get_active_for_user(self, user_id: str) -> Optional[Conversation]:
        return self.db.query(Conversation).filter(
            Conversation.user_id == user_id,
            Conversation.status == 1
        ).first()

    def create(self, user_id: str, title: str, status: int = 1,
               conversation_id: str = None) -> Conversation:
        if conversation_id is None:
            conversation_id = f"conv_{user_id}_{int(time.time())}"
        conv = Conversation(
            id=str(uuid.uuid4()).replace('-', '')[:32],
            conversation_id=conversation_id,
            user_id=user_id,
            title=title,
            status=status,
        )
        self.db.add(conv)
        self.db.commit()
        self.db.refresh(conv)
        return conv

    def create_with_md5_id(self, conversation_id: str, user_id: str,
                           title: str) -> Conversation:
        short_id = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()
        conv = Conversation(
            id=short_id,
            conversation_id=conversation_id,
            user_id=user_id,
            title=title,
        )
        self.db.add(conv)
        self.db.commit()
        return conv

    def list_for_user(self, user_id: str = None) -> List[Conversation]:
        query = self.db.query(Conversation)
        if user_id:
            query = query.filter(Conversation.user_id == user_id)
        conversations = query.order_by(desc(Conversation.created)).all()
        for conv in conversations:
            if conv.modified is None:
                conv.modified = conv.created
        return conversations

    def list_all_with_message_count(self) -> List[Dict[str, Any]]:
        conversations = self.db.query(Conversation).order_by(
            desc(Conversation.modified)
        ).all()
        result = []
        for conv in conversations:
            count = self.db.query(ConversationHistory).filter(
                ConversationHistory.conversation_id == conv.conversation_id
            ).count()
            result.append({
                'conversation_id': conv.conversation_id,
                'title': conv.title,
                'message_count': count,
                'created': conv.created.isoformat(),
                'modified': (conv.modified or conv.created).isoformat(),
                'status': conv.status,
            })
        return result

    def update_title(self, conversation_id: str, title: str) -> Conversation:
        conv = self.get_by_conversation_id(conversation_id)
        if conv is None:
            raise ValueError("对话不存在")
        conv.title = title
        self.db.add(conv)
        self.db.commit()
        self.db.refresh(conv)
        return conv

    def delete(self, conversation_id: str) -> None:
        self.db.query(ConversationHistory).filter(
            ConversationHistory.conversation_id == conversation_id
        ).delete()
        conv = self.get_by_conversation_id(conversation_id)
        if conv:
            self.db.delete(conv)
        self.db.commit()

    # ── ConversationHistory ──

    def get_history(self, conversation_id: str) -> List[ConversationHistory]:
        return self.db.query(ConversationHistory).filter(
            ConversationHistory.conversation_id == conversation_id
        ).order_by(ConversationHistory.created_at).all()

    def save_history(self, conversation_id: str, question: str,
                     answer: str) -> ConversationHistory:
        record = ConversationHistory(
            conversation_id=conversation_id,
            question=question,
            answer=answer,
        )
        self.db.add(record)
        self.db.commit()
        return record
