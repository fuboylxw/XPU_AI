"""
对话会话相关的API路由
"""
import uuid
import logging
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Dict, Any

from fastapi_app.database import get_db
from fastapi_app.models import Conversation, ConversationHistory
from fastapi_app.schemas import (
    ConversationResponse, ConversationCreate, ConversationUpdate,
    ConversationHistoryResponse
)

router = APIRouter()


@router.get("/conversations/", response_model=List[ConversationResponse])
async def get_conversations(user_id: str = None, db: Session = Depends(get_db)):
    """获取对话列表"""
    try:
        query = db.query(Conversation)
        if user_id:
            query = query.filter(Conversation.user_id == user_id)
        
        conversations = query.order_by(desc(Conversation.created)).all()
        
        # 处理modified字段为NULL的情况
        for conv in conversations:
            if conv.modified is None:
                conv.modified = conv.created
        
        return conversations
    except Exception as e:
        logging.error(f"获取对话列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取对话列表失败: {str(e)}")


@router.post("/conversations/get_or_create/", response_model=ConversationResponse)
async def get_or_create_user_conversation(
    conversation_data: ConversationCreate,
    db: Session = Depends(get_db)
):
    """获取或创建用户的唯一对话（一个用户只有一个会话）"""
    try:
        # 查找用户现有的活跃对话
        existing_conversation = db.query(Conversation).filter(
            Conversation.user_id == conversation_data.user_id,
            Conversation.status == 1
        ).first()
        
        if existing_conversation:
            logging.info(f"找到用户 {conversation_data.user_id} 的现有会话: {existing_conversation.conversation_id}")
            return existing_conversation
        
        # 如果没有现有对话，创建新的
        conversation_id = f"conv_{conversation_data.user_id}_{int(time.time())}"
        
        # 创建对话记录
        db_conversation = Conversation(
            id=str(uuid.uuid4()).replace('-', ''),  # 生成32字符的ID（移除连字符）
            conversation_id=conversation_id,  # 业务对话ID
            user_id=conversation_data.user_id,
            title=conversation_data.title or f"我的对话",
            status=conversation_data.status
        )
        
        db.add(db_conversation)
        db.commit()
        db.refresh(db_conversation)
        
        logging.info(f"为用户 {conversation_data.user_id} 创建新会话: {conversation_id}")
        return db_conversation
        
    except Exception as e:
        db.rollback()
        logging.error(f"获取或创建对话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取或创建对话失败: {str(e)}")


@router.post("/conversations/create/", response_model=ConversationResponse)
async def create_conversation(
    conversation_data: ConversationCreate,
    db: Session = Depends(get_db)
):
    """创建新对话"""
    try:
        # 生成唯一的对话ID
        conversation_id = f"conv_{conversation_data.user_id}_{int(time.time())}"
        
        # 创建对话记录
        db_conversation = Conversation(
            id=str(uuid.uuid4()).replace('-', ''),  # 生成32字符的ID（移除连字符）
            conversation_id=conversation_id,  # 业务对话ID
            user_id=conversation_data.user_id,
            title=conversation_data.title or f"新对话 {int(time.time())}",
            status=conversation_data.status
        )
        
        db.add(db_conversation)
        db.commit()
        db.refresh(db_conversation)
        
        logging.info(f"为用户 {conversation_data.user_id} 创建新会话: {conversation_id}")
        return db_conversation
        
    except Exception as e:
        db.rollback()
        logging.error(f"创建对话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建对话失败: {str(e)}")


@router.get("/conversations/{conversation_id}/messages/", response_model=List[ConversationHistoryResponse])
async def get_conversation_messages(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    """获取指定对话的消息历史"""
    try:
        # 检查对话是否存在
        conversation = db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="对话不存在")
        
        # 获取消息历史
        messages = db.query(ConversationHistory).filter(
            ConversationHistory.conversation_id == conversation_id
        ).order_by(ConversationHistory.created_at).all()
        
        return messages
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"获取对话消息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取对话消息失败: {str(e)}")


@router.get("/conversations/{conversation_id}/context/", response_model=Dict[str, Any])
async def get_conversation_context(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    """获取指定对话的上下文信息"""
    try:
        # 检查对话是否存在
        conversation = db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="对话不存在")
        
        # 获取消息历史
        messages = db.query(ConversationHistory).filter(
            ConversationHistory.conversation_id == conversation_id
        ).order_by(ConversationHistory.created_at).all()
        
        # 构建上下文信息
        context = {
            'conversation_id': conversation_id,
            'title': conversation.title,
            'message_count': len(messages),
            'created': conversation.created.isoformat(),
            'modified': (conversation.modified or conversation.created).isoformat(),
            'messages': [
                {
                    'id': msg.id,
                    'question': msg.question,
                    'answer': msg.answer,
                    'created_at': msg.created_at.isoformat()
                }
                for msg in messages
            ]
        }
        
        return context
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"获取对话上下文失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取对话上下文失败: {str(e)}")


@router.get("/contexts/", response_model=List[Dict[str, Any]])
async def get_all_contexts(db: Session = Depends(get_db)):
    """获取所有对话的上下文信息"""
    try:
        conversations = db.query(Conversation).order_by(desc(Conversation.modified)).all()
        
        contexts = []
        for conversation in conversations:
            # 获取每个对话的消息数量
            message_count = db.query(ConversationHistory).filter(
                ConversationHistory.conversation_id == conversation.conversation_id
            ).count()
            
            contexts.append({
                'conversation_id': conversation.conversation_id,
                'title': conversation.title,
                'message_count': message_count,
                'created': conversation.created.isoformat(),
                'modified': (conversation.modified or conversation.created).isoformat(),
                'status': conversation.status
            })
        
        return contexts
        
    except Exception as e:
        logging.error(f"获取所有上下文失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取所有上下文失败: {str(e)}")


@router.delete("/conversations/{conversation_id}/delete/")
async def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    """删除指定对话及其所有消息"""
    try:
        # 检查对话是否存在
        conversation = db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="对话不存在")
        
        # 删除对话历史记录
        db.query(ConversationHistory).filter(
            ConversationHistory.conversation_id == conversation_id
        ).delete()
        
        # 删除对话记录
        db.delete(conversation)
        db.commit()
        
        return {"message": "对话删除成功", "conversation_id": conversation_id}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"删除对话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除对话失败: {str(e)}")