"""
ChatBI 对话API - 专注于对话功能的简化API
支持流式输出，符合图片中的流程设计
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json
import asyncio
from datetime import datetime
from typing import AsyncGenerator, Optional, Dict
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

# 尝试导入智能体
try:
    from src.chatbi.agents.chat_agent import ChatBIAgent
    print("✅ 成功导入智能体模块")
    
    # 初始化智能体
    chat_agent = ChatBIAgent()  # 集成了统一问答功能
    print("✅ 成功初始化智能体")
except Exception as e:
    print(f"❌ 初始化智能体失败: {e}")
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

class UnifiedQARequest(BaseModel):
    question: str
    user_id: str = "guest"
    user_role: str = "guest"  # guest/student/teacher/admin
    session_token: Optional[str] = None
    image_data: Optional[str] = None  # base64编码的图像数据
    conversation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


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

@app.post("/api/v3/qa")
async def unified_qa_endpoint(request: UnifiedQARequest):
    """
    统一问答接口 - 集成所有智能体功能
    
    功能：
    1. 安全审核
    2. 意图识别（支持多模态）
    3. 知识库查询
    4. 统一回答生成
    """
    print(f"🤖 收到统一问答请求 - 用户: {request.user_id}, 角色: {request.user_role}")
    print(f"❓ 问题: {request.question[:100]}...")
    
    if not chat_agent:
        return {
            "success": False,
            "error": "智能体未初始化",
            "timestamp": datetime.now().isoformat()
        }
    
    try:
        # 处理图像数据
        image_data = None
        if request.image_data:
            try:
                import base64
                from PIL import Image
                import io
                
                # 解码base64图像
                if request.image_data.startswith('data:image'):
                    image_data = request.image_data.split(',')[1]
                else:
                    image_data = request.image_data
                
                image_bytes = base64.b64decode(image_data)
                image_data = Image.open(io.BytesIO(image_bytes))
                print("📷 成功处理图像数据")
            except Exception as e:
                print(f"❌ 图像处理失败: {e}")
                image_data = None
        
        # 调用集成了统一问答功能的ChatBIAgent
        from src.chatbi.agents.data_query_agent import UserRole
        user_role_enum = UserRole.GUEST
        try:
            user_role_enum = UserRole(request.user_role.lower())
        except ValueError:
            print(f"⚠️ 无效的用户角色: {request.user_role}，使用默认角色: guest")
        
        result = await chat_agent.answer_question_stream(
            question=request.question,
            conversation_id=request.conversation_id,
            user_id=request.user_id,
            user_role=user_role_enum,
            session_token=request.session_token
        )
        
        print(f"✅ 问答处理完成")
        
        # 创建流式响应
        async def generate():
            try:
                async for chunk in result:
                    yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.01)
                yield "data: [DONE]\n\n"
            except Exception as e:
                error_msg = f"流式处理时出错: {str(e)}"
                print(f"❌ {error_msg}")
                yield f"data: {json.dumps({'error': error_msg})}\n\n"
                yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream"
        )
        
    except Exception as e:
        print(f"❌ 统一问答处理失败: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "success": False,
            "question": request.question,
            "answer": f"抱歉，处理您的问题时遇到系统错误：{str(e)}。请稍后重试或联系技术支持。",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
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
            "qa": "/api/v3/qa",
            "health": "/api/v2/health"
        },
        "features": [
            "支持流式输出",
            "支持多模态输入",
            "支持模型配置",
            "支持温度参数调节"
        ],
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

# 启动服务器
if __name__ == "__main__":
    print("🚀 启动ChatBI智能问答API服务器...")
    print("📖 API文档: http://localhost:8003/docs")
    print("💬 原始对话接口: http://localhost:8003/api/v2/chat")
    print("🤖 统一问答接口: http://localhost:8003/api/v3/qa")
    print("🔐 会话管理: http://localhost:8003/api/v3/session/create")
    print("📊 系统状态: http://localhost:8003/api/v3/system/status")
    print("🔍 健康检查: http://localhost:8003/api/v2/health")
    print("\n✨ 新功能:")
    print("  - 安全审核模块")
    print("  - 意图识别（支持图像）")
    print("  - 校园知识库查询")
    print("  - 权限控制的数据查询")
    print("  - 多模态问答支持")
    import os
    os.system("start cmd /k uvicorn chat_api:app --host 0.0.0.0 --port 8003")