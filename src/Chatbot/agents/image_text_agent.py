"""
图片文本处理智能体 - 负责处理上传的图片文本
使用PaddleOCR进行图片文字识别，并构建内存向量索引
"""

import os
import json
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime
from pathlib import Path
import base64
from io import BytesIO
from PIL import Image
import tempfile

# 设置模型缓存目录
import os.path as osp
PROJECT_ROOT = osp.abspath(osp.join(osp.dirname(__file__), "../../../"))
MODELS_CACHE_DIR = osp.join(PROJECT_ROOT, "models_cache")
os.environ['HF_HOME'] = MODELS_CACHE_DIR
os.environ['TRANSFORMERS_CACHE'] = MODELS_CACHE_DIR
os.environ['SENTENCE_TRANSFORMERS_HOME'] = MODELS_CACHE_DIR

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../"))

# 导入依赖
try:
    import paddleocr
    from paddleocr import PaddleOCR
except ImportError:
    print("PaddleOCR not installed. Please install with: pip install paddleocr")
    raise

try:
    import faiss
except ImportError:
    print("FAISS not installed. Please install with: pip install faiss-cpu")
    raise

try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
except ImportError:
    print("LangChain not installed. Please install with: pip install langchain")
    raise

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("SentenceTransformers not installed. Please install with: pip install sentence-transformers")
    raise

from src.Chatbot.utils.logger import setup_logger

logger = setup_logger("image_text_agent")


class ImageTextProcessor:
    """图片文本处理器 - 处理图片OCR和文本向量化"""
    
    def __init__(self, models_cache_dir: str = MODELS_CACHE_DIR):
        """
        初始化图片文本处理器
        
        Args:
            models_cache_dir: 模型缓存目录
        """
        self.models_cache_dir = models_cache_dir
        self.ocr_engine = None
        self.embedding_model = None
        self.text_splitter = None
        self.faiss_index = None
        self.document_store = []  # 存储文档内容和元数据
        self.index_to_doc_mapping = {}  # 索引到文档的映射
        
        # 初始化组件
        self._initialize_ocr()
        self._initialize_embedding_model()
        self._initialize_text_splitter()
        
        logger.info("图片文本处理器初始化完成")
    
    def _initialize_ocr(self):
        """初始化PaddleOCR"""
        try:
            # 设置PaddleOCR模型缓存目录
            ocr_model_dir = os.path.join(self.models_cache_dir, "paddleocr")
            os.makedirs(ocr_model_dir, exist_ok=True)
            
            # 设置环境变量，让PaddleOCR使用指定的缓存目录
            os.environ['PADDLEOCR_HOME'] = ocr_model_dir
            
            # 初始化PaddleOCR，使用本地模型缓存
            self.ocr_engine = PaddleOCR(
                use_textline_orientation=True,  # 使用新的参数名
                lang='ch'  # 支持中文
            )
            logger.info(f"PaddleOCR初始化成功，模型缓存目录: {ocr_model_dir}")
        except Exception as e:
            logger.error(f"PaddleOCR初始化失败: {e}")
            # 如果指定模型路径失败，尝试使用默认配置
            try:
                logger.info("尝试使用默认配置初始化PaddleOCR...")
                os.environ['PADDLEOCR_HOME'] = ocr_model_dir
                self.ocr_engine = PaddleOCR(lang='ch')
                logger.info("PaddleOCR使用默认配置初始化成功")
            except Exception as e2:
                logger.error(f"PaddleOCR默认配置初始化也失败: {e2}")
                raise
    
    def _initialize_embedding_model(self):
        """初始化BGE-M3嵌入模型"""
        try:
            model_path = os.path.join(self.models_cache_dir, "models--BAAI--bge-m3")
            if os.path.exists(model_path):
                # 检查模型是否完整
                config_path = os.path.join(model_path, "config.json")
                if os.path.exists(config_path):
                    # 使用本地模型
                    self.embedding_model = SentenceTransformer(model_path)
                    logger.info(f"使用本地BGE-M3模型: {model_path}")
                else:
                    # 本地模型不完整，重新下载
                    self.embedding_model = SentenceTransformer(
                        'BAAI/bge-m3',
                        cache_folder=self.models_cache_dir
                    )
                    logger.info("BGE-M3模型重新下载并初始化成功")
            else:
                # 下载模型到指定目录
                self.embedding_model = SentenceTransformer(
                    'BAAI/bge-m3',
                    cache_folder=self.models_cache_dir
                )
                logger.info("BGE-M3模型下载并初始化成功")
        except Exception as e:
            logger.warning(f"BGE-M3模型初始化失败: {e}，尝试使用备用模型")
            try:
                # 使用备用的中文嵌入模型
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("使用备用嵌入模型: all-MiniLM-L6-v2")
            except Exception as e2:
                logger.error(f"备用嵌入模型也初始化失败: {e2}")
                raise
    
    def _initialize_text_splitter(self):
        """初始化文本分割器"""
        try:
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,  # 每个块的大小
                chunk_overlap=50,  # 块之间的重叠
                length_function=len,
                separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
            )
            logger.info("文本分割器初始化成功")
        except Exception as e:
            logger.error(f"文本分割器初始化失败: {e}")
            raise
    
    def extract_text_from_image(self, image_data: Union[str, bytes, Image.Image]) -> str:
        """
        从图片中提取文字
        
        Args:
            image_data: 图片数据，可以是base64字符串、字节数据或PIL Image对象
            
        Returns:
            提取的文字内容
        """
        try:
            # 处理不同类型的输入
            if isinstance(image_data, str):
                # Base64字符串
                if image_data.startswith('data:image'):
                    # 移除data:image前缀
                    image_data = image_data.split(',')[1]
                image_bytes = base64.b64decode(image_data)
                image = Image.open(BytesIO(image_bytes))
            elif isinstance(image_data, bytes):
                # 字节数据
                image = Image.open(BytesIO(image_data))
            elif isinstance(image_data, Image.Image):
                # PIL Image对象
                image = image_data
            else:
                raise ValueError("不支持的图片数据类型")
            
            # 保存临时文件用于OCR处理
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                image.save(tmp_file.name, 'PNG')
                tmp_path = tmp_file.name
            
            try:
                # 使用PaddleOCR进行文字识别
                result = self.ocr_engine.ocr(tmp_path)
                logger.info(f"OCR原始结果类型: {type(result)}")
                
                # 提取文字内容
                extracted_text = []
                if result:
                    # 检查是否是新版本PaddleOCR的返回格式
                    if isinstance(result, list) and len(result) > 0:
                        first_result = result[0]
                        if isinstance(first_result, dict):
                            # 新版本格式：包含rec_texts和rec_scores
                            if 'rec_texts' in first_result and 'rec_scores' in first_result:
                                texts = first_result['rec_texts']
                                scores = first_result['rec_scores']
                                logger.info(f"识别到的文字: {texts}")
                                logger.info(f"置信度分数: {scores}")
                                
                                for text, score in zip(texts, scores):
                                    logger.info(f"文字: '{text}', 置信度: {score}")
                                    if score > 0.3:  # 置信度阈值
                                        extracted_text.append(text)
                            else:
                                logger.warning("未找到rec_texts字段")
                        else:
                            # 旧版本格式：嵌套列表
                            for line in first_result:
                                logger.info(f"处理OCR行: {line}")
                                if isinstance(line, list) and len(line) >= 2:
                                    text_info = line[1]
                                    if isinstance(text_info, list) and len(text_info) >= 2:
                                        text = text_info[0]
                                        confidence = text_info[1]
                                        logger.info(f"提取文字: '{text}', 置信度: {confidence}")
                                        if confidence > 0.3:
                                            extracted_text.append(text)
                                    elif isinstance(text_info, str):
                                        logger.info(f"直接提取文字: '{text_info}'")
                                        extracted_text.append(text_info)
                    else:
                        logger.warning("OCR结果格式不正确")
                else:
                    logger.warning("OCR结果为空")
                
                final_text = '\n'.join(extracted_text)
                logger.info(f"成功提取文字，长度: {len(final_text)}, 内容: '{final_text}'")
                return final_text
                
            finally:
                # 清理临时文件
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                    
        except Exception as e:
            logger.error(f"图片文字提取失败: {e}")
            raise
    
    def process_text_and_build_index(self, text: str, metadata: Optional[Dict] = None) -> Dict:
        """
        处理文本并构建向量索引
        
        Args:
            text: 要处理的文本
            metadata: 文档元数据
            
        Returns:
            处理结果信息
        """
        try:
            if not text.strip():
                return {"status": "error", "message": "文本内容为空"}
            
            # 使用RecursiveCharacterTextSplitter进行语义切分
            text_chunks = self.text_splitter.split_text(text)
            logger.info(f"文本切分完成，共{len(text_chunks)}个块")
            
            if not text_chunks:
                return {"status": "error", "message": "文本切分后为空"}
            
            # 使用BGE-M3进行向量化
            embeddings = self.embedding_model.encode(text_chunks, normalize_embeddings=True)
            logger.info(f"文本向量化完成，维度: {embeddings.shape}")
            
            # 构建或更新FAISS索引
            if self.faiss_index is None:
                # 创建新的FAISS索引
                dimension = embeddings.shape[1]
                self.faiss_index = faiss.IndexFlatIP(dimension)  # 使用内积相似度
                logger.info(f"创建新的FAISS索引，维度: {dimension}")
            
            # 添加向量到索引
            start_idx = len(self.document_store)
            self.faiss_index.add(embeddings.astype(np.float32))
            
            # 存储文档信息
            for i, chunk in enumerate(text_chunks):
                doc_info = {
                    "content": chunk,
                    "metadata": metadata or {},
                    "timestamp": datetime.now().isoformat(),
                    "chunk_index": i,
                    "total_chunks": len(text_chunks)
                }
                self.document_store.append(doc_info)
                self.index_to_doc_mapping[start_idx + i] = len(self.document_store) - 1
            
            result = {
                "status": "success",
                "message": f"成功处理文本并构建索引",
                "chunks_count": len(text_chunks),
                "total_documents": len(self.document_store),
                "index_size": self.faiss_index.ntotal if self.faiss_index else 0
            }
            
            logger.info(f"文本处理完成: {result}")
            return result
            
        except Exception as e:
            logger.error(f"文本处理失败: {e}")
            return {"status": "error", "message": f"文本处理失败: {str(e)}"}
    
    def search_similar_content(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        搜索相似内容
        
        Args:
            query: 查询文本
            top_k: 返回的相似内容数量
            
        Returns:
            相似内容列表
        """
        try:
            if self.faiss_index is None or len(self.document_store) == 0:
                return []
            
            # 对查询进行向量化
            query_embedding = self.embedding_model.encode([query], normalize_embeddings=True)
            
            # 在FAISS索引中搜索
            scores, indices = self.faiss_index.search(
                query_embedding.astype(np.float32), 
                min(top_k, self.faiss_index.ntotal)
            )
            
            # 构建结果
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx in self.index_to_doc_mapping:
                    doc_idx = self.index_to_doc_mapping[idx]
                    doc_info = self.document_store[doc_idx].copy()
                    doc_info["similarity_score"] = float(score)
                    results.append(doc_info)
            
            logger.info(f"搜索完成，返回{len(results)}个结果")
            return results
            
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return []
    
    def get_index_stats(self) -> Dict:
        """获取索引统计信息"""
        return {
            "total_documents": len(self.document_store),
            "index_size": self.faiss_index.ntotal if self.faiss_index else 0,
            "embedding_dimension": self.faiss_index.d if self.faiss_index else 0
        }
    
    def clear_index(self):
        """清空索引和文档存储"""
        self.faiss_index = None
        self.document_store = []
        self.index_to_doc_mapping = {}
        logger.info("索引和文档存储已清空")


class ImageTextAgent:
    """图片文本处理智能体"""
    
    def __init__(self, models_cache_dir: str = MODELS_CACHE_DIR):
        """
        初始化图片文本处理智能体
        
        Args:
            models_cache_dir: 模型缓存目录
        """
        self.processor = ImageTextProcessor(models_cache_dir)
        logger.info("图片文本处理智能体初始化完成")
    
    async def process_image_text(self, image_data: Union[str, bytes, Image.Image], 
                               metadata: Optional[Dict] = None) -> Dict:
        """
        处理图片文本的主要接口
        
        Args:
            image_data: 图片数据
            metadata: 元数据
            
        Returns:
            处理结果
        """
        try:
            # 提取图片中的文字
            extracted_text = self.processor.extract_text_from_image(image_data)
            
            if not extracted_text.strip():
                return {
                    "status": "error",
                    "message": "未能从图片中提取到文字内容"
                }
            
            # 处理文本并构建索引
            result = self.processor.process_text_and_build_index(extracted_text, metadata)
            
            # 添加提取的文字到结果中
            result["extracted_text"] = extracted_text
            result["text_length"] = len(extracted_text)
            
            return result
            
        except Exception as e:
            logger.error(f"图片文本处理失败: {e}")
            return {
                "status": "error",
                "message": f"图片文本处理失败: {str(e)}"
            }
    
    async def search_content(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        搜索相关内容
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            
        Returns:
            搜索结果
        """
        return self.processor.search_similar_content(query, top_k)
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self.processor.get_index_stats()
    
    def clear_all(self):
        """清空所有数据"""
        self.processor.clear_index()


# 全局实例
image_text_agent = None

def get_image_text_agent() -> ImageTextAgent:
    """获取图片文本处理智能体实例"""
    global image_text_agent
    if image_text_agent is None:
        image_text_agent = ImageTextAgent()
    return image_text_agent