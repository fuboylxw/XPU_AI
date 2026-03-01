"""
聊天相关的API路由
"""
import uuid
import logging
import json
import os
import time
import hashlib
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Dict, Any, List

from fastapi_app.database import get_db
from fastapi_app.models import Conversation, ConversationHistory
from fastapi_app.schemas import ChatMessageRequest, ChatMessageResponse, ConversationResponse, ConversationCreate, ConversationUpdate, ConversationHistoryResponse
from fastapi_app.repositories.conversation import ConversationRepository
from src.Chatbot.core.providers import get_chatbot_agent

router = APIRouter()


@router.post("/chat/", response_model=ChatMessageResponse)
async def send_message(
    message_data: ChatMessageRequest,
    db: Session = Depends(get_db)
):
    """发送聊天消息（非流式）"""
    repo = ConversationRepository(db)
    try:
        conversation_id = message_data.conversation_id
        user_message = message_data.message
        user_id = message_data.user_id

        conversation = repo.get_by_conversation_id(conversation_id)

        if not conversation:
            existing = repo.get_active_for_user(user_id)
            if existing:
                conversation = existing
                conversation_id = existing.conversation_id
            else:
                title = user_message[:50] + "..." if len(user_message) > 50 else user_message
                conversation = repo.create(user_id=user_id, title=title)
                conversation_id = conversation.conversation_id

        chat_agent = get_chatbot_agent()
        if not chat_agent:
            raise HTTPException(status_code=500, detail="聊天服务初始化失败")

        history_records = repo.get_history(conversation_id)
        conversation_history = []
        for record in history_records:
            conversation_history.append({"role": "user", "content": record.question})
            conversation_history.append({"role": "assistant", "content": record.answer})

        try:
            response = await chat_agent.answer_question(
                question=user_message,
                conversation_id=conversation_id,
                user_id=user_id,
                user_role="guest"
            )
            if response.get('success', False):
                ai_response = response.get('answer', '抱歉，未能获取到回复')
            else:
                ai_response = response.get('answer', f"处理失败: {response.get('error', '未知错误')}")
        except Exception as agent_error:
            logging.error(f"ChatbotAgent处理消息失败: {str(agent_error)}")
            ai_response = f"抱歉，处理您的消息时出现错误: {str(agent_error)}"

        history_record = repo.save_history(conversation_id, user_message, ai_response)

        return ChatMessageResponse(
            conversation_id=conversation_id,
            message=user_message,
            response=ai_response,
            timestamp=history_record.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"发送消息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"发送消息失败: {str(e)}")


@router.post("/chat/stream/")
async def send_message_stream(
    message_data: ChatMessageRequest,
    db: Session = Depends(get_db)
):
    """发送消息并获取AI流式回复"""
    repo = ConversationRepository(db)

    try:
        conversation_id = message_data.conversation_id
        message = message_data.message
        user_id = message_data.user_id
        use_web_search = getattr(message_data, "use_web_search", False)

        chat_agent = get_chatbot_agent()
        if chat_agent is None:
            raise HTTPException(status_code=500, detail="ChatbotAgent未初始化")

        async def stream_generator():
            try:
                conversation = repo.get_by_conversation_id(conversation_id)
                if not conversation:
                    repo.create_with_md5_id(
                        conversation_id=conversation_id,
                        user_id=user_id,
                        title=f'会话 {conversation_id[:8]}'
                    )

                full_response = ""
                async for chunk in chat_agent.answer_question_stream(
                    question=message,
                    conversation_id=conversation_id,
                    user_id=user_id,
                    user_role="guest",
                    session_token=None,
                    use_web_search=use_web_search
                ):
                    full_response += chunk
                    chunk_data = f"data: {json.dumps({'chunk': chunk, 'type': 'chunk'}, ensure_ascii=False)}\n\n"
                    yield chunk_data
                    await asyncio.sleep(0.01)

                done_data = f"data: {json.dumps({'type': 'done', 'full_response': full_response}, ensure_ascii=False)}\n\n"
                yield done_data

                repo.save_history(conversation_id, message, full_response)

            except Exception as e:
                error_msg = f"流式处理失败: {str(e)}"
                error_data = f"data: {json.dumps({'type': 'error', 'error': error_msg}, ensure_ascii=False)}\n\n"
                yield error_data
                logging.error(f"流式问答处理失败: {error_msg}")

        return StreamingResponse(
            stream_generator(),
            media_type='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type'
            }
        )

    except Exception as e:
        logging.error(f"发送流式消息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"发送流式消息失败: {str(e)}")


@router.get("/conversations/", response_model=List[ConversationResponse])
async def get_conversations(user_id: str = None, db: Session = Depends(get_db)):
    try:
        repo = ConversationRepository(db)
        return repo.list_for_user(user_id)
    except Exception as e:
        logging.error(f"获取对话列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取对话列表失败: {str(e)}")


@router.post("/conversations/get_or_create/", response_model=ConversationResponse)
async def get_or_create_user_conversation(
    conversation_data: ConversationCreate,
    db: Session = Depends(get_db)
):
    try:
        repo = ConversationRepository(db)
        existing = repo.get_active_for_user(conversation_data.user_id)
        if existing:
            logging.info(f"找到用户 {conversation_data.user_id} 的现有会话: {existing.conversation_id}")
            return existing
        conv = repo.create(
            user_id=conversation_data.user_id,
            title=conversation_data.title or "我的对话",
            status=conversation_data.status,
        )
        logging.info(f"为用户 {conversation_data.user_id} 创建新会话: {conv.conversation_id}")
        return conv
    except Exception as e:
        db.rollback()
        logging.error(f"获取或创建对话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取或创建对话失败: {str(e)}")


@router.post("/conversations/create/", response_model=ConversationResponse)
async def create_conversation(
    conversation_data: ConversationCreate,
    db: Session = Depends(get_db)
):
    try:
        repo = ConversationRepository(db)
        conv = repo.create(
            user_id=conversation_data.user_id,
            title=conversation_data.title or f"新对话 {int(time.time())}",
            status=conversation_data.status,
        )
        logging.info(f"为用户 {conversation_data.user_id} 创建新会话: {conv.conversation_id}")
        return conv
    except Exception as e:
        db.rollback()
        logging.error(f"创建对话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建对话失败: {str(e)}")


@router.get("/conversations/{conversation_id}/messages/", response_model=List[ConversationHistoryResponse])
async def get_conversation_messages(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    try:
        repo = ConversationRepository(db)
        conversation = repo.get_by_conversation_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="对话不存在")
        return repo.get_history(conversation_id)
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
    try:
        repo = ConversationRepository(db)
        conversation = repo.get_by_conversation_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="对话不存在")
        messages = repo.get_history(conversation_id)
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
    try:
        repo = ConversationRepository(db)
        return repo.list_all_with_message_count()
    except Exception as e:
        logging.error(f"获取所有上下文失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取所有上下文失败: {str(e)}")


@router.delete("/conversations/{conversation_id}/delete/")
async def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    try:
        repo = ConversationRepository(db)
        conversation = repo.get_by_conversation_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="对话不存在")
        repo.delete(conversation_id)
        return {"message": "对话删除成功", "conversation_id": conversation_id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"删除对话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除对话失败: {str(e)}")


@router.put("/conversations/{conversation_id}/title", response_model=ConversationResponse)
async def update_conversation_title(
    conversation_id: str,
    conversation_update: ConversationUpdate,
    db: Session = Depends(get_db)
):
    try:
        repo = ConversationRepository(db)
        new_title = (conversation_update.title or "").strip()
        if not new_title:
            raise HTTPException(status_code=400, detail="标题不能为空")
        conv = repo.update_title(conversation_id, new_title)
        return conv
    except ValueError:
        raise HTTPException(status_code=404, detail="对话不存在")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"更新对话标题失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新对话标题失败: {str(e)}")
