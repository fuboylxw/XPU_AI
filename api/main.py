"""
FastAPI应用主文件
提供对话功能的RESTful API接口
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
import json
from typing import Optional
import uvicorn
from pathlib import Path
import sys

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from api.models import (
    ChatRequest, ChatResponse, StreamChatResponse,
    DocumentUploadRequest, DocumentUploadResponse,
    DocumentSearchRequest, DocumentSearchResponse,
    DocumentSummaryResponse, HealthResponse, ErrorResponse,
    WebSearchRequest, WebSearchResponse, ApiResponse
)
from api.service_factory import get_service_factory, initialize_services, cleanup_services, get_chat_service
from api.middleware import ExceptionHandlerMiddleware, RateLimitMiddleware, RequestLoggingMiddleware, SecurityMiddleware
from api.validators import validate_chat, validate_upload, validate_search, validate_session
from src.config.settings import Settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化服务
    try:
        await initialize_services()
        print("✅ 服务工厂初始化成功")
    except Exception as e:
        print(f"❌ 服务初始化失败: {e}")
        raise
    
    yield
    
    # 关闭时清理资源
    try:
        await cleanup_services()
        print("✅ 服务清理完成")
    except Exception as e:
        print(f"❌ 服务清理失败: {e}")

# 创建FastAPI应用
app = FastAPI(
    title="新生信息问答API",
    description="基于AI的学校信息问答系统API接口",
    version="1.0.0",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加中间件
settings = Settings()
app.add_middleware(SecurityMiddleware, settings=settings)
app.add_middleware(RequestLoggingMiddleware, settings=settings)
app.add_middleware(RateLimitMiddleware, settings=settings)
app.add_middleware(ExceptionHandlerMiddleware, settings=settings)

async def get_service():
    """获取聊天服务实例"""
    try:
        return await get_chat_service()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"服务获取失败: {str(e)}"
        )

@app.get("/", response_model=dict)
async def root():
    """根路径"""
    return {
        "message": "新生信息问答API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", response_model=ApiResponse[HealthResponse])
async def health_check():
    """健康检查"""
    try:
        service = get_service()
        components = {
            "chat_service": "healthy",
            "document_manager": "healthy",
            "llm_client": "healthy"
        }
        
        response = HealthResponse(
            status="healthy",
            version="1.0.0",
            components=components
        )
        return ApiResponse.success_response(response, "系统运行正常")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"服务不健康: {str(e)}"
        )

# 移除非流式对话接口，统一使用流式接口

@app.post("/chat/stream")
@validate_chat
async def chat_stream(request: ChatRequest):
    """流式对话接口 - 支持单条消息和多轮对话"""
    try:
        # 验证请求数据
        if not request.message and not request.messages:
            raise HTTPException(
                status_code=400,
                detail="必须提供 message 或 messages 参数"
            )
        
        if request.message and request.messages:
            raise HTTPException(
                status_code=400,
                detail="不能同时提供 message 和 messages 参数"
            )
        
        async def generate_stream():
            service = await get_service()
            async for chunk in service.chat_stream(request):
                # 将响应转换为JSON格式的服务器发送事件
                data = chunk.model_dump_json()
                yield f"data: {data}\n\n"
            
            # 发送结束信号
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"流式对话处理失败: {str(e)}"
        )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理器"""
    return ErrorResponse(
        error="InternalServerError",
        message="服务器内部错误",
        detail=str(exc)
    )

if __name__ == "__main__":
    # 开发环境启动
    settings = Settings()
    uvicorn.run(
        "api.main:app",
        host="localhost",
        port=8316,
        reload=True,
        log_level="info"
    )