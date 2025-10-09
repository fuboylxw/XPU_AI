from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "ChatBI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # 项目根目录
    project_root: Path = Path(__file__).parent.parent
    
    # OpenAI配置
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "deepseek-chat")
    OPENAI_MODEL_BASE_URL: str = os.getenv("OPENAI_MODEL_BASE_URL", "https://api.openai.com/v1")
    OPENAI_TEMPERATURE: float = 0.7
    OPENAI_MAX_TOKENS: int = 2000
    
    # 向量数据库配置
    embedding_model: str = "text-embedding-ada-002"
    vector_db_dir: Path = Path(__file__).parent.parent / "vector_db"
    documents_dir: Path = Path(__file__).parent.parent / "documents"
    
    # 百度AI搜索配置
    baidu_ai_search_url: str = os.getenv("SEARCH_ENGINE_BASE_URL", "")
    baidu_ai_search_token: str = os.getenv("SEARCH_ENGINE_API_KEY", "")
    
    # 数据库配置
    DB_HOST: Optional[str] = None
    DB_PORT: Optional[str] = None
    DB_NAME: Optional[str] = None
    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = None

    # 搜索引擎配置
    SEARCH_ENGINE_BASE_URL: str = os.getenv("SEARCH_ENGINE_BASE_URL", "https://www.baidu.com/s")
    SEARCH_ENGINE_API_KEY: str = os.getenv("SEARCH_ENGINE_API_KEY", "")
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8501
    
    # 会话配置
    SESSION_TIMEOUT: int = 3600  # 1小时
    MAX_CONVERSATION_HISTORY: int = 50
    
    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = "./logs/chatbi.log"
    
    # Redis配置（替代传统数据库）
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "")  # 可选：直接使用Redis URL
    
    # 安全配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    
    # 数据库配置
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./chatbi.db")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# 全局配置实例
settings = Settings()