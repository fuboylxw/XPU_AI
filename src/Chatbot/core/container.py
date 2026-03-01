"""
类型化依赖注入容器
替代 GlobalInitializer 的字符串键字典模式，提供类型安全的组件管理
"""
import logging
from dataclasses import dataclass, field
from typing import Optional, Any, List
from datetime import datetime

from src.Chatbot.core.lifecycle import Lifecycle, LifecycleManager, SetupHandler
from src.Chatbot.core.events import event_bus, SYSTEM_STARTUP, SYSTEM_SHUTDOWN

logger = logging.getLogger(__name__)


@dataclass
class Container:
    """应用级依赖注入容器，所有组件为类型化字段"""

    # LLM 客户端
    llm: Any = None
    llm_stream: Any = None

    # 智能体
    security_agent: Any = None
    intent_agent: Any = None
    data_agent: Any = None

    # 工具
    web_search_tool: Any = None
    mcp_tool_runner: Any = None

    # 检索引擎
    dense_engine: Any = None
    sparse_engine: Any = None

    # 生命周期管理的服务（按注册顺序启动，逆序关闭）
    _services: List[Any] = field(default_factory=list, repr=False)
    _lifecycle_manager: LifecycleManager = field(default_factory=LifecycleManager, repr=False)

    # 内部状态
    _initialized: bool = field(default=False, repr=False)
    _initialization_time: Optional[datetime] = field(default=None, repr=False)

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def register_effect(self, name: str, setup: SetupHandler) -> None:
        """注册 setup/cleanup effect，行为类似 onMount/onCleanup"""
        self._lifecycle_manager.register_effect(name, setup)

    def register_service(self, service: Any) -> None:
        """注册一个实现 Lifecycle 协议的服务，由容器管理其生命周期"""
        if isinstance(service, Lifecycle):
            self._services.append(service)
            service_name = type(service).__name__
            logger.info(f"注册生命周期服务: {service_name}")

            async def _setup():
                await service.startup()

                async def _cleanup():
                    await service.shutdown()

                return _cleanup

            self.register_effect(f"service:{service_name}", _setup)
        else:
            logger.warning(f"{type(service).__name__} 未实现 Lifecycle 协议，跳过注册")

    async def startup(self) -> bool:
        """按依赖顺序初始化所有组件，然后执行注册的生命周期 effect"""
        if self._initialized:
            logger.info("容器已初始化，跳过重复初始化")
            return True

        logger.info("开始容器初始化...")
        start_time = datetime.now()

        try:
            await self._init_llm()
            await self._init_tools()
            await self._init_agents()
            await self._init_retrieval()

            await self._lifecycle_manager.startup()

            self._initialized = True
            self._initialization_time = datetime.now()
            duration = (self._initialization_time - start_time).total_seconds()
            logger.info(f"容器初始化完成 (耗时: {duration:.2f}秒)")

            # 发布系统启动事件
            await event_bus.emit(SYSTEM_STARTUP, {"time": self._initialization_time.isoformat()})

            return True
        except Exception as e:
            logger.error(f"容器初始化失败: {e}")
            return False

    async def shutdown(self):
        """先关闭 lifecycle effect，再清理基础组件"""
        logger.info("开始容器关闭...")

        # 发布系统关闭事件
        await event_bus.emit(SYSTEM_SHUTDOWN)

        await self._lifecycle_manager.shutdown()

        # 清理基础组件：检索引擎 → 智能体 → 工具 → LLM
        for name in ("dense_engine", "sparse_engine", "security_agent",
                      "intent_agent", "data_agent", "web_search_tool"):
            component = getattr(self, name, None)
            if component and hasattr(component, "cleanup"):
                try:
                    component.cleanup()
                    logger.info(f"  {name} 清理完成")
                except Exception as e:
                    logger.warning(f"  {name} 清理失败: {e}")
            setattr(self, name, None)

        self.llm = None
        self.llm_stream = None
        self._initialized = False
        self._initialization_time = None
        logger.info("容器关闭完成")

    async def _init_llm(self):
        """初始化 LLM 客户端"""
        logger.info("初始化LLM客户端...")
        from langchain_community.chat_models import ChatOpenAI
        from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
        from config.settings import settings

        self.llm = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            base_url=settings.OPENAI_MODEL_BASE_URL,
            temperature=settings.OPENAI_TEMPERATURE,
            max_tokens=settings.OPENAI_MAX_TOKENS,
        )

        self.llm_stream = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            base_url=settings.OPENAI_MODEL_BASE_URL,
            temperature=settings.OPENAI_TEMPERATURE,
            max_tokens=settings.OPENAI_MAX_TOKENS,
            streaming=True,
            callbacks=[StreamingStdOutCallbackHandler()],
        )

        # LLM 预热
        try:
            _ = self.llm.invoke("Hello, this is a warmup message.")
            logger.info("LLM模型预热完成")
        except Exception as e:
            logger.warning(f"LLM模型预热失败: {e}")

        logger.info("LLM客户端初始化完成")

    async def _init_tools(self):
        """初始化工具组件"""
        logger.info("初始化工具组件...")
        from config.settings import settings
        from src.Chatbot.tools.MCP.web_search import WebSearchTool

        self.web_search_tool = WebSearchTool(settings)
        logger.info("工具组件初始化完成")

    async def _init_agents(self):
        """初始化智能体组件"""
        logger.info("初始化智能体组件...")
        from src.Chatbot.agents.security_audit_agent import SecurityAuditAgent
        from src.Chatbot.agents.intent_recognition_agent import IntentRecognitionAgent
        from src.Chatbot.agents.data_query_agent import DataQueryAgent

        self.security_agent = SecurityAuditAgent()
        self.intent_agent = IntentRecognitionAgent()
        self.data_agent = DataQueryAgent()
        logger.info("智能体组件初始化完成")

    async def _init_retrieval(self):
        """初始化检索引擎（可选）"""
        logger.info("尝试初始化检索引擎...")

        try:
            from src.Chatbot.tools.dense_retrieval import DenseRetrievalEngine
            self.dense_engine = DenseRetrievalEngine()
            # 预热
            if hasattr(self.dense_engine, "model") and self.dense_engine.model:
                _ = self.dense_engine.model.encode("测试查询用于预热检索引擎")
                logger.info("密集检索引擎预热完成")
        except Exception as e:
            logger.warning(f"DenseRetrievalEngine 初始化失败: {e}")
            self.dense_engine = None

        try:
            from src.Chatbot.tools.sparse_retrieval import SparseRetrievalEngine
            self.sparse_engine = SparseRetrievalEngine()
            if hasattr(self.sparse_engine, "initialize"):
                self.sparse_engine.initialize()
            logger.info("稀疏检索引擎初始化完成")
        except Exception as e:
            logger.warning(f"SparseRetrievalEngine 初始化失败: {e}")
            self.sparse_engine = None

        logger.info("检索引擎初始化完成")


# 全局容器实例
_app_container: Optional[Container] = None


def get_container() -> Container:
    """获取全局容器实例"""
    global _app_container
    if _app_container is None:
        _app_container = Container()
    return _app_container


async def init_container() -> bool:
    """初始化全局容器"""
    container = get_container()
    return await container.startup()


async def shutdown_container():
    """关闭全局容器"""
    global _app_container
    if _app_container is not None:
        await _app_container.shutdown()
        _app_container = None
