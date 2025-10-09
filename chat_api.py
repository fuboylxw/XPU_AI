"""
ChatBI 对话API - 专注于对话功能的简化API
支持流式输出，符合图片中的流程设计
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json
import asyncio
from datetime import datetime
from typing import AsyncGenerator, Optional, Dict, Any
import uuid
import sys
import os


# 在导入前确保nest_asyncio应用
import nest_asyncio
nest_asyncio.apply()

# 修改导入路径
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = current_dir  # 直接使用当前目录
sys.path.append(project_root)
print(f"项目根目录: {project_root}")
print(f"系统路径: {sys.path}")

# 尝试导入ChatBIAgent
try:
    from src.chatbi.agents.chat_agent import ChatBIAgent
    print("✅ 成功导入ChatBIAgent")
    # 初始化ChatBIAgent
    chat_agent = ChatBIAgent()
    print("✅ 成功初始化ChatBIAgent")
except Exception as e:
    print(f"❌ 初始化ChatBIAgent失败: {e}")
    import traceback
    traceback.print_exc()
    chat_agent = None


# 初始化FastAPI应用
app = FastAPI(
    title="ChatBI 对话API",
    description="专注于对话功能的简化API，支持流式输出",
    version="2.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求模型
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    stream: bool = True
    model_name: Optional[str] = None
    temperature: Optional[float] = 0.7


# API端点
@app.post("/api/v2/chat")
async def chat_endpoint(request: ChatRequest):
    """
    对话接口 - 支持流式和非流式输出（使用新的流式对话方法）
    
    流程：
    1. 接收用户消息
    2. 调用ChatBI代理处理
    3. 根据stream参数决定输出格式
    4. 返回响应（流式或完整）
    """
    print(f"💬 收到对话请求 - 会话ID: {request.conversation_id}")
    print(f"📝 用户消息: {request.message[:100]}...")
    print(f"🌊 流式输出: {request.stream}")
    
    try:
        # 根据stream参数决定输出方式
        async def generate():
            try:
                async for chunk in chat_agent.chat_stream(
                    message=request.message,
                    conversation_id=request.conversation_id,
                    model_name=request.model_name,
                    temperature=request.temperature
                ):
                    # 处理不同类型的chunk
                    if hasattr(chunk, 'model_dump_json'):
                        # 对于对象类型，直接使用model_dump_json
                        data = chunk.model_dump_json()
                        yield f"data: {data}\n\n"
                    else:
                        # 对于字符串类型，立即发送整个块
                        chunk_str = str(chunk)
                        if chunk_str:
                            char_data = json.dumps({"content": chunk_str}, ensure_ascii=False)
                            yield f"data: {char_data}\n\n"
                            # 添加短暂延迟以确保流式效果
                            await asyncio.sleep(0.01)
                # 发送结束信号
                yield "data: [DONE]\n\n"
            except Exception as e:
                error_msg = f"流式处理时出错: {str(e)}"
                print(f"❌ {error_msg}")
                yield f"data: {json.dumps({'error': error_msg, 'conversation_id': request.conversation_id})}\n\n"
            finally:
                yield "data: [DONE]\n\n"
        
        # 返回流式响应
        return StreamingResponse(
            generate(),
            media_type="text/event-stream"
        )
    except Exception as e:
        # 如果处理过程中出错，返回一个简单的响应
        error_msg = f"处理请求时出错: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            "success": False,
            "message": error_msg,
            "conversation_id": request.conversation_id,
            "timestamp": datetime.now().isoformat(),
            "model_used": request.model_name or "未知模型"
        }

@app.get("/api/v2/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "service": "ChatBI对话API",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
    }

@app.get("/")
async def root():
    """根端点"""
    return {
        "message": "ChatBI 对话API v2.0",
        "description": "专注于对话功能的简化API，支持流式输出",
        "endpoints": {
            "chat": "/api/v2/chat",
            "health": "/api/v2/health"
        },
        "features": [
            "支持流式输出",
            "支持会话管理",
            "支持模型配置",
            "支持温度参数调节"
        ],
        "usage": {
            "stream_chat": {
                "method": "POST",
                "endpoint": "/api/v2/chat",
                "request": {
                    "message": "用户消息",
                    "conversation_id": "会话ID",
                    "stream": True,
                    "model_name": "模型名称（可选）",
                    "temperature": "温度参数（可选）"
                },
                "response": "流式SSE输出"
            },
            "normal_chat": {
                "method": "POST", 
                "endpoint": "/api/v2/chat",
                "request": {
                    "message": "用户消息",
                    "conversation_id": "会话ID",
                    "stream": False
                },
                "response": "完整JSON响应"
            }
        },
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

# 启动服务器
if __name__ == "__main__":
    print("🚀 启动ChatBI对话API服务器...")
    print("📖 API文档: http://localhost:8003/docs")
    print("💬 对话接口: http://localhost:8003/api/v2/chat")
    print("🔍 健康检查: http://localhost:8003/health")
    import os
    os.system("start cmd /k uvicorn chat_api:app --host 0.0.0.0 --port 8003")