#!/usr/bin/env python3
"""
完整的稀疏检索工具 - 支持PostgreSQL BM25关键词查询
包含中文分词、停用词过滤、关键词合并等完整功能

Author: Assistant
Date: 2024-12-30
"""

import os
import re
import logging
import asyncpg
import jieba
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from config.settings import settings

# 中文停用词列表
CHINESE_STOPWORDS = {
    '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', 
    '会', '着', '没有', '看', '好', '自己', '这', '那', '里', '就是', '还', '把', '比', '或者', '虽然', '因为', '所以', '但是', 
    '然后', '如果', '这样', '那样', '什么', '怎么', '为什么', '哪里', '哪个', '多少', '几个', '第一', '可以', '应该', '能够',
    '已经', '正在', '将要', '可能', '或许', '大概', '也许', '当然', '确实', '真的', '实际', '基本', '主要', '重要', '一般',
    '特别', '非常', '十分', '相当', '比较', '更加', '最', '太', '挺', '还是', '总是', '经常', '有时', '偶尔', '从来',
    '刚刚', '马上', '立即', '现在', '以前', '以后', '今天', '明天', '昨天', '这里', '那里', '哪里', '到处', '处处'
}

@dataclass
class PostgreSQLConfig:
    """PostgreSQL配置（统一从settings读取）"""
    host: str = settings.POSTGRES_HOST
    port: int = settings.POSTGRES_PORT
    database: str = settings.POSTGRES_DB
    user: str = settings.POSTGRES_USER
    password: str = settings.POSTGRES_PASSWORD

@dataclass
class Document:
    """文档数据结构"""
    id: str
    title: str
    content: str
    category: str = ""
    summary: str = ""
    keywords: List[str] = None
    embedding: str = ""
    metadata: Dict[str, Any] = None
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.keywords is None:
            self.keywords = []

@dataclass
class SearchResult:
    """搜索结果数据结构"""
    doc_id: str
    title: str
    content: str
    category: str
    score: float
    rank: int
    summary: str = ""
    keywords: List[str] = None
    embedding: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.keywords is None:
            self.keywords = []

class TextProcessor:
    """文本处理工具类"""
    
    # 学校相关自定义词汇
    CUSTOM_WORDS = [
        # 部门和机构
        "网信处", "网络与信息化管理处", "信息化管理处", "网络管理处",
        "教务处", "学生处", "研究生院", "招生办", "就业指导中心",
        "图书馆", "后勤处", "保卫处", "财务处", "人事处", "科研处",
        "国际交流处", "继续教育学院", "体育部", "马克思主义学院",
        
        # 职务和职称
        "处长", "副处长", "科长", "主任", "副主任", "院长", "副院长",
        "书记", "副书记", "主席", "副主席", "部长", "副部长",
        "网信处处长", "教务处处长", "学生处处长", "信息化处长",
        
        # 学院和专业
        "纺织学院", "机电工程学院", "电子信息学院", "计算机科学学院",
        "理学院", "人文社会科学学院", "艺术工程学院", "服装与艺术设计学院",
        "管理学院", "环境与化学工程学院", "材料工程学院", "城市规划与市政工程学院",
        
        # 校区和地点
        "金花校区", "临潼校区", "西安工程大学", "工程大学",
        
        # 学术和教学
        "本科生", "研究生", "博士生", "硕士生", "学士学位", "硕士学位", "博士学位",
        "奖学金", "助学金", "学费", "住宿费", "选课", "退课", "补考", "重修",
        "毕业设计", "学位论文", "答辩", "实习", "实训", "课程设计",
        
        # 其他常用词汇
        "联系方式", "联系电话", "办公地址", "办公时间", "工作时间",
        "招生简章", "录取分数线", "专业介绍", "培养方案", "课程安排"
    ]
    
    @classmethod
    def _initialize_jieba(cls):
        """初始化jieba分词器，添加自定义词汇"""
        for word in cls.CUSTOM_WORDS:
            jieba.add_word(word)
    
    @staticmethod
    def segment_text(text: str) -> List[str]:
        """中文分词"""
        if not text or not text.strip():
            return []
        
        # 确保jieba已经初始化自定义词汇
        TextProcessor._initialize_jieba()
        
        # 使用jieba进行中文分词
        words = list(jieba.cut(text.strip()))
        
        # 过滤空字符串和单字符（除了有意义的单字）
        meaningful_single_chars = {'网', '信', '息', '化', '管', '理', '处', '长', '院', '校', '系', '部', '科', '技', '学', '教', '研'}
        filtered_words = []
        for word in words:
            word = word.strip()
            if len(word) > 1 or (len(word) == 1 and word in meaningful_single_chars):
                filtered_words.append(word)
        
        return filtered_words
    
    @staticmethod
    def remove_stopwords(words: List[str]) -> List[str]:
        """停用词过滤"""
        return [word for word in words if word not in CHINESE_STOPWORDS and len(word.strip()) > 0]
    
    @staticmethod
    def merge_keywords(segmented_words: List[str], additional_keywords: List[str]) -> tuple[List[str], List[str]]:
        """
        合并关键词并去重，同时识别重合关键词
        
        Returns:
            tuple: (所有关键词列表, 重合关键词列表)
        """
        # 将分词后的关键词转换为集合
        segmented_set = set(segmented_words)
        all_keywords = set(segmented_words)
        overlap_keywords = []
        
        # 添加额外的关键词并识别重合部分
        for keyword in additional_keywords:
            if keyword and keyword.strip():
                # 对额外关键词也进行分词处理
                extra_words = TextProcessor.segment_text(keyword.strip())
                extra_words = TextProcessor.remove_stopwords(extra_words)
                
                # 检查重合关键词
                for word in extra_words:
                    if word in segmented_set:
                        overlap_keywords.append(word)
                
                all_keywords.update(extra_words)
        
        # 去重重合关键词列表
        overlap_keywords = list(set(overlap_keywords))
        
        # 返回去重后的关键词列表（按长度排序，长词优先）和重合关键词列表
        final_keywords = sorted(list(all_keywords), key=len, reverse=True)
        return final_keywords, overlap_keywords
    
    @staticmethod
    def build_tsquery(keywords: List[str]) -> str:
        """构建PostgreSQL tsquery查询字符串"""
        if not keywords:
            return ""
        
        # 对关键词进行转义，避免特殊字符问题
        escaped_keywords = []
        for keyword in keywords:
            # 移除特殊字符，只保留中文、英文、数字
            clean_keyword = re.sub(r'[^\w\u4e00-\u9fff]', '', keyword)
            if clean_keyword:
                escaped_keywords.append(clean_keyword)
        
        if not escaped_keywords:
            return ""
        
        # 使用OR连接所有关键词，提高召回率
        return ' | '.join(escaped_keywords)

class PostgreSQLSearcher:
    """PostgreSQL BM25搜索器 - 支持完整的中文文本处理"""
    
    def __init__(self, config: PostgreSQLConfig):
        self.config = config
        self.connection = None
        self.logger = logging.getLogger(__name__)
        self.text_processor = TextProcessor()
    
    async def connect(self) -> bool:
        """连接数据库"""
        try:
            self.connection = await asyncpg.connect(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password
            )
            self.logger.info("PostgreSQL连接成功")
            return True
        except Exception as e:
            self.logger.error(f"PostgreSQL连接失败: {e}")
            return False
    
    async def disconnect(self):
        """断开数据库连接"""
        if self.connection:
            await self.connection.close()
            self.connection = None
    
    async def search_by_question_and_keywords(self, question: str, keywords: List[str] = None, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        通过问题和关键词进行稀疏检索
        
        Args:
            question: 输入的问题文本
            keywords: 额外的关键词列表（可选）
            top_k: 返回的文档数量
            
        Returns:
            List[Tuple[str, float]]: 文档ID和相关性得分的列表
        """
        if not self.connection:
            raise Exception("数据库未连接")
        
        if not question or not question.strip():
            return []
        
        try:
            # 检查documents表是否存在
            table_exists = await self.connection.fetchval(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'documents')"
            )
            
            if not table_exists:
                self.logger.warning("documents表不存在，无法执行搜索")
                return []
            
            # 步骤1: 对问题进行中文分词
            self.logger.info(f"开始处理问题: '{question}'")
            segmented_words = self.text_processor.segment_text(question)
            self.logger.info(f"分词结果: {segmented_words}")
            
            # 步骤2: 停用词过滤
            filtered_words = self.text_processor.remove_stopwords(segmented_words)
            self.logger.info(f"停用词过滤后: {filtered_words}")
            
            # 步骤3: 与传入关键词合并去重，并识别重合关键词
            if keywords is None:
                keywords = []
            final_keywords, overlap_keywords = self.text_processor.merge_keywords(filtered_words, keywords)
            self.logger.info(f"最终关键词: {final_keywords}")
            self.logger.info(f"重合关键词: {overlap_keywords}")
            
            if not final_keywords:
                self.logger.warning("没有有效的关键词，无法执行搜索")
                return []
            
            # 步骤4: 生成tsquery查询
            tsquery_str = self.text_processor.build_tsquery(final_keywords)
            self.logger.info(f"生成的tsquery: '{tsquery_str}'")
            
            if not tsquery_str:
                self.logger.warning("无法生成有效的tsquery")
                return []
            
            # 步骤5: 执行多策略搜索，传入重合关键词信息
            results = await self._execute_multi_strategy_search(tsquery_str, final_keywords, overlap_keywords, top_k)
            
            self.logger.info(f"搜索完成，返回 {len(results)} 个结果")
            return results
            
        except Exception as e:
            self.logger.error(f"搜索过程中发生错误: {e}")
            return []
    
    async def _execute_multi_strategy_search(self, tsquery_str: str, keywords: List[str], overlap_keywords: List[str], top_k: int) -> List[Tuple[str, float]]:
        """
        执行多策略搜索，为重合关键词的结果提高权重
        
        Args:
            tsquery_str: 全文搜索查询字符串
            keywords: 所有关键词列表
            overlap_keywords: 重合关键词列表（分词后关键词与传入关键词的重合部分）
            top_k: 返回结果数量
        """
        
        # 计算重合关键词权重提升系数
        overlap_boost = 1.5 if overlap_keywords else 1.0
        self.logger.info(f"重合关键词权重提升系数: {overlap_boost}")
        
        # 策略1: 使用全文搜索（优先中文，回退到简单配置）
        try:
            # 首先尝试中文配置
            fts_results = await self.connection.fetch("""
                SELECT 
                    id,
                    ts_rank_cd(ts_content, plainto_tsquery('chinese', $1), 32) as score
                FROM documents
                WHERE ts_content @@ plainto_tsquery('chinese', $1)
                ORDER BY score DESC
                LIMIT $2
            """, tsquery_str, top_k)
            
            if fts_results:
                results = []
                for row in fts_results:
                    base_score = float(row['score'])
                    # 检查文档是否包含重合关键词，如果包含则提升权重
                    enhanced_score = await self._calculate_enhanced_score(row['id'], base_score, overlap_keywords, overlap_boost)
                    results.append((row['id'], enhanced_score))
                
                # 重新排序结果
                results.sort(key=lambda x: x[1], reverse=True)
                self.logger.info(f"中文全文搜索成功: 返回 {len(results)} 个结果")
                return results
                
        except Exception as e:
            self.logger.warning(f"中文全文搜索失败: {e}")
            
        # 如果中文配置失败，尝试简单配置
        try:
            fts_results = await self.connection.fetch("""
                SELECT 
                    id,
                    ts_rank_cd(ts_content, plainto_tsquery('simple', $1), 32) as score
                FROM documents
                WHERE ts_content @@ plainto_tsquery('simple', $1)
                ORDER BY score DESC
                LIMIT $2
            """, tsquery_str, top_k)
            
            if fts_results:
                results = []
                for row in fts_results:
                    base_score = float(row['score'])
                    # 检查文档是否包含重合关键词，如果包含则提升权重
                    enhanced_score = await self._calculate_enhanced_score(row['id'], base_score, overlap_keywords, overlap_boost)
                    results.append((row['id'], enhanced_score))
                
                # 重新排序结果
                results.sort(key=lambda x: x[1], reverse=True)
                self.logger.info(f"简单全文搜索成功: 返回 {len(results)} 个结果")
                return results
                
        except Exception as e2:
            self.logger.warning(f"简单全文搜索失败: {e2}")
        
        # 策略2: 关键词分词搜索（改进的BM25评分，增强重合关键词权重）
        try:
            if keywords:
                # 构建动态SQL查询，为每个关键词创建ILIKE条件
                title_conditions = []
                content_conditions = []
                params = []
                
                for i, keyword in enumerate(keywords):
                    param_idx = i + 1
                    title_conditions.append(f"title ILIKE ${param_idx}")
                    content_conditions.append(f"content ILIKE ${param_idx}")
                    params.append(f'%{keyword}%')
                
                title_condition = " OR ".join(title_conditions)
                content_condition = " OR ".join(content_conditions)
                
                query = f"""
                    SELECT 
                        id,
                        CASE 
                            WHEN ({title_condition}) AND ({content_condition}) THEN 5.0
                            WHEN ({title_condition}) THEN 3.0
                            WHEN ({content_condition}) THEN 1.0
                            ELSE 0.0
                        END as score
                    FROM documents
                    WHERE ({title_condition}) OR ({content_condition})
                    ORDER BY score DESC
                    LIMIT ${len(params) + 1}
                """
                
                params.append(top_k)
                keyword_results = await self.connection.fetch(query, *params)
                
                if keyword_results:
                    results = []
                    for row in keyword_results:
                        if row['score'] > 0:
                            base_score = float(row['score'])
                            # 检查文档是否包含重合关键词，如果包含则提升权重
                            enhanced_score = await self._calculate_enhanced_score(row['id'], base_score, overlap_keywords, overlap_boost)
                            results.append((row['id'], enhanced_score))
                    
                    if results:
                        # 重新排序结果
                        results.sort(key=lambda x: x[1], reverse=True)
                        self.logger.info(f"关键词分词搜索成功: 返回 {len(results)} 个结果")
                        return results
                        
        except Exception as e:
            self.logger.warning(f"关键词分词搜索失败: {e}")
        
        # 策略3: 模糊匹配搜索（最后的回退策略）
        try:
            # 将所有关键词组合成一个查询字符串
            combined_query = ' '.join(keywords)
            fuzzy_results = await self.connection.fetch("""
                SELECT 
                    id,
                    CASE 
                        WHEN title ILIKE $1 THEN 3.0
                        WHEN content ILIKE $1 THEN 1.0
                        ELSE 0.5
                    END as score
                FROM documents
                WHERE title ILIKE $1 OR content ILIKE $1
                ORDER BY score DESC
                LIMIT $2
            """, f'%{combined_query}%', top_k)
            
            if fuzzy_results:
                results = []
                for row in fuzzy_results:
                    base_score = float(row['score'])
                    # 检查文档是否包含重合关键词，如果包含则提升权重
                    enhanced_score = await self._calculate_enhanced_score(row['id'], base_score, overlap_keywords, overlap_boost)
                    results.append((row['id'], enhanced_score))
                
                # 重新排序结果
                results.sort(key=lambda x: x[1], reverse=True)
                self.logger.info(f"模糊匹配搜索成功: 返回 {len(results)} 个结果")
                return results
                
        except Exception as e:
            self.logger.warning(f"模糊匹配搜索失败: {e}")
        
        self.logger.warning(f"所有搜索策略都失败")
        return []
    
    async def _calculate_enhanced_score(self, doc_id: str, base_score: float, overlap_keywords: List[str], overlap_boost: float) -> float:
        """
        计算增强后的分数，为包含重合关键词的文档提高权重
        
        Args:
            doc_id: 文档ID
            base_score: 基础分数
            overlap_keywords: 重合关键词列表
            overlap_boost: 权重提升系数
            
        Returns:
            增强后的分数
        """
        if not overlap_keywords:
            return base_score
        
        try:
            # 获取文档内容
            doc_result = await self.connection.fetchrow("""
                SELECT title, content FROM documents WHERE id = $1
            """, doc_id)
            
            if not doc_result:
                return base_score
            
            # 检查文档标题和内容中是否包含重合关键词
            title = doc_result['title'] or ""
            content = doc_result['content'] or ""
            full_text = (title + " " + content).lower()
            
            # 计算重合关键词在文档中的匹配数量
            matched_overlap_count = 0
            for keyword in overlap_keywords:
                if keyword.lower() in full_text:
                    matched_overlap_count += 1
            
            # 如果文档包含重合关键词，则提升权重
            if matched_overlap_count > 0:
                # 权重提升程度与匹配的重合关键词数量成正比
                boost_factor = overlap_boost + (matched_overlap_count - 1) * 0.2  # 每多匹配一个关键词额外提升0.2
                enhanced_score = base_score * boost_factor
                self.logger.debug(f"文档 {doc_id} 匹配 {matched_overlap_count} 个重合关键词，分数从 {base_score:.4f} 提升到 {enhanced_score:.4f}")
                return enhanced_score
            
            return base_score
            
        except Exception as e:
            self.logger.warning(f"计算增强分数失败 (doc_id: {doc_id}): {e}")
            return base_score
    
    async def get_document_by_id(self, doc_id: str) -> Optional[Document]:
        """根据ID获取文档"""
        if not self.connection:
            return None
        
        try:
            # 查询文档信息
            result = await self.connection.fetchrow("""
                SELECT id, title, summary, content, category, keywords, embedding, created_at, updated_at
                FROM documents
                WHERE id = $1
            """, doc_id)
            
            if result:
                # 处理keywords字段（PostgreSQL数组）
                keywords = result['keywords'] if result['keywords'] else []
                
                return Document(
                    id=str(result['id']),
                    title=result['title'] or "",
                    summary=result['summary'] or "",
                    content=result['content'] or "",
                    category=result['category'] or "",
                    keywords=keywords,
                    embedding=result['embedding'] or "",
                    created_at=str(result['created_at']) if result['created_at'] else "",
                    updated_at=str(result['updated_at']) if result['updated_at'] else ""
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"获取文档失败 (ID: {doc_id}): {e}")
            return None

# 便捷的入口函数
async def sparse_retrieval_search(question: str, keywords: List[str] = None, top_k: int = 5) -> List[SearchResult]:
    """
    稀疏检索的主入口函数
    
    Args:
        question: 输入的问题文本
        keywords: 额外的关键词列表（可选）
        top_k: 返回的文档数量
        
    Returns:
        List[SearchResult]: 搜索结果列表
    """
    # 初始化配置和搜索器
    config = PostgreSQLConfig()
    searcher = PostgreSQLSearcher(config)
    
    try:
        # 连接数据库
        if not await searcher.connect():
            logging.error("无法连接到PostgreSQL数据库")
            return []
        
        # 执行搜索
        search_results = await searcher.search_by_question_and_keywords(question, keywords, top_k)
        
        # 获取完整的文档信息
        results = []
        for i, (doc_id, score) in enumerate(search_results):
            document = await searcher.get_document_by_id(doc_id)
            if document:
                result = SearchResult(
                    doc_id=doc_id,
                    title=document.title,
                    content=document.content,
                    category=document.category,
                    score=score,
                    rank=i + 1,
                    summary=document.summary,
                    keywords=document.keywords,
                    embedding=document.embedding,
                    metadata=document.metadata
                )
                results.append(result)
        
        return results
        
    except Exception as e:
        logging.error(f"稀疏检索过程中发生错误: {e}")
        return []
    finally:
        # 断开数据库连接
        await searcher.disconnect()

# 向后兼容的函数
async def search_by_keywords(keywords: str, top_k: int = 5) -> List[Tuple[str, float]]:
    """
    向后兼容的关键词搜索函数
    
    Args:
        keywords: 关键词字符串
        top_k: 返回的文档数量
        
    Returns:
        List[Tuple[str, float]]: 文档ID和得分的元组列表
    """
    config = PostgreSQLConfig()
    searcher = PostgreSQLSearcher(config)
    
    try:
        if not await searcher.connect():
            return []
        
        # 将关键词字符串作为问题处理
        return await searcher.search_by_question_and_keywords(keywords, [], top_k)
        
    except Exception as e:
        logging.error(f"关键词搜索失败: {e}")
        return []
    finally:
        await searcher.disconnect()

