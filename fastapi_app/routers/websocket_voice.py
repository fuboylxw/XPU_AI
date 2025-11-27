"""
WebSocket持续语音监听路由
实现真正的持续语音监听功能
"""

import asyncio
import json
import logging
import tempfile
import uuid
import os
import io
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.websockets import WebSocketState
from sqlalchemy.orm import Session
from pydub import AudioSegment
import speech_recognition as sr

from ..database import get_db
from ..models import PhoneSession, PhoneConversationHistory

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter()

# 简化的语音识别函数
async def recognize_audio(audio_data: bytes) -> str:
    """简化的语音识别函数，用于测试"""
    try:
        # 模拟语音识别结果
        return f"测试语音识别结果 - 收到 {len(audio_data)} 字节音频数据"
    except Exception as e:
        logger.error(f"语音识别失败: {e}")
        return ""

class ContinuousVoiceSession:
    """持续语音监听会话"""
    
    def __init__(self, session_id: str, user_id: str, websocket: WebSocket):
        self.session_id = session_id
        self.user_id = user_id
        self.websocket = websocket
        self.phone_session_id = None
        self.is_active = True
        self.last_activity = datetime.now()
        self.context_history = []
        self.audio_buffer = []
        self.is_processing = False
        
    def add_conversation(self, question: str, answer: str):
        """添加对话记录"""
        self.context_history.append({
            "question": question,
            "answer": answer,
            "timestamp": datetime.now()
        })
        self.last_activity = datetime.now()
        
        # 保持最近10轮对话
        if len(self.context_history) > 10:
            self.context_history = self.context_history[-10:]
    
    def get_context_for_ai(self) -> str:
        """获取AI上下文"""
        if not self.context_history:
            return ""
        
        context_parts = []
        for item in self.context_history[-5:]:
            context_parts.append(f"用户: {item['question']}")
            context_parts.append(f"助手: {item['answer']}")
        
        return "\n".join(context_parts)
    
    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """检查会话是否过期"""
        return datetime.now() - self.last_activity > timedelta(minutes=timeout_minutes)
    
    async def send_message(self, message: dict):
        """发送消息到客户端"""
        try:
            if self.websocket.client_state == WebSocketState.CONNECTED:
                await self.websocket.send_text(json.dumps(message, ensure_ascii=False))
        except Exception as e:
            logger.error(f"发送WebSocket消息失败: {e}")
            self.is_active = False
    
    async def send_audio(self, audio_data: bytes):
        """发送音频数据到客户端"""
        try:
            if self.websocket.client_state == WebSocketState.CONNECTED:
                await self.websocket.send_bytes(audio_data)
        except Exception as e:
            logger.error(f"发送WebSocket音频失败: {e}")
            self.is_active = False

# 全局会话管理
active_sessions: Dict[str, ContinuousVoiceSession] = {}

async def cleanup_expired_sessions():
    """清理过期会话"""
    expired_sessions = []
    for session_id, session in active_sessions.items():
        if session.is_expired() or not session.is_active:
            expired_sessions.append(session_id)
    
    for session_id in expired_sessions:
        session = active_sessions.pop(session_id, None)
        if session:
            logger.info(f"清理过期的持续语音会话: {session_id}")

@router.websocket("/ws/continuous_voice/{user_id}")
async def continuous_voice_websocket(
    websocket: WebSocket, 
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    持续语音监听WebSocket端点
    """
    await websocket.accept()
    
    # 创建会话
    session_id = f"ws_voice_{uuid.uuid4().hex[:12]}"
    session = ContinuousVoiceSession(session_id, user_id, websocket)
    
    try:
        # 创建电话会话 - 简化版本，不依赖voice模块
        phone_session = PhoneSession(
            user_id=user_id,
            session_id=f"phone_{uuid.uuid4().hex[:12]}",
            status="active",
            created_at=datetime.now()
        )
        db.add(phone_session)
        db.commit()
        db.refresh(phone_session)
        
        session.phone_session_id = phone_session.session_id
        
        # 注册会话
        active_sessions[session_id] = session
        
        logger.info(f"建立持续语音监听连接: {session_id}, 用户: {user_id}")
        
        # 发送连接成功消息
        await session.send_message({
            "type": "connection_established",
            "session_id": session_id,
            "phone_session_id": phone_session.session_id,
            "message": "持续语音监听连接已建立"
        })
        
        # 启动后台任务
        cleanup_task = asyncio.create_task(periodic_cleanup())
        
        try:
            while session.is_active:
                # 接收消息
                try:
                    data = await asyncio.wait_for(websocket.receive(), timeout=1.0)
                    
                    if data.get("type") == "websocket.receive":
                        if "bytes" in data:
                            # 接收到音频数据
                            await handle_audio_data(session, data["bytes"], db)
                        elif "text" in data:
                            # 接收到文本消息
                            message = json.loads(data["text"])
                            await handle_text_message(session, message, db)
                            
                except asyncio.TimeoutError:
                    # 超时，检查连接状态
                    if websocket.client_state != WebSocketState.CONNECTED:
                        break
                    continue
                except WebSocketDisconnect:
                    logger.info(f"客户端断开连接: {session_id}")
                    break
                    
        finally:
            cleanup_task.cancel()
            
    except Exception as e:
        logger.error(f"WebSocket连接异常: {e}")
        await session.send_message({
            "type": "error",
            "message": f"连接异常: {str(e)}"
        })
    finally:
        # 清理会话
        if session_id in active_sessions:
            del active_sessions[session_id]
        
        # 结束电话会话
        if session.phone_session_id:
            end_phone_session(session.phone_session_id, db)
        
        logger.info(f"持续语音监听会话结束: {session_id}")

async def handle_audio_data(session: ContinuousVoiceSession, audio_data: bytes, db: Session):
    """处理音频数据"""
    if session.is_processing:
        return  # 如果正在处理，跳过
    
    session.is_processing = True
    
    try:
        if len(audio_data) == 0:
            return
        
        logger.info(f"处理音频数据: {len(audio_data)} bytes")
        
        # 语音识别
        recognized_text = await recognize_audio(audio_data)
        
        if recognized_text and recognized_text.strip():
            logger.info(f"识别到语音: {recognized_text}")
            
            # 发送识别结果
            await session.send_message({
                "type": "speech_recognized",
                "text": recognized_text
            })
            
            # 获取AI回复 - 简化版本，返回固定回复
            response_text = f"我收到了您的消息：{recognized_text}。这是WebSocket持续语音监听的测试回复。"
            
            logger.info(f"AI回复: {response_text[:100]}...")
            
            # 发送AI回复文本
            await session.send_message({
                "type": "ai_response",
                "text": response_text
            })
            
            # 添加到会话历史
            session.add_conversation(recognized_text, response_text)
            
            # 保存到数据库 - 使用正确的字段名
            if session.phone_session_id:
                conversation = PhoneConversationHistory(
                    session_id=session.phone_session_id,
                    user_id=session.user_id,
                    question=recognized_text,
                    answer=response_text
                )
                db.add(conversation)
                db.commit()
            
            # 生成语音回复 - 简化版本，跳过TTS
            try:
                # 发送模拟音频完成消息
                await session.send_message({
                    "type": "audio_response_complete", 
                    "message": "语音回复已发送（测试模式）"
                })
                
            except Exception as e:
                logger.error(f"生成语音回复失败: {e}")
                await session.send_message({
                    "type": "error",
                    "message": "语音合成失败"
                })
        else:
            # 没有识别到有效语音
            await session.send_message({
                "type": "no_speech",
                "message": "未识别到有效语音"
            })
            
    except Exception as e:
        logger.error(f"处理音频数据失败: {e}")
        await session.send_message({
            "type": "error",
            "message": f"处理音频失败: {str(e)}"
        })
    finally:
        session.is_processing = False

async def handle_text_message(session: ContinuousVoiceSession, message: dict, db: Session):
    """处理文本消息"""
    message_type = message.get("type")
    
    if message_type == "ping":
        await session.send_message({"type": "pong"})
    elif message_type == "get_status":
        await session.send_message({
            "type": "status",
            "session_id": session.session_id,
            "is_active": session.is_active,
            "is_processing": session.is_processing,
            "last_activity": session.last_activity.isoformat()
        })
    elif message_type == "end_session":
        session.is_active = False
        await session.send_message({
            "type": "session_ended",
            "message": "会话已结束"
        })

async def recognize_audio(audio_data: bytes) -> Optional[str]:
    """语音识别"""
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            temp_file_path = temp_file.name
            
            try:
                # 转换音频格式
                audio_segment = AudioSegment.from_file(io.BytesIO(audio_data), format="webm")
                audio_segment = audio_segment.set_frame_rate(16000).set_channels(1)
                audio_segment.export(temp_file_path, format="wav")
                
                # 语音识别
                recognizer = sr.Recognizer()
                with sr.AudioFile(temp_file_path) as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.3)
                    audio = recognizer.record(source)
                
                # 使用Google语音识别
                recognized_text = recognizer.recognize_google(audio, language='zh-CN')
                return recognized_text
                
            except sr.UnknownValueError:
                return None
            except Exception as e:
                logger.warning(f"语音识别失败: {e}")
                return None
            finally:
                # 清理临时文件
                if os.path.exists(temp_file_path):
                    try:
                        os.unlink(temp_file_path)
                    except Exception as e:
                        logger.warning(f"删除临时文件失败: {e}")
                        
    except Exception as e:
        logger.error(f"音频处理失败: {e}")
        return None

async def periodic_cleanup():
    """定期清理过期会话"""
    while True:
        try:
            await cleanup_expired_sessions()
            await asyncio.sleep(60)  # 每分钟清理一次
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"清理会话失败: {e}")
            await asyncio.sleep(60)