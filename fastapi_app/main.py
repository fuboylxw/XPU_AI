"""
FastAPI 主应用文件

采用 lifespan（类似 React onMount/onCleanup）统一管理：
- 应用启动：数据库初始化、容器预热、系统事件注册
- 应用关闭：容器与 provider 资源释放
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import text

from fastapi_app.database import Base, engine
from fastapi_app.routers import auth, chat, config, tasks, tts, upload
from src.Chatbot.core.container import get_container, init_container, shutdown_container
from src.Chatbot.core.events import SYSTEM_SHUTDOWN, SYSTEM_STARTUP, event_bus
from src.Chatbot.core.providers import runtime_snapshot, shutdown_runtime_instances

logger = logging.getLogger(__name__)

try:
    from fastapi_app.routers import voice

    VOICE_ROUTER_AVAILABLE = True
except Exception as e:
    logger.warning("语音路由不可用: %s", e)
    VOICE_ROUTER_AVAILABLE = False

try:
    from src.Chatbot.agents.conversation_title_agent import title_agent

    TITLE_AGENT_AVAILABLE = True
except Exception as e:
    logger.warning("对话标题智能体不可用: %s", e)
    TITLE_AGENT_AVAILABLE = False

try:
    from src.Chatbot.services.auto_title_service import (
        auto_title_service,
        start_auto_title_service,
        stop_auto_title_service,
    )

    AUTO_TITLE_SERVICE_AVAILABLE = True
except Exception as e:
    logger.warning("自动标题生成服务不可用: %s", e)
    AUTO_TITLE_SERVICE_AVAILABLE = False


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
INDEX_HTML = STATIC_DIR / "index.html"


def _on_system_startup(data):
    """系统启动时，启动标题相关服务"""
    try:
        if TITLE_AGENT_AVAILABLE and not title_agent.is_running:
            title_agent.start_monitoring()
            logger.info("对话标题智能体已启动")
    except Exception as e:
        logger.error("启动对话标题智能体失败: %s", e)

    try:
        if AUTO_TITLE_SERVICE_AVAILABLE and not auto_title_service.is_running:
            start_auto_title_service()
            logger.info("自动标题生成服务已启动")
    except Exception as e:
        logger.error("启动自动标题生成服务失败: %s", e)


def _on_system_shutdown(data):
    """系统关闭时，停止标题相关服务"""
    try:
        if TITLE_AGENT_AVAILABLE and title_agent.is_running:
            title_agent.stop_monitoring()
            logger.info("对话标题智能体已关闭")
    except Exception as e:
        logger.error("停止对话标题智能体失败: %s", e)

    try:
        if AUTO_TITLE_SERVICE_AVAILABLE and auto_title_service.is_running:
            stop_auto_title_service()
            logger.info("自动标题生成服务已关闭")
    except Exception as e:
        logger.error("停止自动标题生成服务失败: %s", e)


def _bootstrap_database() -> None:
    """数据库与表结构初始化"""
    try:
        with engine.connect() as conn:
            lock = conn.execute(
                text("SELECT GET_LOCK(:name, :timeout)"),
                {"name": "chatbot_schema_migration", "timeout": 0},
            ).scalar()
            if lock == 1:
                try:
                    Base.metadata.create_all(bind=engine)
                    try:
                        tasks._ensure_db_constraints(conn)
                    except Exception as e:
                        logger.warning("数据库约束迁移失败: %s", e)
                finally:
                    conn.execute(
                        text("SELECT RELEASE_LOCK(:name)"),
                        {"name": "chatbot_schema_migration"},
                    )
    except Exception as e:
        logger.warning("启动时数据库初始化失败: %s", e)


def _run_task_migration() -> None:
    """执行任务表相关迁移"""
    try:
        from fastapi_app.routers.tasks import run_db_migration_once

        run_db_migration_once()
        logger.info("数据库约束检查与迁移已执行")
    except Exception as e:
        logger.warning("数据库迁移执行失败: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期（推荐写法）：
    代替 @app.on_event("startup"/"shutdown")
    """
    unsubscribe_startup = event_bus.on(SYSTEM_STARTUP, _on_system_startup)
    unsubscribe_shutdown = event_bus.on(SYSTEM_SHUTDOWN, _on_system_shutdown)

    logger.info("正在启动 ChatBot 系统...")
    _bootstrap_database()

    try:
        logger.info("开始预加载系统组件...")
        preload_ok = await init_container()
        if preload_ok:
            logger.info("系统组件预加载完成")
        else:
            logger.warning("系统组件预加载部分失败，将以降级模式运行")
    except Exception as e:
        logger.error("系统组件预加载失败: %s", e)

    _run_task_migration()
    logger.info("ChatBot API 服务已启动")

    try:
        yield
    finally:
        logger.info("正在关闭 ChatBot 系统...")
        try:
            await shutdown_container()
        except Exception as e:
            logger.error("容器关闭失败: %s", e)

        try:
            await shutdown_runtime_instances()
        except Exception as e:
            logger.warning("Provider 实例释放失败: %s", e)

        unsubscribe_shutdown()
        unsubscribe_startup()
        logger.info("ChatBot API 服务已关闭")


app = FastAPI(
    title="ChatBot API",
    description="基于 FastAPI 的聊天机器人 API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境请收敛为可信域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(config.router, prefix="/api", tags=["config"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(tts.router, prefix="/api", tags=["tts"])
app.include_router(upload.router, prefix="/api", tags=["upload"])
if VOICE_ROUTER_AVAILABLE:
    app.include_router(voice.router, prefix="/api", tags=["voice"])
app.include_router(tasks.router, prefix="/api", tags=["tasks"])


@app.get("/")
async def read_index():
    """返回前端入口文件（若不存在则回退 JSON 提示）"""
    if INDEX_HTML.exists():
        return FileResponse(str(INDEX_HTML))
    return {
        "status": "ok",
        "message": "ChatBot API is running",
        "hint": "frontend index.html not found under fastapi_app/static",
    }


@app.get("/health")
async def health_check():
    """健康检查接口"""
    container = get_container()
    return {
        "status": "healthy",
        "message": "FastAPI ChatBot is running",
        "system_status": "initialized" if container.is_initialized else "basic",
        "preload_available": True,
        "providers": runtime_snapshot(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000)
