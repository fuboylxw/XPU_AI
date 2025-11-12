"""
知识查询智能体 - 混合检索入口函数
调用密集检索和稀疏检索，融合重排序结果
"""

import asyncio
import os
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

# 设置模型缓存目录
import os.path as osp
PROJECT_ROOT = osp.abspath(osp.join(osp.dirname(__file__), "../../../"))
MODELS_CACHE_DIR = osp.join(PROJECT_ROOT, "models_cache")
os.environ['HF_HOME'] = MODELS_CACHE_DIR
os.environ['TRANSFORMERS_CACHE'] = MODELS_CACHE_DIR
os.environ['SENTENCE_TRANSFORMERS_HOME'] = MODELS_CACHE_DIR

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../"))

from config.settings import settings
from src.Chatbot.tools.dense_retrieval import DenseRetrievalEngine
from src.Chatbot.tools.sparse_retrieval import PostgreSQLConfig, PostgreSQLSearcher, sparse_retrieval_search
from src.Chatbot.utils.logger import setup_logger

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

logger = setup_logger("knowledge_query_agent")

# 全局引擎实例
_dense_engine = None
_engines_initialized = False


def _initialize_engines():
    """初始化检索引擎（单例模式）"""
    global _dense_engine, _engines_initialized
    
    if _engines_initialized:
        return True
    
    try:
        logger.info("初始化检索引擎...")
        
        # 初始化密集检索引擎
        _dense_engine = DenseRetrievalEngine()
        _dense_engine.initialize()
        logger.info("密集检索引擎初始化成功")
        
        _engines_initialized = True
        logger.info("所有检索引擎初始化完成")
        return True
        
    except Exception as e:
        logger.error(f"检索引擎初始化失败: {e}")
        return False


def _normalize_scores(scores: List[float]) -> List[float]:
    """归一化分数到0-1范围"""
    if not scores:
        return []
    
    min_score = min(scores)
    max_score = max(scores)
    
    if max_score == min_score:
        return [1.0] * len(scores)
    
    return [(score - min_score) / (max_score - min_score) for score in scores]


def _merge_and_rerank_results(dense_results: List[Any], sparse_results: List[Any], 
                             dense_weight: float = 0.7, sparse_weight: float = 0.3) -> List[Dict[str, Any]]:
    """
    融合并重排序密集检索和稀疏检索结果
    
    Args:
        dense_results: 密集检索结果
        sparse_results: 稀疏检索结果
        dense_weight: 密集检索权重
        sparse_weight: 稀疏检索权重
        
    Returns:
        融合重排序后的结果列表
    """
    try:
        # 创建结果字典，以文档ID为键
        merged_scores = {}
        
        # 提取密集检索分数并归一化
        dense_scores = []
        dense_doc_map = {}
        
        for result in dense_results:
            doc_id = result.doc_id if hasattr(result, 'doc_id') else result.get('doc_id')
            score = result.score if hasattr(result, 'score') else result.get('score', 0.0)
            dense_scores.append(score)
            dense_doc_map[doc_id] = result
        
        normalized_dense_scores = _normalize_scores(dense_scores)
        
        # 处理密集检索结果
        for i, result in enumerate(dense_results):
            doc_id = result.doc_id if hasattr(result, 'doc_id') else result.get('doc_id')
            normalized_score = normalized_dense_scores[i] if i < len(normalized_dense_scores) else 0.0
            
            merged_scores[doc_id] = {
                'doc_id': doc_id,
                'title': result.title if hasattr(result, 'title') else result.get('title', ''),
                'content': result.content if hasattr(result, 'content') else result.get('content', ''),
                'category': result.category if hasattr(result, 'category') else result.get('category', ''),
                'dense_score': normalized_score,
                'sparse_score': 0.0,
                'metadata': result.metadata if hasattr(result, 'metadata') else result.get('metadata', {}),
                'source': 'dense'
            }
        
        # 提取稀疏检索分数并归一化
        sparse_scores = []
        sparse_doc_map = {}
        
        for result in sparse_results:
            doc_id = result.doc_id if hasattr(result, 'doc_id') else result.get('doc_id')
            score = result.score if hasattr(result, 'score') else result.get('score', 0.0)
            sparse_scores.append(score)
            sparse_doc_map[doc_id] = result
        
        normalized_sparse_scores = _normalize_scores(sparse_scores)
        
        # 处理稀疏检索结果
        for i, result in enumerate(sparse_results):
            doc_id = result.doc_id if hasattr(result, 'doc_id') else result.get('doc_id')
            normalized_score = normalized_sparse_scores[i] if i < len(normalized_sparse_scores) else 0.0
            
            if doc_id in merged_scores:
                # 更新稀疏分数
                merged_scores[doc_id]['sparse_score'] = normalized_score
                merged_scores[doc_id]['source'] = 'both'
            else:
                # 新增稀疏检索结果
                merged_scores[doc_id] = {
                    'doc_id': doc_id,
                    'title': result.title if hasattr(result, 'title') else result.get('title', ''),
                    'content': result.content if hasattr(result, 'content') else result.get('content', ''),
                    'category': result.category if hasattr(result, 'category') else result.get('category', ''),
                    'dense_score': 0.0,
                    'sparse_score': normalized_score,
                    'metadata': result.metadata if hasattr(result, 'metadata') else result.get('metadata', {}),
                    'source': 'sparse'
                }
        
        # 计算融合分数并排序
        final_results = []
        for doc_id, data in merged_scores.items():
            # 计算加权融合分数
            final_score = (dense_weight * data['dense_score'] + 
                          sparse_weight * data['sparse_score'])
            
            # 置信度计算：如果两个引擎都找到了结果，置信度更高
            confidence = 0.5  # 基础置信度
            if data['source'] == 'both':
                confidence = 0.9  # 两个引擎都找到
            elif data['dense_score'] > 0.8 or data['sparse_score'] > 0.8:
                confidence = 0.8  # 单个引擎高分
            elif data['dense_score'] > 0.5 or data['sparse_score'] > 0.5:
                confidence = 0.7  # 单个引擎中等分
            
            final_results.append({
                'doc_id': doc_id,
                'title': data['title'],
                'content': data['content'],
                'category': data['category'],
                'score': final_score,
                'confidence': confidence,
                'dense_score': data['dense_score'],
                'sparse_score': data['sparse_score'],
                'source': data['source'],
                'metadata': data['metadata']
            })
        
        # 按置信度和分数排序
        final_results.sort(key=lambda x: (x['confidence'], x['score']), reverse=True)
        
        logger.info(f"结果融合完成，返回 {len(final_results)} 个结果")
        return final_results
        
    except Exception as e:
        logger.error(f"结果融合失败: {e}")
        return []


async def hybrid_retrieval(query_text: str, top_k: int = 10, keywords: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    混合检索入口函数
    
    Args:
        query_text: 查询文本
        top_k: 返回结果数量
        keywords: 查询文本关键词（可选，如果不提供则使用query_text）
        
    Returns:
        融合重排序后的检索结果列表，按置信度排序
    """
    try:
        # 初始化引擎
        if not _initialize_engines():
            logger.error("检索引擎初始化失败")
            return []
        
        logger.info(f"开始混合检索: '{query_text[:50]}...', top_k={top_k}")
        
        # 如果没有提供关键词，使用查询文本
        search_keywords = keywords if keywords else [query_text]
        
        logger.info("开始并行执行密集检索和稀疏检索...")
        
        # 并行执行密集检索和稀疏检索
        dense_task = asyncio.create_task(_call_dense_retrieval(query_text, top_k))
        sparse_task = asyncio.create_task(_call_sparse_retrieval(query_text, search_keywords, top_k))
        
        # 等待两个检索任务完成，使用return_exceptions=True来捕获异常
        results = await asyncio.gather(dense_task, sparse_task, return_exceptions=True)
        dense_results, sparse_results = results[0], results[1]
        
        # 处理异常结果
        if isinstance(dense_results, Exception):
            logger.error(f"密集检索失败: {dense_results}")
            dense_results = []
        
        if isinstance(sparse_results, Exception):
            logger.error(f"稀疏检索失败: {sparse_results}")
            sparse_results = []
        
        logger.info(f"密集检索返回 {len(dense_results)} 个结果")
        logger.info(f"稀疏检索返回 {len(sparse_results)} 个结果")
        
        # 融合重排序结果
        final_results = _merge_and_rerank_results(dense_results, sparse_results)
        
        # 截取前top_k个结果
        if len(final_results) > top_k:
            final_results = final_results[:top_k]
        
        logger.info(f"混合检索完成，返回 {len(final_results)} 个高置信度结果")
        return final_results
        
    except Exception as e:
        logger.error(f"混合检索失败: {e}")
        return []


async def _call_dense_retrieval(query_text: str, top_k: int) -> List[Any]:
    """调用密集检索函数（异步版本）"""
    try:
        if not _dense_engine:
            raise Exception("密集检索引擎未初始化")
        
        # 在异步环境中运行同步的密集检索
        import asyncio
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None, 
            lambda: _dense_engine.search(query_text, top_k=top_k * 2)
        )
        return results
        
    except Exception as e:
        logger.error(f"密集检索调用失败: {e}")
        return []


async def _call_sparse_retrieval(query_text: str, keywords: List[str], top_k: int) -> List[Any]:
    """调用稀疏检索函数"""
    try:
        
        # 直接调用sparse_retrieval_search函数
        results = await sparse_retrieval_search(query_text, keywords, top_k=top_k * 2)  # 获取更多结果用于融合
        return results
        
    except Exception as e:
        logger.error(f"稀疏检索调用失败: {e}")
        return []


async def close_engines():
    """关闭检索引擎"""
    global _dense_engine, _engines_initialized
    
    try:
        if _dense_engine:
            # 如果dense_engine有close方法，调用它
            if hasattr(_dense_engine, 'close'):
                await _dense_engine.close()
        
        _engines_initialized = False
        logger.info("检索引擎已关闭")
        
    except Exception as e:
        logger.error(f"关闭检索引擎失败: {e}")


# 便捷函数
async def search_knowledge(query: str, top_k: int = 10, keywords: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    知识检索便捷函数
    
    Args:
        query: 查询文本
        top_k: 返回结果数量
        keywords: 查询关键词（可选）
        
    Returns:
        检索结果列表
    """
    return await hybrid_retrieval(query, top_k, keywords)

