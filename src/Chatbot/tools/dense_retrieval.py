"""
密集检索模块
实现基于向量相似度的密集检索功能，包括Query编码、向量搜索和结果回表
"""

import asyncio
import os
import numpy as np
from typing import List, Dict, Any, Optional, Union, Tuple
import hashlib
import json
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path

# 设置模型缓存目录环境变量
import os.path as osp
PROJECT_ROOT = osp.abspath(osp.join(osp.dirname(__file__), "../../../"))
MODELS_CACHE_DIR = osp.join(PROJECT_ROOT, "models_cache")
os.environ['HF_HOME'] = MODELS_CACHE_DIR
os.environ['TRANSFORMERS_CACHE'] = MODELS_CACHE_DIR
os.environ['SENTENCE_TRANSFORMERS_HOME'] = MODELS_CACHE_DIR

# 向量化和存储
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

from config.settings import settings
from src.Chatbot.utils.logger import setup_logger


@dataclass
class Document:
    """文档数据结构"""
    id: str
    title: str
    content: str
    category: str = "其他"
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class DenseSearchResult:
    """密集检索结果数据结构"""
    doc_id: str
    title: str
    content: str
    category: str
    score: float
    rank: int
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class DenseRetrievalEngine:
    """密集检索引擎 - 基于向量相似度的语义检索"""

    def __init__(self):
        self.settings = settings
        self.logger = setup_logger("dense_retrieval")
        
        # 设置集合名称
        self.collection_name = "xpu_knowledge_base"
        
        # 初始化状态
        self.initialized = False
        self.document_store = {}  # 本地文档存储，用于结果回表
        
        # 初始化向量模型
        self._initialize_embedding_model()
        
        # 初始化Qdrant客户端
        self._initialize_qdrant_client()

    def _initialize_embedding_model(self):
        """初始化嵌入模型，使用BGE-M3模型"""
        # 首先尝试使用本地快照路径加载BGE-M3模型
        local_model_path = os.path.join(MODELS_CACHE_DIR, 
                                       "models--BAAI--bge-m3", 
                                       "snapshots", 
                                       "5617a9f61b028005a4858fdac845db406aefb181")
        
        try:
            # 检查本地模型路径是否存在
            if os.path.exists(local_model_path):
                self.logger.info(f"正在从本地路径加载BGE-M3向量模型: {local_model_path}")
                self.model = SentenceTransformer(local_model_path)
                self.vector_dim = self.model.get_sentence_embedding_dimension()
                self.logger.info(f"成功从本地加载BGE-M3向量模型，向量维度: {self.vector_dim}")
                
                # 预热模型 - 执行一次编码以确保模型完全就绪
                self._warmup_model()
                
            else:
                # 如果本地路径不存在，尝试使用模型名称加载
                self.logger.info("本地模型路径不存在，尝试使用模型名称加载...")
                model_name = "BAAI/bge-m3"
                self.logger.info(f"正在加载BGE-M3向量模型: {model_name}")
                self.model = SentenceTransformer(model_name, cache_folder=MODELS_CACHE_DIR)
                self.vector_dim = self.model.get_sentence_embedding_dimension()
                self.logger.info(f"成功加载BGE-M3向量模型，向量维度: {self.vector_dim}")
                
                # 预热模型
                self._warmup_model()
                
        except Exception as e:
            self.logger.warning(f"加载BGE-M3向量模型失败: {e}，使用备用方案")


    def _warmup_model(self):
        """预热模型，确保模型完全就绪"""
        try:
            self.logger.info("正在预热BGE-M3模型...")
            # 使用简单的测试文本进行预热
            warmup_text = "测试文本用于模型预热"
            _ = self.model.encode(warmup_text)
            self.logger.info("BGE-M3模型预热完成，模型已就绪")
        except Exception as e:
            self.logger.warning(f"模型预热失败: {e}")
            # 预热失败不影响模型使用，只是性能可能稍差

    def _initialize_qdrant_client(self):
        """初始化Qdrant客户端"""
        try:
            qdrant_host = os.getenv("QDRANT_HOST", "localhost")
            qdrant_port = os.getenv("QDRANT_PORT", "6333")
            qdrant_url = f"http://{qdrant_host}:{qdrant_port}"
            
            self.qdrant_client = QdrantClient(url=qdrant_url, timeout=10.0)
            self.logger.info(f"成功连接到Qdrant服务器: {qdrant_url}")
        except Exception as e:
            self.logger.error(f"连接Qdrant服务器失败: {e}")
            self.qdrant_client = None

    def initialize(self):
        """初始化密集检索引擎（仅用于查询）"""
        try:
            # 如果已经初始化，则跳过
            if self.initialized:
                self.logger.info("密集检索引擎已初始化，跳过重复初始化")
                return
                
            if self.qdrant_client is None:
                raise Exception("Qdrant客户端未初始化")
            
            # 检查集合是否存在（仅检查，不创建）
            collections = self.qdrant_client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                self.logger.warning(f"集合 {self.collection_name} 不存在，请确保数据已正确上传")
            else:
                self.logger.info(f"集合 {self.collection_name} 已存在，可以进行查询")
            
            self.initialized = True
            self.logger.info("密集检索引擎初始化成功（查询模式）")
        except Exception as e:
            self.logger.error(f"密集检索引擎初始化失败: {e}")
            raise



    def encode_query(self, query: str) -> np.ndarray:
        """
        Query编码：将查询文本编码为向量
        
        Args:
            query: 查询文本
            
        Returns:
            查询向量
        """
        try:
            query_vector = self.model.encode(query, convert_to_numpy=True)
            if query_vector.ndim == 1:
                query_vector = query_vector.reshape(1, -1)
            return query_vector[0]  # 返回一维向量
        except Exception as e:
            self.logger.error(f"查询编码失败: {e}")
            raise



    def vector_search(self, query_vector: np.ndarray, top_k: int = 5, 
                     category_filter: Optional[str] = None) -> List[Tuple[str, float]]:
        """
        向量搜索：在向量索引中搜索相似文档
        
        Args:
            query_vector: 查询向量
            top_k: 返回结果数量
            category_filter: 类别过滤条件
            
        Returns:
            (doc_id, score) 元组列表
        """
        if not self.initialized:
            raise Exception("检索引擎未初始化，请先调用initialize()方法")
        
        try:
            # 构建过滤条件
            query_filter = None
            if category_filter:
                query_filter = Filter(
                    must=[
                        FieldCondition(
                            key="category",
                            match=MatchValue(value=category_filter)
                        )
                    ]
                )
            
            # 执行向量搜索
            search_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_vector.tolist(),
                query_filter=query_filter,
                limit=top_k,
                with_payload=True
            )
            
            # 提取结果
            results = []
            for result in search_results:
                doc_id = str(result.id)  # 使用点的ID作为doc_id
                score = result.score
                results.append((doc_id, score))
            
            self.logger.info(f"向量搜索完成，返回 {len(results)} 个结果")
            return results
        except Exception as e:
            self.logger.error(f"向量搜索失败: {e}")
            raise

    def retrieve_documents(self, doc_ids_scores: List[Tuple[str, float]]) -> List[DenseSearchResult]:
        """
        结果回表：根据文档ID获取完整文档信息
        
        Args:
            doc_ids_scores: (doc_id, score) 元组列表
            
        Returns:
            检索结果列表
        """
        try:
            results = []
            
            # 批量获取文档信息
            doc_ids = [doc_id for doc_id, _ in doc_ids_scores]
            
            try:
                # 从Qdrant获取文档信息
                points = self.qdrant_client.retrieve(
                    collection_name=self.collection_name,
                    ids=doc_ids,
                    with_payload=True
                )
                
                # 创建ID到点的映射
                id_to_point = {str(point.id): point for point in points}
                
                for rank, (doc_id, score) in enumerate(doc_ids_scores, 1):
                    if doc_id in id_to_point:
                        point = id_to_point[doc_id]
                        payload = point.payload
                        
                        result = DenseSearchResult(
                            doc_id=doc_id,
                            title=payload.get('title', ''),
                            content=payload.get('content', ''),
                            category=payload.get('category', '其他'),
                            score=score,
                            rank=rank,
                            metadata={
                                'original_name': payload.get('original_name', ''),
                                'original_filename': payload.get('original_filename', ''),
                                'chunk_index': payload.get('chunk_index', 0),
                                'keywords': payload.get('keywords', ''),
                                'summary': payload.get('summary', '')
                            }
                        )
                        results.append(result)
                    else:
                        self.logger.warning(f"文档 {doc_id} 在Qdrant中未找到")
                
            except Exception as e:
                self.logger.error(f"从Qdrant获取文档信息失败: {e}")
                # 如果批量获取失败，尝试逐个获取
                for rank, (doc_id, score) in enumerate(doc_ids_scores, 1):
                    try:
                        points = self.qdrant_client.retrieve(
                            collection_name=self.collection_name,
                            ids=[doc_id],
                            with_payload=True
                        )
                        
                        if points:
                            payload = points[0].payload
                            result = DenseSearchResult(
                                doc_id=doc_id,
                                title=payload.get('title', ''),
                                content=payload.get('content', ''),
                                category=payload.get('category', '其他'),
                                score=score,
                                rank=rank,
                                metadata={
                                    'original_name': payload.get('original_name', ''),
                                    'original_filename': payload.get('original_filename', ''),
                                    'chunk_index': payload.get('chunk_index', 0),
                                    'keywords': payload.get('keywords', ''),
                                    'summary': payload.get('summary', '')
                                }
                            )
                            results.append(result)
                    except Exception as single_error:
                        self.logger.warning(f"获取文档 {doc_id} 失败: {single_error}")
            
            self.logger.info(f"结果回表完成，返回 {len(results)} 个文档")
            return results
        except Exception as e:
            self.logger.error(f"结果回表失败: {e}")
            raise

    def search(self, query: str, top_k: int = 5, 
               category_filter: Optional[str] = None) -> List[DenseSearchResult]:
        """
        完整的密集检索流程
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            category_filter: 类别过滤条件
            
        Returns:
            检索结果列表
        """
        try:
            # 1. Query编码
            query_vector = self.encode_query(query)
            
            # 2. 向量搜索
            doc_ids_scores = self.vector_search(query_vector, top_k, category_filter)
            
            # 3. 结果回表
            results = self.retrieve_documents(doc_ids_scores)
            
            self.logger.info(f"密集检索完成，查询: '{query}'，返回 {len(results)} 个结果")
            return results
        except Exception as e:
            self.logger.error(f"密集检索失败: {e}")
            raise

    def get_collection_info(self) -> Dict[str, Any]:
        """获取集合信息"""
        if not self.initialized:
            return {"error": "检索引擎未初始化"}
        
        try:
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            return {
                "collection_name": self.collection_name,
                "vectors_count": collection_info.vectors_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count,
                "points_count": collection_info.points_count,
                "status": collection_info.status,
                "vector_dimension": self.vector_dim
            }
        except Exception as e:
            self.logger.error(f"获取集合信息失败: {e}")
            return {"error": str(e)}

    def check_data_persistence(self) -> Dict[str, Any]:
        """检查数据持久化状态"""
        try:
            if not self.qdrant_client:
                return {"status": "error", "message": "Qdrant客户端未初始化"}
            
            # 检查集合是否存在
            collections = self.qdrant_client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                return {
                    "status": "warning", 
                    "message": f"集合 {self.collection_name} 不存在",
                    "vectors_count": 0,
                    "needs_initialization": True
                }
            
            # 获取向量数量
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            
            # 尝试获取向量数量，处理不同的API响应格式
            vectors_count = 0
            if hasattr(collection_info, 'vectors_count'):
                vectors_count = collection_info.vectors_count or 0
            elif hasattr(collection_info, 'points_count'):
                vectors_count = collection_info.points_count or 0
            else:
                # 如果无法直接获取，尝试通过count API获取
                try:
                    count_result = self.qdrant_client.count(collection_name=self.collection_name)
                    vectors_count = count_result.count if hasattr(count_result, 'count') else 0
                except Exception as e:
                    self.logger.warning(f"无法获取向量数量: {e}")
                    vectors_count = 0
            
            if vectors_count == 0:
                return {
                    "status": "warning",
                    "message": f"集合 {self.collection_name} 存在但无数据",
                    "vectors_count": 0,
                    "needs_data_loading": True
                }
            
            return {
                "status": "ok",
                "message": f"集合 {self.collection_name} 数据正常",
                "vectors_count": vectors_count,
                "collection_status": getattr(collection_info, 'status', 'unknown')
            }
            
        except Exception as e:
            self.logger.error(f"检查数据持久化状态失败: {e}")
            return {"status": "error", "message": str(e)}

