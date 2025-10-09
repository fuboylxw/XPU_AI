#!/usr/bin/env python3
"""
增强的配置管理模块
支持多环境配置、环境变量覆盖、配置验证等功能
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
from enum import Enum
from dotenv import load_dotenv
import logging

class Environment(str, Enum):
    """环境类型枚举"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"

class DatabaseConfig(BaseModel):
    """数据库配置"""
    type: str = "sqlite"
    host: Optional[str] = None
    port: Optional[int] = None
    database: str = "xpu_ai.db"
    username: Optional[str] = None
    password: Optional[str] = None
    pool_size: int = 10
    max_overflow: int = 20
    echo: bool = False

class RedisConfig(BaseModel):
    """Redis配置"""
    host: str = "202.200.206.248"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    max_connections: int = 10
    decode_responses: bool = True

class APIConfig(BaseModel):
    """API服务配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    reload: bool = False
    workers: int = 1
    
    # CORS配置
    cors_origins: List[str] = ["*"]
    cors_credentials: bool = True
    cors_methods: List[str] = ["*"]
    cors_headers: List[str] = ["*"]
    
    # 请求限制
    max_request_size: int = 16 * 1024 * 1024  # 16MB
    request_timeout: int = 30
    
    @field_validator('port')
    @classmethod
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError('端口号必须在1-65535之间')
        return v

class SecurityConfig(BaseModel):
    """安全配置"""
    secret_key: str = Field(default="your-secret-key-here-change-in-production", min_length=32)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # API密钥配置
    api_key_header: str = "X-API-Key"
    api_keys: List[str] = ["test-api-key-12345"]
    
    # 限流配置
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000
    burst_limit: int = 10
    
    # IP白名单/黑名单
    whitelist_ips: List[str] = []
    blacklist_ips: List[str] = []
    
    # CSRF保护
    csrf_enabled: bool = True
    csrf_token_lifetime_hours: int = 1

class LoggingConfig(BaseModel):
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_enabled: bool = True
    file_path: str = "logs/app.log"
    file_max_size: str = "10MB"
    file_backup_count: int = 5
    console_enabled: bool = True
    
    @field_validator('level')
    @classmethod
    def validate_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'日志级别必须是: {valid_levels}')
        return v.upper()

class AIConfig(BaseModel):
    """AI服务配置"""
    # DeepSeek配置
    deepseek_api_key: Optional[str] = None
    deepseek_api_base: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    deepseek_temperature: float = 0.7
    deepseek_max_tokens: int = 2000
    
    # 嵌入模型配置
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_device: str = "cpu"
    
    # RAG配置
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k_results: int = 5
    similarity_threshold: float = 0.7
    
    @field_validator('deepseek_temperature')
    @classmethod
    def validate_temperature(cls, v):
        if not 0.0 <= v <= 2.0:
            raise ValueError('temperature必须在0.0-2.0之间')
        return v

class SearchConfig(BaseModel):
    """搜索引擎配置"""
    enabled: bool = True
    timeout: int = 30
    max_results: int = 5
    
    # 百度AI搜索
    baidu_token: Optional[str] = None
    baidu_url: str = "https://qianfan.baidubce.com/v2/ai_search/chat/completions"
    
    # Google搜索
    google_api_key: Optional[str] = None
    google_cse_id: Optional[str] = None
    
    # Bing搜索
    bing_api_key: Optional[str] = None
    
    # 搜索引擎优先级
    engine_priority: List[str] = ["baidu", "google", "bing"]
    
    # 缓存配置
    cache_enabled: bool = True
    cache_ttl: int = 3600

class FileConfig(BaseModel):
    """文件处理配置"""
    upload_dir: str = "data/uploads"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_extensions: List[str] = ["pdf", "docx", "txt", "xlsx", "pptx"]
    
    # 文档处理
    documents_dir: str = "data/documents"
    vector_db_dir: str = "data/vector_db"
    
    @field_validator('max_file_size')
    @classmethod
    def validate_file_size(cls, v):
        if v <= 0:
            raise ValueError('文件大小限制必须大于0')
        return v

class MCPConfig(BaseModel):
    """MCP服务配置"""
    enabled: bool = True
    server_name: str = "school-info-server"
    server_version: str = "1.0.0"
    server_port: int = 3000
    tools_enabled: bool = True

class AppConfig(BaseSettings):
    """应用主配置类"""
    
    # 基础配置
    app_name: str = "XPU AI Assistant"
    version: str = "1.0.0"
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    
    # 各模块配置
    api: APIConfig = APIConfig()
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    security: SecurityConfig = SecurityConfig()
    logging: LoggingConfig = LoggingConfig()
    ai: AIConfig = AIConfig()
    search: SearchConfig = SearchConfig()
    file: FileConfig = FileConfig()
    mcp: MCPConfig = MCPConfig()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"
        case_sensitive = False
        extra = "ignore"  # 忽略额外字段，避免验证错误

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path(__file__).parent
        self.project_root = self.config_dir.parent.parent
        self._config: Optional[AppConfig] = None
        self._environment: Optional[Environment] = None
        
    def load_config(self, environment: Optional[str] = None) -> AppConfig:
        """加载配置"""
        # 确定环境
        env = environment or os.getenv("ENVIRONMENT", "development")
        self._environment = Environment(env)
        
        # 加载环境变量文件
        self._load_env_files()
        
        # 加载配置文件
        config_data = self._load_config_files()
        
        # 创建配置实例
        self._config = AppConfig(**config_data)
        
        # 设置环境相关的默认值
        self._apply_environment_defaults()
        
        # 验证配置
        self._validate_config()
        
        # 创建必要的目录
        self._create_directories()
        
        return self._config
    
    def _load_env_files(self):
        """加载环境变量文件"""
        env_files = [
            self.project_root / ".env",
            self.project_root / f".env.{self._environment.value}",
            self.project_root / ".env.local"
        ]
        
        for env_file in env_files:
            if env_file.exists():
                load_dotenv(env_file, override=True)
                logging.info(f"已加载环境变量文件: {env_file}")
    
    def _load_config_files(self) -> Dict[str, Any]:
        """加载配置文件"""
        config_data = {}
        
        # 加载基础配置
        base_config_file = self.config_dir / "config.yaml"
        if base_config_file.exists():
            config_data.update(self._load_yaml_file(base_config_file))
        
        # 加载环境特定配置
        env_config_file = self.config_dir / f"config.{self._environment.value}.yaml"
        if env_config_file.exists():
            env_config = self._load_yaml_file(env_config_file)
            config_data = self._deep_merge(config_data, env_config)
        
        # 加载本地配置（不提交到版本控制）
        local_config_file = self.config_dir / "config.local.yaml"
        if local_config_file.exists():
            local_config = self._load_yaml_file(local_config_file)
            config_data = self._deep_merge(config_data, local_config)
        
        return config_data
    
    def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """加载YAML配置文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logging.warning(f"无法加载配置文件 {file_path}: {e}")
            return {}
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并字典"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _apply_environment_defaults(self):
        """应用环境相关的默认配置"""
        if self._environment == Environment.DEVELOPMENT:
            self._config.debug = True
            self._config.api.reload = True
            self._config.logging.level = "DEBUG"
            self._config.logging.console_enabled = True
        
        elif self._environment == Environment.TESTING:
            self._config.debug = False
            self._config.api.reload = False
            self._config.logging.level = "WARNING"
            self._config.database.database = "test_xpu_ai.db"
        
        elif self._environment == Environment.PRODUCTION:
            self._config.debug = False
            self._config.api.reload = False
            self._config.api.workers = 4
            self._config.logging.level = "INFO"
            self._config.logging.console_enabled = False
    
    def _validate_config(self):
        """验证配置"""
        # 检查必需的API密钥
        if self._environment == Environment.PRODUCTION:
            if not self._config.ai.deepseek_api_key:
                logging.warning("生产环境建议配置DeepSeek API密钥")
            
            if not self._config.security.secret_key or len(self._config.security.secret_key) < 32:
                logging.warning("生产环境建议配置至少32位的安全密钥")
        
        # 检查端口冲突
        if self._config.api.port == self._config.mcp.server_port:
            raise ValueError("API端口和MCP服务端口不能相同")
    
    def _create_directories(self):
        """创建必要的目录"""
        directories = [
            Path(self._config.file.upload_dir),
            Path(self._config.file.documents_dir),
            Path(self._config.file.vector_db_dir),
            Path(self._config.logging.file_path).parent,
        ]
        
        for directory in directories:
            if not directory.is_absolute():
                directory = self.project_root / directory
            directory.mkdir(parents=True, exist_ok=True)
    
    def get_config(self) -> AppConfig:
        """获取当前配置"""
        if self._config is None:
            raise RuntimeError("配置尚未加载，请先调用load_config()")
        return self._config
    
    def reload_config(self) -> AppConfig:
        """重新加载配置"""
        return self.load_config(self._environment.value if self._environment else None)
    
    def export_config(self, file_path: Path, format: str = "yaml") -> None:
        """导出当前配置到文件"""
        if self._config is None:
            raise RuntimeError("配置尚未加载")
        
        config_dict = self._config.dict()
        
        if format.lower() == "yaml":
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
        elif format.lower() == "json":
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
        else:
            raise ValueError("支持的格式: yaml, json")

# 全局配置管理器实例
config_manager = ConfigManager()

# 便捷函数
def get_config() -> AppConfig:
    """获取应用配置"""
    return config_manager.get_config()

def load_config(environment: Optional[str] = None) -> AppConfig:
    """加载应用配置"""
    return config_manager.load_config(environment)