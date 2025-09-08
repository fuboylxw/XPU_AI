"""
API配置文件
"""

from pydantic import BaseModel
from typing import List, Optional
import os
from pathlib import Path

# 导入新的配置管理系统
try:
    from src.config.config_manager import get_config
    USE_NEW_CONFIG = True
except ImportError:
    USE_NEW_CONFIG = False

class APIConfig:
    """API配置类 - 兼容旧版本API"""
    
    def __init__(self):
        """初始化配置"""
        if USE_NEW_CONFIG:
            try:
                self._config = get_config()
                self._use_new_config = True
            except RuntimeError:
                self._use_new_config = False
                self._init_legacy_config()
        else:
            self._use_new_config = False
            self._init_legacy_config()
    
    def _init_legacy_config(self):
        """初始化传统配置"""
        # 服务配置
        self._host = os.getenv("API_HOST", "202.200.206.248")
        self._port = int(os.getenv("API_PORT", "8000"))
        self._debug = os.getenv("API_DEBUG", "false").lower() == "true"
        self._reload = os.getenv("API_RELOAD", "true").lower() == "true"
        
        # CORS配置
        self._allow_origins = ["*"]
        self._allow_credentials = True
        self._allow_methods = ["*"]
        self._allow_headers = ["*"]
        
        # 文件上传配置
        self._max_file_size = int(os.getenv("MAX_FILE_SIZE", str(10 * 1024 * 1024)))
        self._allowed_file_types = ["pdf", "docx", "txt", "xlsx"]
        
        # 会话配置
        self._session_timeout_minutes = int(os.getenv("SESSION_TIMEOUT", "30"))
        self._max_sessions = int(os.getenv("MAX_SESSIONS", "1000"))
        
        # 流式响应配置
        self._stream_chunk_size = int(os.getenv("STREAM_CHUNK_SIZE", "1024"))
        self._stream_timeout = int(os.getenv("STREAM_TIMEOUT", "30"))
        
        # 日志配置
        self._log_level = os.getenv("LOG_LEVEL", "INFO")
        self._access_log = True
        
        # 安全配置
        self._api_key_header = os.getenv("API_KEY_HEADER", "X-API-Key")
        self._rate_limit_per_minute = int(os.getenv("RATE_LIMIT", "60"))
    
    # 使用属性来提供统一的接口
    @property
    def host(self) -> str:
        if self._use_new_config:
            return self._config.api.host
        return self._host
    
    @property
    def port(self) -> int:
        if self._use_new_config:
            return self._config.api.port
        return self._port
    
    @property
    def debug(self) -> bool:
        if self._use_new_config:
            return self._config.debug
        return self._debug
    
    @property
    def reload(self) -> bool:
        if self._use_new_config:
            return self._config.api.reload
        return self._reload
    
    @property
    def allow_origins(self) -> List[str]:
        if self._use_new_config:
            return self._config.api.cors_origins
        return self._allow_origins
    
    @property
    def allow_credentials(self) -> bool:
        return self._allow_credentials
    
    @property
    def allow_methods(self) -> List[str]:
        if self._use_new_config:
            return self._config.api.cors_methods
        return self._allow_methods
    
    @property
    def allow_headers(self) -> List[str]:
        if self._use_new_config:
            return self._config.api.cors_headers
        return self._allow_headers
    
    @property
    def max_file_size(self) -> int:
        if self._use_new_config:
            return self._config.file.max_file_size
        return self._max_file_size
    
    @property
    def allowed_file_types(self) -> List[str]:
        if self._use_new_config:
            return self._config.file.allowed_extensions
        return self._allowed_file_types
    
    @property
    def session_timeout_minutes(self) -> int:
        if self._use_new_config:
            return self._config.api.session_timeout // 60  # 转换为分钟
        return self._session_timeout_minutes
    
    @property
    def session_timeout(self) -> int:
        """返回会话超时时间（秒）"""
        if self._use_new_config:
            return self._config.api.session_timeout
        return self._session_timeout_minutes * 60  # 转换为秒
    
    @property
    def max_sessions(self) -> int:
        if self._use_new_config:
            return self._config.api.max_sessions
        return self._max_sessions
    
    @property
    def stream_chunk_size(self) -> int:
        if self._use_new_config:
            return self._config.api.stream_chunk_size
        return self._stream_chunk_size
    
    @property
    def stream_timeout(self) -> int:
        if self._use_new_config:
            return self._config.api.stream_timeout
        return self._stream_timeout
    
    @property
    def log_level(self) -> str:
        if self._use_new_config:
            return self._config.logging.level
        return self._log_level
    
    @property
    def access_log(self) -> bool:
        return self._access_log
    
    @property
    def api_key_header(self) -> str:
        if self._use_new_config:
            return self._config.security.api_key_header
        return self._api_key_header
    
    @property
    def rate_limit_per_minute(self) -> int:
        if self._use_new_config:
            return self._config.security.rate_limit.requests_per_minute
        return self._rate_limit_per_minute
    
    @classmethod
    def from_env(cls) -> "APIConfig":
        """从环境变量创建配置 - 保持向后兼容"""
        return cls()

# 全局配置实例
api_config = APIConfig.from_env()

# 兼容函数
def get_settings():
    """获取API配置设置"""
    return api_config