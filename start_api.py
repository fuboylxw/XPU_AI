#!/usr/bin/env python3
"""
API服务启动脚本
"""

import uvicorn
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from src.config.settings import Settings

def main():
    """启动API服务"""
    settings = Settings()
    
    print("🚀 启动新生信息问答API服务...")
    print(f"📍 项目根目录: {project_root}")
    print(f"🌐 服务地址: http://localhost:8316")
    print(f"📚 API文档: http://localhost:8316/docs")
    print(f"🔍 健康检查: http://localhost:8316/health")
    
    try:
        uvicorn.run(
            "api.main:app",
            host="localhost",
            port=8316,
            reload=True,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n👋 API服务已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()