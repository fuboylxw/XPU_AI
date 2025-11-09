"""
全局初始化管理器
完整版实现，支持ChatbotAgent所需的所有组件预加载和管理
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

# 设置日志
logger = logging.getLogger(__name__)

# 导入所需的组件类
try:
    from langchain_community.chat_models import ChatOpenAI
    from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
    from config.settings import settings
    from src.Chatbot.tools.web_search import WebSearchTool
    from src.Chatbot.agents.security_audit_agent import SecurityAuditAgent
    from src.Chatbot.agents.intent_recognition_agent import IntentRecognitionAgent
    from src.Chatbot.agents.data_query_agent import DataQueryAgent
    from src.Chatbot.agents.website_knowledge_agent import WebsiteKnowledgeAgent
except ImportError as e:
    logger.warning(f"导入组件时出现警告: {e}")
    # 在某些情况下，组件可能不可用，但不应阻止初始化器的基本功能

class GlobalInitializer:
    """全局初始化管理器 - 单例模式"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_components'):
            self._components: Dict[str, Any] = {}
            self._initialization_status: Dict[str, str] = {}
            self._system_initialized = False
            self._initialization_time = None
    
    def is_initialized(self) -> bool:
        """检查系统是否已初始化"""
        return self._system_initialized
    
    def get_component(self, component_name: str) -> Optional[Any]:
        """获取预加载的组件"""
        return self._components.get(component_name)
    
    def set_component(self, component_name: str, component: Any):
        """设置组件"""
        self._components[component_name] = component
        self._initialization_status[component_name] = "initialized"
        logger.info(f"组件 {component_name} 已设置")
    
    def get_initialization_status(self) -> Dict[str, str]:
        """获取初始化状态"""
        return self._initialization_status.copy()
    
    async def initialize_system(self) -> bool:
        """初始化全局系统"""
        if self._system_initialized:
            logger.info("系统已经初始化，跳过重复初始化")
            return True
        
        logger.info("🚀 开始全局系统初始化...")
        start_time = datetime.now()
        
        try:
            # 基础初始化 - 这里可以添加实际的组件初始化逻辑
            await self._initialize_basic_components()
            
            self._system_initialized = True
            self._initialization_time = datetime.now()
            
            init_duration = (self._initialization_time - start_time).total_seconds()
            logger.info(f"✅ 全局系统初始化完成 (耗时: {init_duration:.2f}秒)")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 全局系统初始化失败: {e}")
            return False
    
    async def _initialize_basic_components(self):
        """初始化基础组件"""
        logger.info("开始初始化ChatbotAgent所需的所有组件...")
        
        try:
            # 1. 初始化LLM客户端
            logger.info("📊 初始化LLM客户端...")
            self._initialization_status['llm'] = 'initializing'
            
            # 标准LLM客户端
            self._components['llm'] = ChatOpenAI(
                api_key=settings.OPENAI_API_KEY,
                model=settings.OPENAI_MODEL,
                base_url=settings.OPENAI_MODEL_BASE_URL,
                temperature=settings.OPENAI_TEMPERATURE,
                max_tokens=settings.OPENAI_MAX_TOKENS,
            )
            
            # 流式LLM客户端
            streaming_handler = StreamingStdOutCallbackHandler()
            self._components['llm_stream'] = ChatOpenAI(
                api_key=settings.OPENAI_API_KEY,
                model=settings.OPENAI_MODEL,
                base_url=settings.OPENAI_MODEL_BASE_URL,
                temperature=settings.OPENAI_TEMPERATURE,
                max_tokens=settings.OPENAI_MAX_TOKENS,
                streaming=True,
                callbacks=[streaming_handler],
            )
            
            # LLM模型预热
            logger.info("🔥 开始LLM模型预热...")
            try:
                # 使用简单的测试消息预热模型
                warmup_message = "Hello, this is a warmup message."
                _ = self._components['llm'].invoke(warmup_message)
                logger.info("✅ LLM模型预热完成")
            except Exception as e:
                logger.warning(f"⚠️ LLM模型预热失败: {e}")
            
            self._initialization_status['llm'] = 'initialized'
            logger.info("✅ LLM客户端初始化完成")
            
            # 2. 初始化工具组件
            logger.info("🔧 初始化工具组件...")
            self._initialization_status['tools'] = 'initializing'
            
            self._components['web_search_tool'] = WebSearchTool(settings)
            self._initialization_status['tools'] = 'initialized'
            logger.info("✅ 工具组件初始化完成")
            
            # 3. 初始化智能体组件
            logger.info("🤖 初始化智能体组件...")
            self._initialization_status['agents'] = 'initializing'
            
            # 安全审核智能体
            self._components['security_agent'] = SecurityAuditAgent()
            logger.info("   ✅ SecurityAuditAgent 初始化完成")
            
            # 意图识别智能体
            self._components['intent_agent'] = IntentRecognitionAgent()
            logger.info("   ✅ IntentRecognitionAgent 初始化完成")
            
            # 数据查询智能体
            self._components['data_agent'] = DataQueryAgent()
            logger.info("   ✅ DataQueryAgent 初始化完成")
            
            # 网站知识库智能体
            self._components['website_agent'] = WebsiteKnowledgeAgent(
                base_url="https://www.xpu.edu.cn/",
                output_dir=str(settings.project_root / "knowledge_base" / "xpu"),
                max_pages=200,
                delay=0.5,
            )
            logger.info("   ✅ WebsiteKnowledgeAgent 初始化完成")
            
            self._initialization_status['agents'] = 'initialized'
            logger.info("✅ 智能体组件初始化完成")
            
            # 4. 初始化检索引擎（可选，如果可用的话）
            logger.info("🔍 尝试初始化检索引擎...")
            self._initialization_status['retrieval'] = 'initializing'
            
            try:
                # 尝试初始化密集检索引擎
                from src.Chatbot.tools.dense_retrieval import DenseRetrievalEngine
                dense_engine = DenseRetrievalEngine()
                
                # 检索引擎预热
                logger.info("🔥 开始密集检索引擎预热...")
                try:
                    # 使用简单的测试查询预热检索引擎
                    test_query = "测试查询用于预热检索引擎"
                    if hasattr(dense_engine, 'model') and dense_engine.model:
                        _ = dense_engine.model.encode(test_query)
                        logger.info("✅ 密集检索引擎预热完成")
                    else:
                        logger.info("⚠️ 密集检索引擎模型未就绪，跳过预热")
                except Exception as warmup_e:
                    logger.warning(f"⚠️ 密集检索引擎预热失败: {warmup_e}")
                
                self._components['dense_engine'] = dense_engine
                logger.info("   ✅ DenseRetrievalEngine 初始化完成")
            except Exception as e:
                logger.warning(f"   ⚠️ DenseRetrievalEngine 初始化失败: {e}")
                self._components['dense_engine'] = None
            
            try:
                # 尝试初始化稀疏检索引擎
                from src.Chatbot.tools.sparse_retrieval import SparseRetrievalEngine
                sparse_engine = SparseRetrievalEngine()
                
                # 稀疏检索引擎预热
                logger.info("🔥 开始稀疏检索引擎预热...")
                try:
                    # 稀疏检索引擎通常不需要特殊预热，但可以进行基本检查
                    if hasattr(sparse_engine, 'initialize'):
                        sparse_engine.initialize()
                    logger.info("✅ 稀疏检索引擎预热完成")
                except Exception as warmup_e:
                    logger.warning(f"⚠️ 稀疏检索引擎预热失败: {warmup_e}")
                
                self._components['sparse_engine'] = sparse_engine
                logger.info("   ✅ SparseRetrievalEngine 初始化完成")
            except Exception as e:
                logger.warning(f"   ⚠️ SparseRetrievalEngine 初始化失败: {e}")
                self._components['sparse_engine'] = None
            
            self._initialization_status['retrieval'] = 'initialized'
            logger.info("✅ 检索引擎初始化完成")
            
            # 5. 设置系统状态
            self._initialization_status.update({
                'system': 'initialized',
                'basic_components': 'initialized'
            })
            
            logger.info("✅ 所有基础组件初始化完成")
            
        except Exception as e:
            logger.error(f"❌ 基础组件初始化失败: {e}")
            # 即使部分组件初始化失败，也要设置基本状态
            self._initialization_status.update({
                'system': 'partial_initialized',
                'basic_components': 'partial_initialized'
            })
            raise
    
    async def shutdown_system(self):
        """关闭系统并清理资源"""
        logger.info("🔄 开始关闭全局系统...")
        
        try:
            # 清理检索引擎
            if 'dense_engine' in self._components and self._components['dense_engine']:
                try:
                    # 如果检索引擎有清理方法，调用它
                    if hasattr(self._components['dense_engine'], 'cleanup'):
                        self._components['dense_engine'].cleanup()
                    logger.info("   ✅ DenseRetrievalEngine 清理完成")
                except Exception as e:
                    logger.warning(f"   ⚠️ DenseRetrievalEngine 清理失败: {e}")
            
            if 'sparse_engine' in self._components and self._components['sparse_engine']:
                try:
                    # 如果检索引擎有清理方法，调用它
                    if hasattr(self._components['sparse_engine'], 'cleanup'):
                        self._components['sparse_engine'].cleanup()
                    logger.info("   ✅ SparseRetrievalEngine 清理完成")
                except Exception as e:
                    logger.warning(f"   ⚠️ SparseRetrievalEngine 清理失败: {e}")
            
            # 清理智能体组件
            agent_components = ['security_agent', 'intent_agent', 'data_agent', 'website_agent']
            for agent_name in agent_components:
                if agent_name in self._components and self._components[agent_name]:
                    try:
                        # 如果智能体有清理方法，调用它
                        if hasattr(self._components[agent_name], 'cleanup'):
                            self._components[agent_name].cleanup()
                        logger.info(f"   ✅ {agent_name} 清理完成")
                    except Exception as e:
                        logger.warning(f"   ⚠️ {agent_name} 清理失败: {e}")
            
            # 清理工具组件
            if 'web_search_tool' in self._components and self._components['web_search_tool']:
                try:
                    if hasattr(self._components['web_search_tool'], 'cleanup'):
                        self._components['web_search_tool'].cleanup()
                    logger.info("   ✅ WebSearchTool 清理完成")
                except Exception as e:
                    logger.warning(f"   ⚠️ WebSearchTool 清理失败: {e}")
            
            # 清理LLM客户端（通常不需要特殊清理）
            logger.info("   ✅ LLM客户端清理完成")
            
            # 清理组件字典和状态
            self._components.clear()
            self._initialization_status.clear()
            self._system_initialized = False
            self._initialization_time = None
            
            logger.info("✅ 全局系统关闭完成")
            
        except Exception as e:
            logger.error(f"❌ 系统关闭时发生错误: {e}")


# 全局实例
_global_initializer = GlobalInitializer()

# 公共接口函数
def is_system_initialized() -> bool:
    """检查系统是否已初始化"""
    return _global_initializer.is_initialized()

def get_global_component(component_name: str) -> Optional[Any]:
    """获取全局组件"""
    return _global_initializer.get_component(component_name)

def set_global_component(component_name: str, component: Any):
    """设置全局组件"""
    _global_initializer.set_component(component_name, component)

def get_initialization_status() -> Dict[str, str]:
    """获取初始化状态"""
    return _global_initializer.get_initialization_status()

async def initialize_system() -> bool:
    """初始化全局系统"""
    return await _global_initializer.initialize_system()

async def shutdown_system():
    """关闭全局系统"""
    await _global_initializer.shutdown_system()