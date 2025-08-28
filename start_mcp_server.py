"""
启动MCP服务器
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from src.mcp.server import main

if __name__ == "__main__":
    print("启动学校信息MCP服务器...")
    asyncio.run(main())