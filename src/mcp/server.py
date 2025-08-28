"""
MCP服务器实现
提供学校信息查询工具
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from mcp.server.fastmcp import FastMCP
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from src.config.settings import Settings
from src.utils.logger import setup_logger

# 创建FastMCP服务器实例
mcp = FastMCP("School Info Server")

# 模拟学校信息数据库
SCHOOL_INFO_DB = {
    "招生信息": [
        {"title": "2024年本科招生简章", "content": "西安石油大学2024年面向全国招生..."},
        {"title": "研究生招生政策", "content": "我校研究生招生采用统一考试制度..."}
    ],
    "专业介绍": [
        {"title": "石油工程专业", "content": "石油工程专业是我校王牌专业..."},
        {"title": "计算机科学与技术", "content": "计算机专业培养高素质技术人才..."}
    ],
    "校园生活": [
        {"title": "宿舍条件", "content": "学校提供4人间和6人间宿舍..."},
        {"title": "食堂介绍", "content": "校内有多个食堂，提供各地美食..."}
    ]
}

@mcp.tool
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

@mcp.tool
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

@mcp.tool
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

if __name__ == "__main__":
    # 运行MCP服务器
    mcp.run()