"""
校园信息查询智能体模块
实现基于知识库的校园信息查询、文档检索功能
"""

import json
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path

from config.settings import settings
from src.chatbi.tools.document_manager import DocumentManager
from src.chatbi.utils.logger import setup_logger

logger = setup_logger("knowledge_query_agent")

class KnowledgeQueryAgent:
    """校园信息查询智能体"""
    
    def __init__(self):
        """初始化校园信息查询智能体"""
        # 初始化文档管理器
        self.document_manager = DocumentManager()
        
        # 初始化知识库结构
        self._initialize_knowledge_base()
        
        # 查询历史和缓存
        self.query_history = []
        self.query_cache = {}
    
    def _initialize_knowledge_base(self):
        """初始化知识库结构"""
        self.knowledge_categories = {
            "学校概况": {
                "description": "西安工程大学基本信息、历史沿革、办学特色",
                "keywords": ["学校介绍", "历史", "概况", "特色", "校训"],
                "priority": 1
            },
            "学院专业": {
                "description": "各学院介绍、专业设置、培养方案",
                "keywords": ["学院", "专业", "培养方案", "课程设置"],
                "priority": 2
            },
            "招生信息": {
                "description": "招生政策、录取分数线、报考指南",
                "keywords": ["招生", "录取", "分数线", "报考", "入学"],
                "priority": 2
            },
            "教务管理": {
                "description": "课程安排、选课指南、考试制度、成绩管理",
                "keywords": ["课程", "选课", "考试", "成绩", "学分"],
                "priority": 3
            },
            "学生事务": {
                "description": "学籍管理、奖助学金、评优评奖、处分规定",
                "keywords": ["学籍", "奖学金", "助学金", "评优", "处分"],
                "priority": 3
            },
            "校园生活": {
                "description": "宿舍管理、饮食服务、校园卡、网络服务",
                "keywords": ["宿舍", "饮食", "校园卡", "网络", "生活"],
                "priority": 4
            },
            "规章制度": {
                "description": "校规校纪、管理办法、各类制度文件",
                "keywords": ["校规", "制度", "办法", "规定", "文件"],
                "priority": 3
            },
            "就业指导": {
                "description": "就业政策、实习安排、职业规划、招聘信息",
                "keywords": ["就业", "实习", "职业", "招聘", "工作"],
                "priority": 4
            }
        }
        
        # 预设常见问题和答案
        self.faq_database = {
            "学校地址": "西安工程大学位于陕西省西安市，主校区在金花南路19号",
            "学校性质": "西安工程大学是一所以工为主，纺织、服装为特色的多科性大学",
            "联系电话": "学校招生咨询电话：029-82330087",
            "学校网站": "西安工程大学官方网站：http://www.xpu.edu.cn",
            "邮政编码": "710048"
        }
    
    async def query_knowledge(self, question: str, use_cache: bool = True) -> Dict[str, Any]:
        """查询校园知识库"""
        try:
            logger.info(f"开始知识库查询: {question[:50]}...")
            
            # 1. 检查缓存
            if use_cache and question in self.query_cache:
                logger.info("使用缓存结果")
                cached_result = self.query_cache[question]
                cached_result["from_cache"] = True
                return cached_result
            
            # 2. 提取关键词
            keywords = self._extract_keywords(question)
            
            # 3. 确定优先搜索类别
            priority_categories = self._determine_priority_categories(question, keywords)
            
            # 4. 搜索知识库
            kb_results = await self._search_knowledge_base(question, keywords)
            
            # 5. 搜索文档
            doc_results = await self._search_documents(question, keywords, priority_categories)
            
            # 6. 结果整理和缓存
            result = {
                "question": question,
                "sources": {
                    "knowledge_base": kb_results,
                    "documents": doc_results
                },
                "search_analysis": {
                    "keywords": keywords,
                    "priority_categories": priority_categories
                },
                "timestamp": datetime.now().isoformat(),
                "from_cache": False
            }
            
            # 缓存结果
            if use_cache:
                self.query_cache[question] = result.copy()
                # 限制缓存大小
                if len(self.query_cache) > 100:
                    oldest_key = min(self.query_cache.keys())
                    del self.query_cache[oldest_key]
            
            # 记录查询历史
            self._log_query(question, result)
            
            return result
            
        except Exception as e:
            logger.error(f"知识库查询失败: {e}")
            return {
                "question": question,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _extract_keywords(self, question: str) -> List[str]:
        """从问题中提取关键词"""
        # 简单分词，实际应用中可以使用更复杂的分词算法
        words = question.split()
        
        # 过滤掉常见停用词
        stopwords = ["的", "是", "在", "有", "和", "与", "什么", "如何", "怎么", "请问"]
        keywords = [word for word in words if word not in stopwords and len(word) > 1]
        
        # 如果没有提取到关键词，返回原始问题中的所有词
        if not keywords:
            keywords = words
            
        return keywords
    
    def _determine_priority_categories(self, question: str, keywords: List[str]) -> List[str]:
        """确定优先搜索的知识类别"""
        category_scores = {}
        
        # 为每个类别计算匹配分数
        for category, info in self.knowledge_categories.items():
            score = 0
            category_keywords = info["keywords"]
            
            # 检查问题中是否包含类别关键词
            for kw in category_keywords:
                if kw in question:
                    score += 2
            
            # 检查提取的关键词是否匹配类别关键词
            for kw in keywords:
                if any(ckw in kw or kw in ckw for ckw in category_keywords):
                    score += 1
            
            if score > 0:
                category_scores[category] = score
        
        # 如果没有匹配的类别，返回默认类别
        if not category_scores:
            return ["学校概况"]
        
        # 按分数排序并返回前3个类别
        sorted_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
        return [category for category, _ in sorted_categories[:3]]
    
    async def _search_knowledge_base(self, question: str, keywords: List[str]) -> Dict[str, Any]:
        """搜索内置知识库"""
        results = {
            "faq_matches": [],
            "category_matches": [],
            "keyword_matches": []
        }
        
        # 1. 搜索FAQ数据库
        for faq_key, faq_answer in self.faq_database.items():
            if any(keyword in question for keyword in faq_key.split()):
                results["faq_matches"].append({
                    "question": faq_key,
                    "answer": faq_answer,
                    "relevance": 0.9
                })
        
        # 2. 搜索知识类别
        for category, info in self.knowledge_categories.items():
            category_keywords = info["keywords"]
            matches = [kw for kw in keywords if any(ckw in kw for ckw in category_keywords)]
            
            if matches:
                results["category_matches"].append({
                    "category": category,
                    "description": info["description"],
                    "matched_keywords": matches,
                    "priority": info["priority"],
                    "relevance": len(matches) / len(category_keywords)
                })
        
        # 3. 关键词匹配
        for keyword in keywords:
            for category, info in self.knowledge_categories.items():
                if keyword in info["description"] or any(keyword in kw for kw in info["keywords"]):
                    results["keyword_matches"].append({
                        "keyword": keyword,
                        "category": category,
                        "relevance": 0.7
                    })
        
        return results
    
    async def _search_documents(self, question: str, keywords: List[str], priority_categories: List[str]) -> Dict[str, Any]:
        """搜索文档库"""
        try:
            # 确保文档管理器已初始化
            if not self.document_manager.vector_db or self.document_manager.vector_db.ntotal == 0:
                logger.warning("文档向量数据库为空，尝试重新加载数据")
                self.document_manager._load_existing_data()
            
            # 增强搜索查询
            enhanced_query = question
            if keywords:
                # 将关键词添加到查询中以增强搜索效果
                enhanced_query = f"{question} {' '.join(keywords)}"
            
            # 如果有优先类别，按类别搜索
            if priority_categories:
                doc_results = []
                for category in priority_categories:
                    category_docs = await self.document_manager.search_documents(
                        query=enhanced_query,
                        category=category,
                        top_k=5  # 增加返回结果数量
                    )
                    # 处理返回结果格式
                    if isinstance(category_docs, dict) and "documents" in category_docs:
                        doc_results.extend(category_docs["documents"])
                    else:
                        doc_results.extend(category_docs)
            else:
                # 通用搜索，不限制类别
                doc_results = await self.document_manager.search_documents(
                    query=enhanced_query,
                    top_k=10  # 增加返回结果数量
                )
                # 处理返回结果格式
                if isinstance(doc_results, dict) and "documents" in doc_results:
                    doc_results = doc_results["documents"]
            
            # 如果没有找到结果，尝试直接使用关键词搜索
            if not doc_results and keywords:
                logger.info(f"使用关键词直接搜索: {keywords}")
                for keyword in keywords:
                    keyword_docs = await self.document_manager.search_documents(
                        query=keyword,
                        top_k=5
                    )
                    # 处理返回结果格式
                    if isinstance(keyword_docs, dict) and "documents" in keyword_docs:
                        doc_results.extend(keyword_docs["documents"])
                    else:
                        doc_results.extend(keyword_docs)
            
            # 去重
            unique_docs = {}
            for doc in doc_results:
                doc_id = doc.get('doc_id')
                if doc_id not in unique_docs or doc.get('score', 0) > unique_docs[doc_id].get('score', 0):
                    # 修改文档源路径，只保留文件名
                    if "source" in doc:
                        from pathlib import Path
                        source_path = Path(doc["source"])
                        doc["source"] = source_path.name
                    unique_docs[doc_id] = doc
            
            return {
                "documents": list(unique_docs.values()),
                "total_found": len(unique_docs),
                "search_method": "enhanced_semantic_search",
                "query_used": enhanced_query
            }
            
        except Exception as e:
            logger.error(f"文档搜索失败: {e}")
            return {
                "documents": [],
                "total_found": 0,
                "error": str(e)
            }
    
    def _log_query(self, question: str, result: Dict[str, Any]):
        """记录查询历史"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "sources_used": list(result.get("sources", {}).keys()),
            "from_cache": result.get("from_cache", False),
            "query_id": f"query_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
        
        self.query_history.append(log_entry)
        logger.info(f"知识查询完成: {log_entry}")
        
        # 保持历史记录在合理范围内
        if len(self.query_history) > 1000:
            self.query_history = self.query_history[-500:]
    
    async def add_knowledge(self, category: str, title: str, content: str) -> Dict[str, Any]:
        """添加知识到知识库"""
        try:
            # 使用文档管理器添加文档
            doc_id = await self.document_manager.add_document(
                file_content=content,
                filename=f"{title}.txt",
                category=category
            )
            
            logger.info(f"成功添加知识: {title} 到类别 {category}")
            return {
                "success": True,
                "document_id": doc_id,
                "category": category,
                "title": title
            }
            
        except Exception as e:
            logger.error(f"添加知识失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_query_statistics(self) -> Dict[str, Any]:
        """获取查询统计信息"""
        if not self.query_history:
            return {"message": "暂无查询记录"}
        
        total_queries = len(self.query_history)
        cache_hits = sum(1 for log in self.query_history if log.get("from_cache", False))
        
        return {
            "total_queries": total_queries,
            "cache_hit_rate": f"{(cache_hits/total_queries)*100:.2f}%" if total_queries > 0 else "0%",
            "cache_size": len(self.query_cache),
            "recent_queries": self.query_history[-10:]
        }
    
    def clear_cache(self):
        """清空查询缓存"""
        self.query_cache.clear()
        logger.info("查询缓存已清空")