#!/usr/bin/env python3
"""
项目配置管理
兼容旧版本的Settings类，同时集成新的配置管理系统
"""

from pathlib import Path
from typing import Optional, List
import os
from dotenv import load_dotenv

# 导入新的配置管理系统
from .config_manager import load_config, get_config, AppConfig

# 加载环境变量
load_dotenv()

class Settings:
    """应用配置类 - 兼容旧版本API"""
    
    def __init__(self):
        # 加载新的配置系统
        try:
            self._config = get_config()
        except RuntimeError:
            # 如果配置未加载，则加载它
            self._config = load_config()
    
    # 项目基础配置
    @property
    def project_name(self) -> str:
        return self._config.app_name
    
    @property
    def version(self) -> str:
        return self._config.version
    
    @property
    def debug(self) -> bool:
        return self._config.debug
    
    # 日志配置
    @property
    def log_level(self) -> str:
        return self._config.logging.level
    
    # 文件路径配置
    @property
    def project_root(self) -> Path:
        return Path(__file__).parent.parent.parent
    
    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"
    
    @property
    def documents_dir(self) -> Path:
        return Path(self._config.file.documents_dir)
    
    @property
    def vector_db_dir(self) -> Path:
        return Path(self._config.file.vector_db_dir)
    
    @property
    def logs_dir(self) -> Path:
        return self.project_root / "logs"
    
    # DeepSeek API配置
    @property
    def deepseek_api_key(self) -> Optional[str]:
        return self._config.ai.deepseek_api_key or os.getenv("DEEPSEEK_API_KEY")
    
    @property
    def deepseek_api_base(self) -> str:
        return self._config.ai.deepseek_api_base
    
    @property
    def deepseek_base_url(self) -> str:
        """兼容性属性，返回deepseek_api_base的值"""
        return self._config.ai.deepseek_api_base
    
    @property
    def model_name(self) -> str:
        return self._config.ai.deepseek_model
    
    @property
    def temperature(self) -> float:
        return self._config.ai.deepseek_temperature
    
    @property
    def max_tokens(self) -> int:
        return self._config.ai.deepseek_max_tokens
    
    # MCP配置
    @property
    def mcp_server_name(self) -> str:
        return self._config.mcp.server_name
    
    @property
    def mcp_server_version(self) -> str:
        return self._config.mcp.server_version
    
    @property
    def mcp_server_port(self) -> int:
        return self._config.mcp.server_port
    
    @property
    def mcp_tools_enabled(self) -> bool:
        return self._config.mcp.tools_enabled
    
    # 嵌入模型配置
    @property
    def embedding_model(self) -> str:
        return self._config.ai.embedding_model
    
    # RAG配置
    @property
    def chunk_size(self) -> int:
        return self._config.ai.chunk_size
    
    @property
    def chunk_overlap(self) -> int:
        return self._config.ai.chunk_overlap
    
    @property
    def top_k_results(self) -> int:
        return self._config.ai.top_k_results
    
    @property
    def similarity_threshold(self) -> float:
        return self._config.ai.similarity_threshold
    
    # 向量数据库配置
    @property
    def vector_db_type(self) -> str:
        return "faiss"  # 保持兼容性
    
    # 搜索引擎API配置
    @property
    def google_api_key(self) -> Optional[str]:
        return self._config.search.google_api_key or os.getenv("GOOGLE_API_KEY")
    
    @property
    def google_cse_id(self) -> Optional[str]:
        return self._config.search.google_cse_id or os.getenv("GOOGLE_CSE_ID")
    
    @property
    def bing_api_key(self) -> Optional[str]:
        return self._config.search.bing_api_key or os.getenv("BING_API_KEY")
    
    @property
    def serpapi_key(self) -> Optional[str]:
        return os.getenv("SERPAPI_KEY")
    
    # 百度AI搜索API配置
    @property
    def baidu_ai_search_token(self) -> Optional[str]:
        return self._config.search.baidu_token or os.getenv("BAIDU_AI_SEARCH_TOKEN")
    
    @property
    def baidu_ai_search_url(self) -> str:
        return self._config.search.baidu_url
    
    # 网络搜索配置
    @property
    def web_search_enabled(self) -> bool:
        return self._config.search.enabled
    
    @property
    def web_search_max_results(self) -> int:
        return self._config.search.max_results
    
    @property
    def web_search_timeout(self) -> int:
        return self._config.search.timeout
    
    @property
    def web_search_engines(self) -> List[str]:
        return ["baidu"]  # 保持兼容性
    
    @property
    def web_search_fallback_threshold(self) -> float:
        return 0.5  # 保持兼容性
    
    # 搜索引擎优先级配置
    @property
    def search_engine_priority(self) -> List[str]:
        return self._config.search.engine_priority
    
    # 搜索结果缓存配置
    @property
    def search_cache_enabled(self) -> bool:
        return self._config.search.cache_enabled
    
    @property
    def search_cache_ttl(self) -> int:
        return self._config.search.cache_ttl
    
    def create_directories(self):
        """创建必要的目录"""
        directories = [
            self.data_dir,
            self.documents_dir,
            self.vector_db_dir,
            self.logs_dir
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def get_config(self) -> AppConfig:
        """获取完整的配置对象"""
        return self._config


# 全局设置实例
_settings = None

def get_settings() -> Settings:
    """获取全局设置实例"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

def setup_logger(name: str = None):
    """设置日志记录器"""
    import logging
    from src.utils.logger import setup_logger as _setup_logger
    return _setup_logger(name)