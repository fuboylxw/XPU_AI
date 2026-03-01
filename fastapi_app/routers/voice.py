"""
语音识别相关的API路由
"""
import os
import logging
import tempfile
import uuid
import io
import time
from pathlib import Path
from typing import Dict, Any, Generator, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends
from fastapi.responses import JSONResponse, StreamingResponse
import speech_recognition as sr
from pydub import AudioSegment
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

# 导入智能体
from src.Chatbot.core.providers import (
    get_chatbot_agent,
    get_tts_agent,
    get_voice_recognition_agent,
)

# 导入数据库相关
from fastapi_app.database import get_db
from fastapi_app.models import PhoneSession, PhoneConversationHistory

router = APIRouter()

# 配置日志
logger = logging.getLogger(__name__)

# 持续通话会话管理
class ContinuousCallSession:
    """持续通话会话管理类"""
    
    def __init__(self, session_id: str, user_id: str):
        self.session_id = session_id
        self.user_id = user_id
        self.state = "ACTIVE"
        self.context_history = []
        self.last_activity = datetime.now()
        self.phone_session_id = None
    
    def add_conversation(self, question: str, answer: str):
        """添加对话记录到上下文"""
        self.context_history.append({
            "question": question,
            "answer": answer,
            "timestamp": datetime.now()
        })
        self.last_activity = datetime.now()
        
        # 保持上下文历史在合理范围内（最近10轮对话）
        if len(self.context_history) > 10:
            self.context_history = self.context_history[-10:]
    
    def get_context_for_ai(self) -> str:
        """获取用于AI的上下文字符串"""
        if not self.context_history:
            return ""
        
        context_parts = []
        for item in self.context_history[-5:]:  # 最近5轮对话
            context_parts.append(f"用户: {item['question']}")
            context_parts.append(f"助手: {item['answer']}")
        
        return "\n".join(context_parts)
    
    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """检查会话是否过期"""
        return datetime.now() - self.last_activity > timedelta(minutes=timeout_minutes)

# 全局会话存储
continuous_sessions: Dict[str, ContinuousCallSession] = {}
# 会话级上一次识别文本缓存（用于空音频触发回复）
pending_phone_questions: Dict[str, str] = {}

def cleanup_expired_sessions():
    """清理过期的会话"""
    expired_sessions = [
        session_id for session_id, session in continuous_sessions.items()
        if session.is_expired()
    ]
    for session_id in expired_sessions:
        del continuous_sessions[session_id]
        logger.info(f"清理过期会话: {session_id}")

# 初始化TTS代理（优先使用本地ChatTTS，无API强制）
_initial_tts_agent = get_tts_agent()
if _initial_tts_agent:
    if getattr(_initial_tts_agent, "chattts", None):
        logger.info("TTS已启用本地ChatTTS")
    else:
        logger.info("TTS使用本地回退合成（无API密钥）")
else:
    logger.error("TTS代理初始化失败")


def _require_voice_recognition_agent():
    agent = get_voice_recognition_agent()
    if agent is None:
        raise HTTPException(status_code=503, detail="语音识别服务暂不可用")
    return agent


def _require_chat_agent():
    agent = get_chatbot_agent()
    if agent is None:
        raise HTTPException(status_code=503, detail="对话服务暂不可用")
    return agent


def _require_tts_agent():
    agent = get_tts_agent()
    if agent is None:
        raise HTTPException(status_code=503, detail="语音合成服务暂不可用")
    return agent


# 电话会话管理函数
def get_or_create_phone_session(user_id: str, db: Session) -> str:
    """获取或创建电话会话"""
    # 查找用户当前进行中的电话会话
    active_session = db.query(PhoneSession).filter(
        PhoneSession.user_id == user_id,
        PhoneSession.status == 1
    ).first()
    
    if active_session:
        logger.info(f"找到用户 {user_id} 的活跃会话: {active_session.id}")
        return active_session.id
    
    # 创建新的电话会话
    session_id = f"phone_session_{uuid.uuid4().hex[:12]}"
    new_session = PhoneSession(
        id=session_id,
        user_id=user_id,
        status=1
    )
    db.add(new_session)
    db.commit()
    logger.info(f"为用户 {user_id} 创建新的电话会话: {session_id}")
    return session_id


def end_phone_session(session_id: str, db: Session):
    """结束电话会话"""
    session = db.query(PhoneSession).filter(PhoneSession.id == session_id).first()
    if session:
        session.status = 0
        session.session_end = datetime.now()
        db.commit()
        logger.info(f"结束电话会话: {session_id}")


def get_phone_conversation_history(session_id: str, db: Session, limit: int = 10) -> list:
    """获取电话对话历史"""
    history = db.query(PhoneConversationHistory).filter(
        PhoneConversationHistory.session_id == session_id
    ).order_by(PhoneConversationHistory.created_at.desc()).limit(limit).all()
    
    # 按时间正序返回
    return list(reversed(history))


def save_phone_conversation(session_id: str, user_id: str, question: str, answer: str, db: Session):
    """保存电话对话记录"""
    conversation = PhoneConversationHistory(
        session_id=session_id,
        user_id=user_id,
        question=question,
        answer=answer
    )
    db.add(conversation)
    db.commit()
    logger.info(f"保存电话对话记录到会话 {session_id}")


@router.post("/voice/phone_session/end/")
async def end_phone_call_session(
    user_id: str = Form(...),
    db: Session = Depends(get_db)
) -> JSONResponse:
    """
    结束电话会话接口
    用于前端主动结束电话通话时调用
    """
    try:
        # 查找用户当前活跃的电话会话
        active_session = db.query(PhoneSession).filter(
            PhoneSession.user_id == user_id,
            PhoneSession.status == 1
        ).first()
        
        if active_session:
            end_phone_session(active_session.id, db)
            return JSONResponse(
                content={
                    "success": True,
                    "message": "电话会话已结束",
                    "session_id": active_session.id
                }
            )
        else:
            return JSONResponse(
                content={
                    "success": False,
                    "message": "没有找到活跃的电话会话"
                }
            )
    
    except Exception as e:
        logger.error(f"结束电话会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"结束电话会话失败: {str(e)}")


@router.post("/phone-call/end")
async def end_phone_call(
    request_data: dict,
    db: Session = Depends(get_db)
) -> JSONResponse:
    """
    结束电话通话接口 - 匹配前端请求路径
    用于前端挂断电话时调用
    """
    try:
        # 从请求数据中获取conversation_id（如果有的话）
        conversation_id = request_data.get('conversation_id', 'default')
        
        # 查找所有活跃的电话会话并结束它们
        active_sessions = db.query(PhoneSession).filter(
            PhoneSession.status == 1
        ).all()
        
        ended_sessions = 0
        for session in active_sessions:
            end_phone_session(session.id, db)
            ended_sessions += 1
        
        return JSONResponse(
            content={
                "success": True,
                "message": f"已结束 {ended_sessions} 个活跃的电话会话",
                "conversation_id": conversation_id
            }
        )
    
    except Exception as e:
        logger.error(f"结束电话通话失败: {e}")
        raise HTTPException(status_code=500, detail=f"结束电话通话失败: {str(e)}")


@router.get("/voice/phone_session/history/{user_id}")
async def get_phone_session_history(
    user_id: str,
    limit: int = 20,
    db: Session = Depends(get_db)
) -> JSONResponse:
    """
    获取用户的电话对话历史
    """
    try:
        # 获取用户最近的电话会话
        recent_sessions = db.query(PhoneSession).filter(
            PhoneSession.user_id == user_id
        ).order_by(PhoneSession.created_at.desc()).limit(5).all()
        
        history_data = []
        for session in recent_sessions:
            # 获取每个会话的对话记录
            conversations = db.query(PhoneConversationHistory).filter(
                PhoneConversationHistory.session_id == session.id
            ).order_by(PhoneConversationHistory.created_at.asc()).all()
            
            session_data = {
                "session_id": session.id,
                "session_start": session.session_start.isoformat(),
                "session_end": session.session_end.isoformat() if session.session_end else None,
                "status": session.status,
                "conversations": [
                    {
                        "question": conv.question,
                        "answer": conv.answer,
                        "created_at": conv.created_at.isoformat()
                    }
                    for conv in conversations
                ]
            }
            history_data.append(session_data)
        
        return JSONResponse(
            content={
                "success": True,
                "data": history_data
            }
        )
    
    except Exception as e:
        logger.error(f"获取电话会话历史失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取电话会话历史失败: {str(e)}")


@router.post("/voice/recognize/")
async def recognize_speech(audio_file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    语音识别接口
    接收音频文件，返回识别的文本结果
    优先使用Google语音识别API，失败时备选百度语音识别API
    """
    try:
        # 验证文件类型
        if not audio_file.content_type or not audio_file.content_type.startswith('audio/'):
            raise HTTPException(status_code=400, detail="请上传音频文件")
        
        audio_data = await audio_file.read()
        
        fd, temp_file_path = tempfile.mkstemp(suffix='.wav')
        os.close(fd)
        try:
            if audio_file.content_type == 'audio/webm':
                audio_segment = AudioSegment.from_file(io.BytesIO(audio_data), format="webm")
                audio_segment = audio_segment.set_frame_rate(16000).set_channels(1)
                audio_segment.export(temp_file_path, format="wav")
            else:
                with open(temp_file_path, 'wb') as f:
                    f.write(audio_data)
                
                # 第一步：优先使用Whisper本地模型识别
                whisper_result = _require_voice_recognition_agent().recognize_speech_whisper(temp_file_path)
                if whisper_result and whisper_result.get("success"):
                    logger.info(f"Whisper语音识别成功: {whisper_result['text']}")
                    return JSONResponse(
                        status_code=200,
                        content={
                            "success": True,
                            "text": whisper_result["text"].strip(),
                            "message": "Whisper语音识别成功",
                            "confidence": whisper_result.get("confidence", 1.0),
                            "provider": "whisper"
                        }
                    )

                # 第二步：尝试使用Google语音识别
                google_result = None
                try:
                    logger.info("尝试使用Google语音识别")
                    recognizer = sr.Recognizer()
                    with sr.AudioFile(temp_file_path) as source:
                        recognizer.adjust_for_ambient_noise(source, duration=0.5)
                        audio = recognizer.record(source)
                    recognized_text = recognizer.recognize_google(audio, language='zh-CN')
                    logger.info(f"Google语音识别成功: {recognized_text}")
                    return JSONResponse(
                        status_code=200,
                        content={
                            "success": True,
                            "text": recognized_text.strip(),
                            "message": "Google语音识别成功",
                            "confidence": 1.0,
                            "provider": "google"
                        }
                    )
                except sr.UnknownValueError:
                    logger.warning("Google语音识别无法理解音频，尝试百度识别")
                    google_result = "无法理解音频"
                except sr.RequestError as e:
                    logger.warning(f"Google语音识别服务错误: {e}，尝试百度识别")
                    google_result = f"服务错误: {e}"
                except Exception as e:
                    logger.warning(f"Google语音识别异常: {e}，尝试百度识别")
                    google_result = f"识别异常: {e}"
                
                # 第三步：Google识别失败，使用百度语音识别作为备选
                logger.info("Google识别失败，使用百度语音识别作为备选")
                
                # 转换WAV为PCM格式（百度API需要）
                pcm_filename = temp_file_path.replace('.wav', '.pcm')
                convert_result = _require_voice_recognition_agent().convert_to_pcm(temp_file_path, pcm_filename)
                
                if not convert_result['success']:
                    logger.error(f"音频格式转换失败: {convert_result['error']}")
                    return JSONResponse(
                        status_code=200,
                        content={
                            "success": False,
                            "text": "",
                            "message": f"Google识别失败({google_result})，音频格式转换失败: {convert_result['error']}",
                            "errors": [f"Google: {google_result}", f"转换: {convert_result['error']}"],
                            "provider": "fallback_failed"
                        }
                    )
                
                # 使用百度语音识别
                recognition_result = _require_voice_recognition_agent().recognize_speech(pcm_filename)
                
                # 清理PCM临时文件
                try:
                    if os.path.exists(pcm_filename):
                        os.unlink(pcm_filename)
                        logger.info(f"成功删除PCM临时文件: {pcm_filename}")
                except Exception as e:
                    logger.warning(f"删除PCM临时文件失败: {pcm_filename}, 错误: {e}")
                
                if recognition_result['success']:
                    logger.info(f"百度语音识别成功: {recognition_result['text']}")
                    return JSONResponse(
                        status_code=200,
                        content={
                            "success": True,
                            "text": recognition_result['text'].strip(),
                            "message": f"Google识别失败({google_result})，百度语音识别成功",
                            "confidence": recognition_result.get('confidence', 1.0),
                            "provider": "baidu_fallback"
                        }
                    )
                else:
                    logger.error(f"百度语音识别也失败: {recognition_result['error']}")
                    return JSONResponse(
                        status_code=200,
                        content={
                            "success": False,
                            "text": "",
                            "message": f"Google和百度语音识别都失败",
                            "errors": [f"Google: {google_result}", f"百度: {recognition_result['error']}"],
                            "provider": "both_failed"
                        }
                    )
                
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    logger.info(f"成功删除语音识别临时文件: {temp_file_path}")
                except Exception as e:
                    try:
                        import time
                        time.sleep(0.3)
                        os.unlink(temp_file_path)
                        logger.info(f"延迟删除语音识别临时文件成功: {temp_file_path}")
                    except Exception as e2:
                        logger.error(f"强制删除语音识别临时文件也失败: {temp_file_path}, 错误: {e2}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"语音识别处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"语音识别处理失败: {str(e)}")

@router.get("/voice/status/")
async def get_voice_recognition_status() -> Dict[str, Any]:
    """
    获取语音识别服务状态
    """
    try:
        # 检查语音识别依赖是否可用
        status = {
            "service_available": True,
            "engines": {
                "google": True,  # 需要网络连接
                "baidu": False,  # 需要API密钥配置
                "sphinx": False  # 需要安装pocketsphinx
            },
            "supported_formats": ["audio/wav", "audio/webm", "audio/mp3", "audio/ogg"],
            "max_file_size": "10MB",
            "languages": ["zh-CN", "en-US"]
        }
        
        # 检查Sphinx是否可用
        try:
            import pocketsphinx
            status["engines"]["sphinx"] = True
        except ImportError:
            pass
        
        return status
        
    except Exception as e:
        logger.error(f"获取语音识别状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取语音识别状态失败: {str(e)}")


@router.post("/voice/phone_call/")
async def voice_phone_call_async(audio_file: UploadFile = File(...)) -> StreamingResponse:
    """
    异步语音电话接口 - 使用异步流式语音合成
    """
    try:
        # 验证文件类型
        if not audio_file.content_type or not audio_file.content_type.startswith('audio/'):
            raise HTTPException(status_code=400, detail="请上传音频文件")
        
        # 读取上传的音频文件
        audio_data = await audio_file.read()
        
        if len(audio_data) == 0:
            raise HTTPException(status_code=400, detail="音频文件为空")
        
        logger.info(f"开始处理异步语音电话请求，音频大小: {len(audio_data)} bytes")
        
        # 语音识别部分（同步）
        temp_file_path = None
        try:
            fd, temp_file_path = tempfile.mkstemp(suffix='.wav')
            os.close(fd)
            if audio_file.content_type == 'audio/webm':
                audio_segment = AudioSegment.from_file(io.BytesIO(audio_data), format="webm")
                audio_segment = audio_segment.set_frame_rate(16000).set_channels(1)
                audio_segment.export(temp_file_path, format="wav")
            else:
                with open(temp_file_path, 'wb') as f:
                    f.write(audio_data)
                
                if len(audio_data) == 0:
                    recognized_text = pending_phone_questions.get("async", "")
                else:
                    whisper_result = _require_voice_recognition_agent().recognize_speech_whisper(temp_file_path)
                    if whisper_result and whisper_result.get("success"):
                        recognized_text = whisper_result["text"].strip()
                        pending_phone_questions["async"] = recognized_text
                        logger.info(f"异步Whisper语音识别成功: {recognized_text}")
                    else:
                        recognized_text = "抱歉，我没有听清楚您说的话。"
                
                # 调用聊天智能体
                chat_response = await _require_chat_agent().answer_question(
                    question=recognized_text,
                    user_id="phone_user_async",
                    user_role="guest",
                    conversation_id=f"phone_call_async_{uuid.uuid4().hex[:8]}",
                    phone_mode=True,
                    fast_response=True
                )
                
                response_text = chat_response.get("answer", "抱歉，我无法回答您的问题。") if chat_response.get("success") else "系统暂时无法处理您的请求。"
                
                # 异步流式语音合成
                async def generate_async_audio_stream():
                    """异步生成音频流"""
                    try:
                        logger.info("开始异步生成语音流")
                        
                        async for audio_chunk in _require_tts_agent().synthesize_speech_stream_async(
                            text=response_text,
                            chunk_size=1024
                        ):
                            if audio_chunk:
                                yield audio_chunk
                        
                        logger.info("异步语音流生成完成")
                        
                    except Exception as e:
                        logger.error(f"异步生成语音流失败: {e}")
                        yield b''
                
                return StreamingResponse(
                    generate_async_audio_stream(),
                    media_type="audio/wav",
                    headers={
                        "Content-Disposition": "attachment; filename=phone_response_async.wav",
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Recognized-Text-Base64": __import__('base64').b64encode(recognized_text.encode('utf-8')).decode('ascii'),
                        "X-Response-Text-Base64": __import__('base64').b64encode(response_text.encode('utf-8')).decode('ascii')
                    }
                )
                
        except Exception as inner_e:
            logger.error(f"异步语音处理内部错误: {inner_e}")
            raise
        finally:
            # 确保临时文件被删除
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    logger.info(f"成功删除异步临时文件: {temp_file_path}")
                except Exception:
                    try:
                        import time
                        time.sleep(0.3)
                        os.unlink(temp_file_path)
                        logger.info(f"延迟删除异步临时文件成功: {temp_file_path}")
                    except Exception as e2:
                        logger.error(f"强制删除异步临时文件也失败: {temp_file_path}, 错误: {e2}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"异步语音电话处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"异步语音电话处理失败: {str(e)}")


@router.get("/voice/phone_call/status/")
async def get_phone_call_status() -> Dict[str, Any]:
    """
    获取语音电话服务状态
    """
    try:
        # 简化状态检查，避免长时间等待
        status = {
            "service_available": True,
            "voice_recognition": {
                "available": True,  # 简化检查，避免设备检测延迟
                "devices_count": 1,
                "default_device": 0
            },
            "chat_agent": {
                "available": True,
                "phone_mode_supported": True,
                "fast_response_supported": True
            },
            "text_to_speech": {
                "available": get_tts_agent() is not None,
                "supported_formats": ["mp3-16k", "wav-16k"],
                "stream_supported": True,
                "async_stream_supported": True
            },
            "endpoints": {
                "/voice/phone_call/": "同步语音电话接口",
                "/voice/phone_call_async/": "异步语音电话接口"
            },
            "supported_audio_formats": ["audio/wav", "audio/webm", "audio/mp3", "audio/ogg"],
            "response_format": "audio/wav",
            "features": [
                "语音识别 (Google Speech Recognition)",
                "智能对话 (ChatAgent with phone mode)",
                "语音合成 (TTS with streaming)",
                "流式音频响应",
                "异步处理支持"
            ]
        }
        
        return status
        
    except Exception as e:
        logger.error(f"获取语音电话状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取语音电话状态失败: {str(e)}")


# 统一的持续语音监听接口
@router.post("/continuous_call/")
async def continuous_call_handler(
    action: str = Form(...),  # "start", "process", "end"
    user_id: str = Form("continuous_user"),
    session_id: str = Form(None),
    audio_file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    """
    统一的持续语音监听接口
    action: "start" - 开始会话, "process" - 处理音频, "end" - 结束会话
    """
    try:
        if action == "start":
            # 开始持续语音监听会话
            cleanup_expired_sessions()
            
            # 创建新的持续通话会话
            new_session_id = f"continuous_{uuid.uuid4().hex[:12]}"
            continuous_session = ContinuousCallSession(new_session_id, user_id)
            
            # 创建或获取电话会话
            phone_session_id = get_or_create_phone_session(user_id, db)
            continuous_session.phone_session_id = phone_session_id
            
            # 存储会话
            continuous_sessions[new_session_id] = continuous_session
            
            logger.info(f"开始持续语音监听会话: {new_session_id}, 电话会话: {phone_session_id}")
            
            return JSONResponse(
                content={
                    "success": True,
                    "session_id": new_session_id,
                    "phone_session_id": phone_session_id,
                    "state": continuous_session.state,
                    "message": "持续语音监听会话已开始"
                }
            )
            
        elif action == "process":
            # 处理持续语音监听中的音频片段
            if not session_id:
                raise HTTPException(status_code=400, detail="处理音频需要提供session_id")
            
            if not audio_file:
                raise HTTPException(status_code=400, detail="处理音频需要提供音频文件")
            
            # 验证会话
            if session_id not in continuous_sessions:
                raise HTTPException(status_code=404, detail="持续语音会话不存在")
            
            continuous_session = continuous_sessions[session_id]
            
            # 检查会话是否过期
            if continuous_session.is_expired():
                del continuous_sessions[session_id]
                raise HTTPException(status_code=410, detail="持续语音会话已过期")
            
            # 验证文件类型
            if not audio_file.content_type or not audio_file.content_type.startswith('audio/'):
                raise HTTPException(status_code=400, detail="请上传音频文件")
            
            # 读取音频数据
            audio_data = await audio_file.read()
            if len(audio_data) == 0:
                logger.warning(f"会话 {session_id} 收到空音频，跳过处理")
                # 返回空音频响应
                def empty_audio_stream():
                    yield b''
                
                return StreamingResponse(
                    empty_audio_stream(),
                    media_type="audio/mpeg",
                    headers={
                        "X-Session-ID": session_id,
                        "X-Status": "empty_audio",
                        "X-Message": "音频为空，跳过处理"
                    }
                )
            
            logger.info(f"处理持续语音会话 {session_id} 的音频片段，大小: {len(audio_data)} bytes")
            
            # 语音识别
            temp_file_path = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                    temp_file_path = temp_file.name
                    
                    # 音频格式转换
                    if audio_file.content_type == 'audio/webm':
                        audio_segment = AudioSegment.from_file(io.BytesIO(audio_data), format="webm")
                        audio_segment = audio_segment.set_frame_rate(16000).set_channels(1)
                        audio_segment.export(temp_file_path, format="wav")
                    else:
                        temp_file.write(audio_data)
                    
                    # 语音识别
                    recognizer = sr.Recognizer()
                    with sr.AudioFile(temp_file_path) as source:
                        recognizer.adjust_for_ambient_noise(source, duration=0.3)
                        audio = recognizer.record(source)
                    
                    recognized_text = None
                    try:
                        recognized_text = recognizer.recognize_google(audio, language='zh-CN')
                        logger.info(f"持续语音识别成功: {recognized_text}")
                    except sr.UnknownValueError:
                        logger.info("持续语音识别：检测到静音或无法理解的音频")
                        def silent_audio_stream():
                            yield b''
                        
                        return StreamingResponse(
                            silent_audio_stream(),
                            media_type="audio/mpeg",
                            headers={
                                "X-Session-ID": session_id,
                                "X-Status": "silent",
                                "X-Message": "检测到静音"
                            }
                        )
                    except Exception as e:
                        logger.warning(f"持续语音识别异常: {e}")
                        recognized_text = "语音识别出现问题，请重新尝试。"
                    
                    # 如果识别到文本，进行AI处理
                    if recognized_text and recognized_text.strip():
                        # 获取上下文
                        context_str = continuous_session.get_context_for_ai()
                        
                        # 构建完整问题
                        if context_str:
                            full_question = f"对话历史:\n{context_str}\n\n当前问题: {recognized_text}"
                        else:
                            full_question = recognized_text
                        
                        # 调用聊天智能体
                        logger.info(f"调用聊天智能体处理持续语音: {recognized_text}")
                        chat_response = await _require_chat_agent().answer_question(
                            question=full_question,
                            user_id=continuous_session.user_id,
                            user_role="guest",
                            conversation_id=continuous_session.phone_session_id,
                            phone_mode=True,
                            fast_response=True
                        )
                        
                        if chat_response.get("success", False):
                            response_text = chat_response.get("answer", "抱歉，我无法回答您的问题。")
                        else:
                            response_text = "抱歉，系统暂时无法处理您的请求。"
                        
                        logger.info(f"持续语音AI回复: {response_text[:100]}...")
                        
                        # 添加到会话上下文
                        continuous_session.add_conversation(recognized_text, response_text)
                        
                        # 保存到数据库
                        if continuous_session.phone_session_id:
                            save_phone_conversation(
                                continuous_session.phone_session_id,
                                continuous_session.user_id,
                                recognized_text,
                                response_text,
                                db
                            )
                        
                        # 生成语音响应
                        def generate_continuous_audio_stream() -> Generator[bytes, None, None]:
                            """生成持续语音的音频流"""
                            try:
                                logger.info("开始生成持续语音流")
                                
                                for audio_chunk in _require_tts_agent().synthesize_speech_stream(
                                    text=response_text,
                                    chunk_size=1024,
                                    format='mp3-16k',
                                    speed=6,
                                    volume=7
                                ):
                                    if audio_chunk:
                                        yield audio_chunk
                                
                                logger.info("持续语音流生成完成")
                                
                            except Exception as e:
                                logger.error(f"生成持续语音流失败: {e}")
                                yield b''
                        
                        return StreamingResponse(
                            generate_continuous_audio_stream(),
                            media_type="audio/mpeg",
                            headers={
                                "Content-Disposition": "attachment; filename=continuous_response.mp3",
                                "Cache-Control": "no-cache",
                                "Connection": "keep-alive",
                                "X-Session-ID": session_id,
                                "X-Phone-Session-ID": continuous_session.phone_session_id,
                                "X-Recognized-Text": recognized_text[:100].encode('utf-8', errors='ignore').decode('latin-1', errors='ignore'),
                                "X-Response-Text": response_text[:100].encode('utf-8', errors='ignore').decode('latin-1', errors='ignore'),
                                "X-Status": "processed"
                            }
                        )
                    else:
                        # 没有识别到有效文本
                        def empty_response_stream():
                            yield b''
                        
                        return StreamingResponse(
                            empty_response_stream(),
                            media_type="audio/mpeg",
                            headers={
                                "X-Session-ID": session_id,
                                "X-Status": "no_text",
                                "X-Message": "未识别到有效文本"
                            }
                        )
                    
            finally:
                # 清理临时文件
                if temp_file_path and os.path.exists(temp_file_path):
                    try:
                        os.unlink(temp_file_path)
                        logger.debug(f"删除持续语音临时文件: {temp_file_path}")
                    except Exception as e:
                        logger.warning(f"删除持续语音临时文件失败: {e}")
            
        elif action == "end":
            # 结束持续语音监听会话
            if not session_id:
                raise HTTPException(status_code=400, detail="结束会话需要提供session_id")
            
            if session_id not in continuous_sessions:
                return JSONResponse(
                    content={
                        "success": False,
                        "message": "持续语音会话不存在或已结束"
                    }
                )
            
            continuous_session = continuous_sessions[session_id]
            
            # 结束电话会话
            if continuous_session.phone_session_id:
                end_phone_session(continuous_session.phone_session_id, db)
            
            # 移除持续会话
            del continuous_sessions[session_id]
            
            logger.info(f"结束持续语音监听会话: {session_id}")
            
            return JSONResponse(
                content={
                    "success": True,
                    "message": "持续语音监听会话已结束",
                    "session_id": session_id,
                    "phone_session_id": continuous_session.phone_session_id
                }
            )
        
        else:
            raise HTTPException(status_code=400, detail="无效的action参数，支持: start, process, end")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"持续语音监听操作失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"持续语音监听操作失败: {str(e)}")


@router.get("/voice/continuous_call/status/{session_id}")
async def get_continuous_call_status(session_id: str) -> JSONResponse:
    """
    获取持续语音监听会话状态
    """
    try:
        if session_id not in continuous_sessions:
            return JSONResponse(
                content={
                    "success": False,
                    "exists": False,
                    "message": "持续语音会话不存在"
                }
            )
        
        continuous_session = continuous_sessions[session_id]
        
        # 检查是否过期
        if continuous_session.is_expired():
            del continuous_sessions[session_id]
            return JSONResponse(
                content={
                    "success": False,
                    "exists": False,
                    "expired": True,
                    "message": "持续语音会话已过期"
                }
            )
        
        return JSONResponse(
            content={
                "success": True,
                "exists": True,
                "session_id": session_id,
                "user_id": continuous_session.user_id,
                "state": continuous_session.state,
                "phone_session_id": continuous_session.phone_session_id,
                "last_activity": continuous_session.last_activity.isoformat(),
                "conversation_count": len(continuous_session.context_history),
                "message": "持续语音会话正常"
            }
        )
        
    except Exception as e:
        logger.error(f"获取持续语音会话状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取持续语音会话状态失败: {str(e)}")


@router.get("/voice/continuous_call/sessions/")
async def list_continuous_sessions() -> JSONResponse:
    """
    列出所有活跃的持续语音监听会话（用于调试）
    """
    try:
        # 清理过期会话
        cleanup_expired_sessions()
        
        sessions_info = []
        for session_id, session in continuous_sessions.items():
            sessions_info.append({
                "session_id": session_id,
                "user_id": session.user_id,
                "state": session.state,
                "phone_session_id": session.phone_session_id,
                "last_activity": session.last_activity.isoformat(),
                "conversation_count": len(session.context_history)
            })
        
        return JSONResponse(
            content={
                "success": True,
                "active_sessions": len(sessions_info),
                "sessions": sessions_info
            }
        )
        
    except Exception as e:
        logger.error(f"列出持续语音会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"列出持续语音会话失败: {str(e)}")
