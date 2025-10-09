"""
MCP服务器实现
提供学校信息查询和网络搜索工具
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from mcp.server.fastmcp import FastMCP
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from src.config.settings import Settings
from src.utils.logger import setup_logger
from src.utils.web_search import WebSearchTool

# 创建FastMCP服务器实例
mcp = FastMCP("School Info Server")

# 初始化配置和工具
settings = Settings()
logger = setup_logger(settings)

# 模拟学校信息数据库
SCHOOL_INFO_DB = {
    "招生信息": [
        {"title": "2024年本科招生简章", "content": "西安工程大学2024年面向全国招生..."},
        {"title": "研究生招生政策", "content": "我校研究生招生采用统一考试制度..."}
    ],
    "专业介绍": [
        {"title": "纺织工程专业", "content": "纺织工程专业是我校王牌专业..."},
        {"title": "计算机科学与技术", "content": "计算机专业培养高素质技术人才..."}
    ],
    "校园生活": [
        {"title": "宿舍条件", "content": "学校提供4人间和6人间宿舍..."},
        {"title": "食堂介绍", "content": "校内有多个食堂，提供各地美食..."}
    ]
}

@mcp.tool()
def search_school_info(query: str, category: Optional[str] = None) -> str:
    """搜索学校信息
    
    Args:
        query: 搜索关键词
        category: 信息类别（招生信息、专业介绍、校园生活等）
    
    Returns:
        搜索结果
    """
    results = []
    
    # 如果指定了类别，只在该类别中搜索
    if category and category in SCHOOL_INFO_DB:
        search_data = {category: SCHOOL_INFO_DB[category]}
    else:
        search_data = SCHOOL_INFO_DB
    
    # 在数据中搜索
    for cat, items in search_data.items():
        for item in items:
            if query.lower() in item["title"].lower() or query.lower() in item["content"].lower():
                results.append(f"类别: {cat}\n标题: {item['title']}\n内容: {item['content']}")
    
    if results:
        return "\n\n".join(results)
    else:
        return f"未找到关于'{query}'的相关信息"

@mcp.tool()
def web_search(query: str, engine: str = "google", max_results: int = 5) -> str:
    """网络搜索工具
    
    Args:
        query: 搜索关键词
        engine: 搜索引擎（google、baidu、duckduckgo）
        max_results: 最大结果数量
    
    Returns:
        搜索结果
    """
    try:
        # 创建网络搜索工具实例
        search_tool = WebSearchTool(settings)
        
        # 执行同步搜索
        results = search_tool.search_sync(query, engine, max_results)
        
        if not results:
            return f"未找到关于'{query}'的网络搜索结果"
        
        # 格式化结果
        formatted_results = []
        for i, result in enumerate(results, 1):
            formatted_result = f"""{i}. 标题: {result['title']}
   来源: {result['source']}
   链接: {result['url']}
   摘要: {result['snippet'][:200]}..."""
            formatted_results.append(formatted_result)
        
        return "\n\n".join(formatted_results)
        
    except Exception as e:
        logger.error(f"网络搜索失败: {e}")
        return f"网络搜索失败: {str(e)}"

@mcp.tool()
def comprehensive_search(query: str, max_results: int = 8) -> str:
    """综合搜索工具（本地+网络）
    
    Args:
        query: 搜索关键词
        max_results: 最大结果数量
    
    Returns:
        综合搜索结果
    """
    results = []
    
    # 首先搜索本地学校信息
    local_results = search_school_info(query)
    if "未找到" not in local_results:
        results.append(f"=== 本地学校信息 ===\n{local_results}")
    
    # 然后进行网络搜索
    try:
        search_tool = WebSearchTool(settings)
        web_results = search_tool.search_sync(query, "google", max_results//2)
        
        if web_results:
            web_formatted = []
            for i, result in enumerate(web_results, 1):
                web_formatted.append(f"""{i}. {result['title']}
   来源: {result['source']}
   链接: {result['url']}
   摘要: {result['snippet'][:150]}...""")
            
            results.append(f"=== 网络搜索结果 ===\n" + "\n\n".join(web_formatted))
    
    except Exception as e:
        logger.error(f"网络搜索部分失败: {e}")
        results.append(f"网络搜索部分失败: {str(e)}")
    
    if results:
        return "\n\n" + "="*50 + "\n\n".join(results)
    else:
        return f"未找到关于'{query}'的任何信息"

@mcp.tool()
def get_document_summary(document_type: Optional[str] = None) -> str:
    """获取文档摘要
    
    Args:
        document_type: 文档类型
    
    Returns:
        文档摘要信息
    """
    if document_type and document_type in SCHOOL_INFO_DB:
        items = SCHOOL_INFO_DB[document_type]
        summary = f"{document_type}类别包含{len(items)}个文档:\n"
        for item in items:
            summary += f"- {item['title']}\n"
        return summary
    else:
        total_docs = sum(len(items) for items in SCHOOL_INFO_DB.values())
        summary = f"学校信息库总共包含{total_docs}个文档，分为以下类别:\n"
        for category, items in SCHOOL_INFO_DB.items():
            summary += f"- {category}: {len(items)}个文档\n"
        return summary

@mcp.tool()
def add_school_document(content: str, title: str, category: str = "其他") -> str:
    """添加学校文档
    
    Args:
        content: 文档内容
        title: 文档标题
        category: 文档类别
    
    Returns:
        添加结果
    """
    if category not in SCHOOL_INFO_DB:
        SCHOOL_INFO_DB[category] = []
    
    SCHOOL_INFO_DB[category].append({
        "title": title,
        "content": content
    })
    
    return f"成功添加文档'{title}'到'{category}'类别"

@mcp.tool()
def get_search_engines() -> str:
    """获取可用的搜索引擎列表
    
    Returns:
        可用搜索引擎信息
    """
    try:
        search_tool = WebSearchTool(settings)
        available_engines = search_tool.available_engines if hasattr(search_tool, 'available_engines') else ["google", "baidu", "duckduckgo"]
        
        engine_info = "可用的搜索引擎:\n"
        for engine in available_engines:
            engine_info += f"- {engine}\n"
        
        engine_info += "\n使用方法: web_search(query='搜索词', engine='引擎名称')"
        return engine_info
        
    except Exception as e:
        return f"获取搜索引擎信息失败: {str(e)}"

async def main():
    """启动MCP服务器"""
    try:
        logger.info("启动学校信息MCP服务器...")
        tools = await mcp.list_tools()
        logger.info(f"可用工具: {[tool.name for tool in tools]}")
        
        # 运行MCP服务器
        await mcp.run()
        
    except Exception as e:
        logger.error(f"MCP服务器启动失败: {e}")
        raise

if __name__ == "__main__":
    # 检查是否已有事件循环在运行
    try:
        loop = asyncio.get_running_loop()
        # 如果已有事件循环，使用 create_task
        import nest_asyncio
        nest_asyncio.apply()
        asyncio.run(main())
    except RuntimeError:
        # 没有运行的事件循环，正常启动
        asyncio.run(main())