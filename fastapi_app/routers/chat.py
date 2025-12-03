"""
聊天相关的API路由
"""
import uuid
import logging
import json
import os
import sys
import time
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Dict, Any, List

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi_app.database import get_db
from fastapi_app.models import Conversation, ConversationHistory
from fastapi_app.schemas import ChatMessageRequest, ChatMessageResponse, ConversationResponse, ConversationCreate, ConversationUpdate, ConversationHistoryResponse

router = APIRouter()

# 延迟导入ChatbotAgent，避免循环导入问题
chatbot_agent = None

def get_chatbot_agent():
    """获取ChatbotAgent实例，延迟初始化"""
    global chatbot_agent
    if chatbot_agent is None:
        try:
            print("🔍 开始初始化ChatbotAgent...")
            from src.Chatbot.agents.chat_agent import ChatbotAgent
            print("✅ ChatbotAgent导入成功")
            chatbot_agent = ChatbotAgent()
            print("✅ ChatbotAgent初始化成功")
        except Exception as e:
            print(f"❌ 初始化ChatbotAgent失败: {str(e)}")
            logging.error(f"初始化ChatbotAgent失败: {str(e)}")
            import traceback
            traceback.print_exc()
            chatbot_agent = None
    return chatbot_agent


@router.post("/chat/", response_model=ChatMessageResponse)
async def send_message(
    message_data: ChatMessageRequest,
    db: Session = Depends(get_db)
):
    """发送聊天消息（非流式）"""
    try:
        conversation_id = message_data.conversation_id
        user_message = message_data.message
        user_id = message_data.user_id
        
        # 检查对话是否存在，如果不存在则获取或创建用户的唯一对话
        conversation = db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id
        ).first()
        
        if not conversation:
            # 查找用户现有的活跃对话
            existing_conversation = db.query(Conversation).filter(
                Conversation.user_id == user_id,
                Conversation.status == 1
            ).first()
            
            if existing_conversation:
                # 使用现有对话
                conversation = existing_conversation
                conversation_id = existing_conversation.conversation_id
            else:
                # 创建新对话，使用用户ID作为会话标识
                unique_conversation_id = f"conv_{user_id}_{int(time.time())}"
                conversation = Conversation(
                    id=str(uuid.uuid4()).replace('-', '')[:32],
                    conversation_id=unique_conversation_id,
                    user_id=user_id,
                    title=user_message[:50] + "..." if len(user_message) > 50 else user_message,
                    status=1
                )
                db.add(conversation)
                db.commit()
                conversation_id = unique_conversation_id
        
        # 获取ChatbotAgent
        chat_agent = get_chatbot_agent()
        if not chat_agent:
            raise HTTPException(status_code=500, detail="聊天服务初始化失败")
        
        # 获取对话历史
        history_records = db.query(ConversationHistory).filter(
            ConversationHistory.conversation_id == conversation_id
        ).order_by(ConversationHistory.created_at).all()
        
        # 构建对话历史
        conversation_history = []
        for record in history_records:
            conversation_history.append({"role": "user", "content": record.question})
            conversation_history.append({"role": "assistant", "content": record.answer})
        
        # 调用ChatbotAgent获取回复
        try:
            # 使用非流式方法获取完整回复
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
        
        # 保存对话历史
        history_record = ConversationHistory(
            conversation_id=conversation_id,
            question=user_message,
            answer=ai_response
        )
        db.add(history_record)
        
        # 更新对话的修改时间
        conversation.modified = history_record.created_at
        
        db.commit()
        
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
    import asyncio
    import json
    import hashlib
    
    try:
        # 获取请求数据
        conversation_id = message_data.conversation_id
        message = message_data.message
        user_id = message_data.user_id
        use_web_search = getattr(message_data, "use_web_search", False)
        
        # 获取ChatbotAgent实例
        chat_agent = get_chatbot_agent()
        if chat_agent is None:
            raise HTTPException(status_code=500, detail="ChatbotAgent未初始化")

        async def stream_generator():
            """生成流式响应"""
            try:
                # 确保会话存在
                conversation = db.query(Conversation).filter(
                    Conversation.conversation_id == conversation_id
                ).first()
                
                if not conversation:
                    # 创建新会话，使用MD5哈希生成32字符ID
                    short_id = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()
                    conversation = Conversation(
                        id=short_id,
                        conversation_id=conversation_id,
                        user_id=user_id,
                        title=f'会话 {conversation_id[:8]}'
                    )
                    db.add(conversation)
                    db.commit()
                
                # 调用流式问答函数
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
                    # 立即发送数据块，使用SSE格式
                    chunk_data = f"data: {json.dumps({'chunk': chunk, 'type': 'chunk'}, ensure_ascii=False)}\n\n"
                    yield chunk_data
                    # 强制刷新缓冲区
                    await asyncio.sleep(0.01)  # 添加小延迟确保流式输出
                
                # 发送完成信号
                done_data = f"data: {json.dumps({'type': 'done', 'full_response': full_response}, ensure_ascii=False)}\n\n"
                yield done_data
                
                # 保存完整对话到数据库
                conversation_history = ConversationHistory(
                    conversation_id=conversation_id,
                    question=message,
                    answer=full_response
                )
                db.add(conversation_history)
                db.commit()
                        
            except Exception as e:
                error_msg = f"流式处理失败: {str(e)}"
                error_data = f"data: {json.dumps({'type': 'error', 'error': error_msg}, ensure_ascii=False)}\n\n"
                yield error_data
                logging.error(f"流式问答处理失败: {error_msg}")
        
        # 返回流式响应
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
        query = db.query(Conversation)
        if user_id:
            query = query.filter(Conversation.user_id == user_id)
        conversations = query.order_by(desc(Conversation.created)).all()
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
    try:
        existing_conversation = db.query(Conversation).filter(
            Conversation.user_id == conversation_data.user_id,
            Conversation.status == 1
        ).first()
        if existing_conversation:
            logging.info(f"找到用户 {conversation_data.user_id} 的现有会话: {existing_conversation.conversation_id}")
            return existing_conversation
        conversation_id = f"conv_{conversation_data.user_id}_{int(time.time())}"
        db_conversation = Conversation(
            id=str(uuid.uuid4()).replace('-', ''),
            conversation_id=conversation_id,
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
    try:
        conversation_id = f"conv_{conversation_data.user_id}_{int(time.time())}"
        db_conversation = Conversation(
            id=str(uuid.uuid4()).replace('-', ''),
            conversation_id=conversation_id,
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
    try:
        conversation = db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id
        ).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="对话不存在")
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
    try:
        conversation = db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id
        ).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="对话不存在")
        messages = db.query(ConversationHistory).filter(
            ConversationHistory.conversation_id == conversation_id
        ).order_by(ConversationHistory.created_at).all()
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
        conversations = db.query(Conversation).order_by(desc(Conversation.modified)).all()
        contexts = []
        for conversation in conversations:
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
    try:
        conversation = db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id
        ).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="对话不存在")
        db.query(ConversationHistory).filter(
            ConversationHistory.conversation_id == conversation_id
        ).delete()
        db.delete(conversation)
        db.commit()
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
        conv = db.query(Conversation).filter(Conversation.conversation_id == conversation_id).first()
        if not conv:
            raise HTTPException(status_code=404, detail="对话不存在")
        new_title = (conversation_update.title or "").strip()
        if not new_title:
            raise HTTPException(status_code=400, detail="标题不能为空")
        conv.title = new_title
        db.add(conv)
        db.commit()
        db.refresh(conv)
        return conv
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"更新对话标题失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新对话标题失败: {str(e)}")
