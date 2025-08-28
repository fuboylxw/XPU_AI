"""
项目配置管理
"""

from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Settings(BaseSettings):
    """应用配置类"""
    
    # 项目基础配置
    project_name: str = "新生信息问答Agent"
    version: str = "1.0.0"
    debug: bool = False
    
    # 日志配置
    log_level: str = "INFO"
    
    # 文件路径配置
    project_root: Path = Path(__file__).parent.parent.parent
    data_dir: Path = project_root / "data"
    documents_dir: Path = data_dir / "documents"
    vector_db_dir: Path = data_dir / "vector_db"
    logs_dir: Path = project_root / "logs"
    
    # DeepSeek API配置
    deepseek_api_key: Optional[str] = os.getenv("DEEPSEEK_API_KEY")
    deepseek_api_base: str = "https://api.deepseek.com/v1"
    model_name: str = "deepseek-chat"
    temperature: float = 0.7
    max_tokens: int = 2000
    
    # MCP配置
    mcp_server_name: str = "school-info-server"
    mcp_server_version: str = "1.0.0"
    mcp_server_port: int = 3000
    mcp_tools_enabled: bool = True
    
    # 嵌入模型配置
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    
    # RAG配置
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k_results: int = 5
    similarity_threshold: float = 0.7
    
    # 向量数据库配置
    vector_db_type: str = "faiss"  # faiss 或 chroma
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 创建必要的目录
        self.create_directories()
    
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
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # 允许额外字段（可选方案）
        # extra = "allow"