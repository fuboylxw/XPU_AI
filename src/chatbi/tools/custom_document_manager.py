"""
自定义文档管理模块
确保从Knowledge文件夹检索文档并修复源路径显示问题
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.chatbi.tools.document_manager import DocumentManager
from config.settings import settings
from src.chatbi.utils.logger import setup_logger

class CustomDocumentManager(DocumentManager):
    """自定义文档管理器，确保从Knowledge文件夹检索文档"""
    
    def __init__(self):
        """初始化自定义文档管理器"""
        # 在初始化父类之前修改settings中的documents_dir
        # 强制设置文档目录为Knowledge文件夹
        settings.documents_dir = Path(os.path.join(os.getcwd(), "Knowledge"))
        self.logger = setup_logger("custom_document_manager")
        self.logger.info(f"使用自定义知识库路径: {settings.documents_dir}")
        
        # 调用父类初始化
        super().__init__()
    
    async def search_documents(self, query: str, category: Optional[str] = None, top_k: int = None) -> Dict[str, Any]:
        """重写搜索方法，确保只搜索Knowledge文件夹中的文件并修复源路径显示"""
        # 调用父类的搜索方法
        results = await super().search_documents(query, category, top_k)
        
        # 修改结果中的文档路径，只保留文件名
        documents = results.get("documents", [])
        for doc in documents:
            if "source" in doc:
                source_path = Path(doc["source"])
                # 只保留文件名
                doc["source"] = source_path.name
        
        return {
            "documents": documents,
            "total_found": len(documents),
            "search_method": results.get("search_method", "semantic_search"),
            "query_used": results.get("query_used", query)
        }