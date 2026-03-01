"""
配置设置模块
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from pathlib import Path

# 加载环境变量（强制覆盖系统环境变量），明确指向项目根目录的 .env
DOTENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=str(DOTENV_PATH), override=True)

class Settings:
    """应用配置类"""
    
    def __init__(self):
        # 项目根目录
        self.BASE_DIR = Path(__file__).resolve().parent.parent
        self.project_root = self.BASE_DIR
        # OpenAI配置
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        # 关键修复：读取 .env 中的 OPENAI_MODEL_BASE_URL，而不是 OPENAI_BASE_URL
        self.OPENAI_MODEL_BASE_URL = os.getenv("OPENAI_MODEL_BASE_URL", "https://api.openai.com/v1")
        self.OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        self.OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
        self.OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "2000"))
        
        # 搜索引擎配置
        self.SEARCH_ENGINE_BASE_URL = os.getenv("SEARCH_ENGINE_BASE_URL", "")
        self.SEARCH_ENGINE_API_KEY = os.getenv("SEARCH_ENGINE_API_KEY", "")
        
        # 百度AI搜索配置
        self.baidu_ai_search_url = os.getenv("SEARCH_ENGINE_BASE_URL", "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions_pro")
        self.baidu_ai_search_token = os.getenv("SEARCH_ENGINE_API_KEY", "")
        
        # 数据库配置
        self.DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/chatbi.db")
        
        # MySQL数据库配置
        self.MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
        self.MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
        self.MYSQL_DATABASE = os.getenv("MYSQL_DB", "chatbot")
        self.MYSQL_USER = os.getenv("MYSQL_USER", "root")
        self.MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
        
        # Redis配置
        self.REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
        self.REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
        self.REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
        self.REDIS_DB = int(os.getenv("REDIS_DB", "0"))
        
        # PostgreSQL配置
        self.POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
        self.POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
        self.POSTGRES_DB = os.getenv("POSTGRES_DB", "postgres")
        self.POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
        self.POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
        self.POSTGRES_DATABASE_URL = os.getenv("POSTGRES_DATABASE_URL", "")
        
        # Qdrant配置
        self.QDRANT_URL = os.getenv("QDRANT_URL", "")
        self.QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
        self.QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
        self.QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
        self.QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "knowledge_base")
        self.EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
        
        # 语音识别参数
        self.VOICE_RECOGNITION_API_URL = os.getenv("VOICE_RECOGNITION_API_URL", "https://vop.baidu.com/server_api")
        self.VOICE_RECOGNITION_API_KEY = os.getenv("VOICE_RECOGNITION_API_KEY", "")
        self.VOICE_AUDIO_FORMAT = os.getenv("VOICE_AUDIO_FORMAT", "paInt16")
        self.VOICE_AUDIO_CHANNELS = int(os.getenv("VOICE_AUDIO_CHANNELS", "1"))
        self.VOICE_AUDIO_RATE = int(os.getenv("VOICE_AUDIO_RATE", "16000"))
        self.VOICE_AUDIO_CHUNK = int(os.getenv("VOICE_AUDIO_CHUNK", "1024"))
        self.VOICE_RECORD_SECONDS = int(os.getenv("VOICE_RECORD_SECONDS", "10"))
        self.VOICE_SILENCE_THRESHOLD = int(os.getenv("VOICE_SILENCE_THRESHOLD", "500"))
        self.VOICE_SILENCE_DURATION = float(os.getenv("VOICE_SILENCE_DURATION", "2.0"))
        self.VOICE_ENABLE_NOISE_REDUCTION = os.getenv("VOICE_ENABLE_NOISE_REDUCTION", "true").lower() == "true"
        self.VOICE_ENABLE_AUDIO_ENHANCEMENT = os.getenv("VOICE_ENABLE_AUDIO_ENHANCEMENT", "true").lower() == "true"
        self.VOICE_NOISE_REDUCTION_STRENGTH = float(os.getenv("VOICE_NOISE_REDUCTION_STRENGTH", "0.5"))
        self.VOICE_HIGH_PASS_CUTOFF = float(os.getenv("VOICE_HIGH_PASS_CUTOFF", "80.0"))
        self.VOICE_LOW_PASS_CUTOFF = float(os.getenv("VOICE_LOW_PASS_CUTOFF", "8000.0"))
        
        # 语音合成参数（TTS）
        self.TTS_API_URL = os.getenv("TTS_API_URL", "https://tsn.baidu.com/text2audio")
        self.TTS_API_KEY = os.getenv("TTS_API_KEY", "")
        self.TTS_FORMAT = os.getenv("TTS_FORMAT", "mp3-16k")
        self.TTS_LANG = os.getenv("TTS_LANG", "zh")
        self.TTS_SPEED = int(os.getenv("TTS_SPEED", "5"))
        self.TTS_PITCH = int(os.getenv("TTS_PITCH", "5"))
        self.TTS_VOLUME = int(os.getenv("TTS_VOLUME", "5"))
        self.TTS_PER = int(os.getenv("TTS_PER", "0"))
        self.TTS_AUE = int(os.getenv("TTS_AUE", "3"))
        self.TTS_OUTPUT_DIR = os.getenv("TTS_OUTPUT_DIR", "./audio_output")
        self.TTS_ENABLE_SUBTITLE = int(os.getenv("TTS_ENABLE_SUBTITLE", "0"))
        
        # 应用配置
        self.APP_NAME = "ChatBI"
        self.APP_VERSION = "1.0.0"
        self.DEBUG = os.getenv("DEBUG", "False").lower() == "true"

        # MCP 网络配置（用于 cline 连接 MCP Server）
        self.MCP_HOST = os.getenv("MCP_HOST", "127.0.0.1")
        self.MCP_PORT = int(os.getenv("MCP_PORT", "8765"))
        
        # 模型配置
        self.MAX_CONVERSATION_HISTORY = 50
        self.MODELS_CACHE_DIR = os.getenv("MODELS_CACHE_DIR", str(self.BASE_DIR / "models_cache"))
        
        # 日志配置
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_FILE = os.getenv("LOG_FILE", "logs/chatbi.log")

        # 对话标题监听配置
        self.TITLE_CHECK_INTERVAL = int(os.getenv("TITLE_CHECK_INTERVAL", "300"))
        self.TITLE_IDLE_THRESHOLD = int(os.getenv("TITLE_IDLE_THRESHOLD", "600"))

        self.WECHAT_CORP_ID = os.getenv("WECHAT_CORP_ID", "")
        self.WECHAT_CORP_SECRET = os.getenv("WECHAT_CORP_SECRET", "")
        self.WECHAT_AGENT_ID = os.getenv("WECHAT_AGENT_ID", "")
        self.WECHAT_DEFAULT_USER = os.getenv("WECHAT_DEFAULT_USER", "")

        # 流式思考控制（SSE负载优化）
        self.STREAM_THINKING_ENABLED = os.getenv("STREAM_THINKING_ENABLED", "true").lower() == "true"
        self.STREAM_DECISION_ONLY = os.getenv("STREAM_DECISION_ONLY", "false").lower() == "true"
        self.STREAM_THINKING_THROTTLE_MS = int(os.getenv("STREAM_THINKING_THROTTLE_MS", "120"))
        self.STREAM_THINKING_MAX_BUFFER = int(os.getenv("STREAM_THINKING_MAX_BUFFER", "400"))

        # ReAct 执行控制
        self.REACT_MAX_ATTEMPTS = int(os.getenv("REACT_MAX_ATTEMPTS", "6"))
        self.REACT_INCLUDE_TRACE = os.getenv("REACT_INCLUDE_TRACE", "false").lower() == "true"
        self.REACT_ALLOW_FALLBACK_SYNTHESIS = os.getenv("REACT_ALLOW_FALLBACK_SYNTHESIS", "true").lower() == "true"
        self.REACT_MAX_CONSECUTIVE_INVALID = int(os.getenv("REACT_MAX_CONSECUTIVE_INVALID", "2"))
        self.REACT_PROGRESS_INCLUDE_THINKING_DEFAULT = (
            os.getenv("REACT_PROGRESS_INCLUDE_THINKING_DEFAULT", "false").lower() == "true"
        )

# 创建全局设置实例
settings = Settings()
