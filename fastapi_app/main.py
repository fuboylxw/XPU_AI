"""
FastAPI主应用文件
"""
import os
import sys
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi_app.routers import config, chat, auth, tts, upload, tasks
try:
    from fastapi_app.routers import voice
    VOICE_ROUTER_AVAILABLE = True
except Exception as e:
    logging.warning(f"语音路由不可用: {e}")
    VOICE_ROUTER_AVAILABLE = False
from fastapi_app.database import engine, Base
from sqlalchemy import text

# 导入全局初始化器
GLOBAL_INITIALIZER_AVAILABLE = False
try:
    from src.Chatbot.utils.global_initializer import initialize_system, shutdown_system, is_system_initialized
    GLOBAL_INITIALIZER_AVAILABLE = True
except ImportError as e:
    logging.warning(f"全局初始化器不可用: {e}")


# 导入对话标题智能体（可选）
try:
    from src.Chatbot.agents.conversation_title_agent import title_agent
    TITLE_AGENT_AVAILABLE = True
except Exception as e:
    logging.warning(f"对话标题智能体不可用: {e}")
    TITLE_AGENT_AVAILABLE = False

# 导入自动标题生成服务（可选）
try:
    from src.Chatbot.services.auto_title_service import (
        start_auto_title_service,
        stop_auto_title_service,
        auto_title_service,
    )
    AUTO_TITLE_SERVICE_AVAILABLE = True
except Exception as e:
    logging.warning(f"自动标题生成服务不可用: {e}")
    AUTO_TITLE_SERVICE_AVAILABLE = False

# 创建数据库表与迁移在启动时加锁执行，避免并发 DDL 冲突

# 创建FastAPI应用实例
app = FastAPI(
    title="ChatBot API",
    description="基于FastAPI的聊天机器人API",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(config.router, prefix="/api", tags=["config"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(tts.router, prefix="/api", tags=["tts"])
app.include_router(upload.router, prefix="/api", tags=["upload"])
if VOICE_ROUTER_AVAILABLE:
    app.include_router(voice.router, prefix="/api", tags=["voice"])
app.include_router(tasks.router, prefix="/api", tags=["tasks"])
# app.include_router(websocket_voice.router, prefix="/api", tags=["websocket_voice"])  # 临时注释，缺少pyaudio依赖


# 启动事件 - 预加载系统组件
@app.on_event("startup")
async def startup_event():
    """应用启动时的预加载事件"""
    print("🚀 正在启动ChatBot系统...")
    try:
        with engine.connect() as conn:
            lock = conn.execute(text("SELECT GET_LOCK(:name, :timeout)"), {"name": "chatbot_schema_migration", "timeout": 0}).scalar()
            if lock == 1:
                try:
                    Base.metadata.create_all(bind=engine)
                    # 执行一次数据库迁移
                    try:
                        tasks._ensure_db_constraints(conn)
                    except Exception as e:
                        logging.warning(f"数据库迁移失败: {e}")
                finally:
                    conn.execute(text("SELECT RELEASE_LOCK(:name)"), {"name": "chatbot_schema_migration"})
    except Exception as e:
        logging.warning(f"启动时数据库初始化失败: {e}")
    
    if GLOBAL_INITIALIZER_AVAILABLE:
        try:
            print("📦 开始预加载系统组件...")
            success = await initialize_system()
            if success:
                print("✅ 系统组件预加载完成")
                print("🎯 ChatBot已就绪，所有组件已预加载")
            else:
                print("⚠️ 系统组件预加载部分失败，将使用降级模式")
        except Exception as e:
            print(f"❌ 系统组件预加载失败: {e}")
            logging.error(f"系统组件预加载失败: {e}")
    else:
        print("⚠️ 全局初始化器不可用，使用传统初始化模式")
    
    # 启动对话标题智能体为常驻服务
    try:
        if TITLE_AGENT_AVAILABLE and not title_agent.is_running:
            title_agent.start_monitoring()
            print("🧠 对话标题智能体已启动并进入监听")
        elif TITLE_AGENT_AVAILABLE:
            print("ℹ️ 对话标题智能体已在运行，跳过重复启动")
    except Exception as e:
        logging.error(f"启动对话标题智能体失败: {e}")
        print(f"❌ 启动对话标题智能体失败: {e}")

    # 启动自动标题生成服务
    try:
        if AUTO_TITLE_SERVICE_AVAILABLE and not auto_title_service.is_running:
            start_auto_title_service()
            print("🧩 自动标题生成服务已启动并进入监听")
        elif AUTO_TITLE_SERVICE_AVAILABLE:
            print("ℹ️ 自动标题生成服务已在运行，跳过重复启动")
    except Exception as e:
        logging.error(f"启动自动标题生成服务失败: {e}")
        print(f"❌ 启动自动标题生成服务失败: {e}")

    try:
        from fastapi_app.routers.tasks import run_db_migration_once
        run_db_migration_once()
        print("🗄️ 数据库约束检查与迁移已执行")
    except Exception as e:
        logging.warning(f"数据库迁移执行失败: {e}")

    print("🌟 ChatBot API服务已启动")

# 关闭事件 - 清理系统资源
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理事件"""
    print("🛑 正在关闭ChatBot系统...")
    
    if GLOBAL_INITIALIZER_AVAILABLE:
        try:
            await shutdown_system()
            print("✅ 系统资源清理完成")
        except Exception as e:
            print(f"⚠️ 系统资源清理时发生错误: {e}")
            logging.error(f"系统资源清理失败: {e}")
    
    # 关闭对话标题智能体
    try:
        if TITLE_AGENT_AVAILABLE and title_agent.is_running:
            title_agent.stop_monitoring()
            print("🧠 对话标题智能体已关闭")
    except Exception as e:
        logging.error(f"停止对话标题智能体失败: {e}")
        print(f"⚠️ 停止对话标题智能体失败: {e}")

    # 关闭自动标题生成服务
    try:
        if AUTO_TITLE_SERVICE_AVAILABLE and auto_title_service.is_running:
            stop_auto_title_service()
            print("🧩 自动标题生成服务已关闭")
    except Exception as e:
        logging.error(f"停止自动标题生成服务失败: {e}")
        print(f"⚠️ 停止自动标题生成服务失败: {e}")
    
    print("👋 ChatBot API服务已关闭")

@app.get("/")
async def read_index():
    """返回主页"""
    return FileResponse(str(STATIC_DIR / "index.html"))

@app.get("/health")
async def health_check():
    """健康检查接口"""
    system_status = "initialized" if (GLOBAL_INITIALIZER_AVAILABLE and is_system_initialized()) else "basic"
    return {
        "status": "healthy", 
        "message": "FastAPI ChatBot is running",
        "system_status": system_status,
        "preload_available": GLOBAL_INITIALIZER_AVAILABLE
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
