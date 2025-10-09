"""
API数据模型定义
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any, Union, Generic, TypeVar
from datetime import datetime
from enum import Enum
import uuid
from .validators import EnhancedBaseModel

# 泛型类型变量
T = TypeVar('T')

# 统一响应包装器
class ApiResponse(BaseModel, Generic[T]):
    """统一API响应格式"""
    success: bool = Field(True, description="请求是否成功")
    data: Optional[T] = Field(None, description="响应数据")
    message: str = Field("操作成功", description="响应消息")
    code: int = Field(200, description="业务状态码")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间")
    request_id: Optional[str] = Field(None, description="请求追踪ID")
    
    @classmethod
    def success_response(cls, data: T = None, message: str = "操作成功", code: int = 200) -> 'ApiResponse[T]':
        """创建成功响应"""
        return cls(
            success=True,
            data=data,
            message=message,
            code=code
        )
    
    @classmethod
    def error_response(cls, message: str, code: int = 400, data: T = None) -> 'ApiResponse[T]':
        """创建错误响应"""
        return cls(
            success=False,
            data=data,
            message=message,
            code=code
        )

class ChatMessage(EnhancedBaseModel):
    """聊天消息模型"""
    role: str = Field(..., description="消息角色：user/assistant/system")
    content: str = Field(..., description="消息内容", min_length=1, max_length=2000)
    timestamp: Optional[datetime] = Field(None, description="消息时间戳")
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        if v not in ['user', 'assistant', 'system']:
            raise ValueError('角色必须是 user、assistant 或 system')
        return v

class ChatRequest(EnhancedBaseModel):
    """对话请求模型"""
    message: Optional[str] = Field(None, description="用户消息（单条消息模式）", min_length=1, max_length=2000)
    messages: Optional[List[ChatMessage]] = Field(None, description="多轮对话消息列表")
    session_id: Optional[str] = Field(None, description="会话ID，用于维持对话上下文")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    stream: bool = Field(False, description="是否使用流式响应")
    enable_web_search: bool = Field(default=True, description="是否启用网络搜索")
    web_search_threshold: Optional[float] = Field(None, description="网络搜索触发阈值")
    
    @field_validator('message')
    @classmethod
    def validate_message(cls, v):
        if v is not None and not v.strip():
            raise ValueError('消息内容不能为空')
        return v.strip() if v else v
    
    def model_validate(cls, values):
        """验证模型数据"""
        if isinstance(values, dict):
            message = values.get('message')
            messages = values.get('messages')
            
            # 确保至少提供一种消息格式
            if not message and not messages:
                raise ValueError('必须提供 message 或 messages 参数')
                
            # 如果同时提供了两种格式，优先使用 messages
            if message and messages:
                values['message'] = None
                
        return values

class ChatResponse(EnhancedBaseModel):
    """对话响应模型"""
    response: str = Field(..., description="AI回复消息")
    session_id: str = Field(..., description="会话ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")
    sources: Optional[List[Dict[str, Any]]] = Field(None, description="参考来源")
    context_used: Optional[bool] = Field(None, description="是否使用了上下文")
    usage: Optional[Dict[str, Any]] = Field(None, description="使用统计")
    confidence: Optional[float] = Field(None, description="回答置信度", ge=0.0, le=1.0)

class StreamChatResponse(EnhancedBaseModel):
    """流式对话响应模型"""
    content: str = Field(..., description="消息片段")
    session_id: str = Field(..., description="会话ID")
    finished: bool = Field(False, description="是否完成")

class DocumentUploadRequest(EnhancedBaseModel):
    """文档上传请求模型"""
    filename: Optional[str] = Field(None, description="文件名")
    category: str = Field("其他", description="文档类别")
    content: Optional[str] = Field(None, description="文本内容（当直接上传文本时）")
    title: Optional[str] = Field(None, description="文档标题")
    description: Optional[str] = Field(None, description="文档描述")

class DocumentInfo(EnhancedBaseModel):
    """文档信息模型"""
    document_id: str = Field(..., description="文档ID")
    filename: str = Field(..., description="文件名")
    file_size: int = Field(..., description="文件大小（字节）")
    upload_time: datetime = Field(default_factory=datetime.now, description="上传时间")
    file_type: str = Field(..., description="文件类型")
    status: str = Field("processing", description="处理状态")

class DocumentUploadResponse(EnhancedBaseModel):
    """文档上传响应模型"""
    document_info: DocumentInfo = Field(..., description="文档信息")
    chunks_count: Optional[int] = Field(None, description="分块数量")
    processing_time: Optional[float] = Field(None, description="处理耗时（秒）")

class DocumentSearchRequest(EnhancedBaseModel):
    """文档搜索请求模型"""
    query: str = Field(..., description="搜索查询", min_length=1)
    category: Optional[str] = Field(None, description="文档类别过滤")
    top_k: Optional[int] = Field(5, description="返回结果数量", ge=1, le=20)

class SearchResult(EnhancedBaseModel):
    """单个搜索结果模型"""
    content: str = Field(..., description="内容")
    source: str = Field(..., description="来源")
    score: float = Field(..., description="相关性分数", ge=0.0, le=1.0)
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")

class DocumentSearchResponse(EnhancedBaseModel):
    """文档搜索响应模型"""
    results: List[SearchResult] = Field(..., description="搜索结果")
    total: int = Field(..., description="总结果数")
    query: str = Field(..., description="搜索查询")
    search_time: Optional[float] = Field(None, description="搜索耗时（秒）")
    has_more: bool = Field(False, description="是否有更多结果")

class DocumentSummaryResponse(EnhancedBaseModel):
    """文档摘要响应模型"""
    summary: str = Field(..., description="文档库摘要")
    total_documents: int = Field(..., description="文档总数")
    total_chunks: int = Field(..., description="文本块总数")
    categories: Dict[str, int] = Field(..., description="各类别文档数量")
    last_updated: Optional[datetime] = Field(None, description="最后更新时间")
    key_points: Optional[List[str]] = Field(None, description="关键要点")
    confidence: Optional[float] = Field(None, description="摘要质量置信度", ge=0.0, le=1.0)

# 添加会话信息响应模型
class SessionInfoResponse(EnhancedBaseModel):
    """会话信息响应模型"""
    session_id: str = Field(..., description="会话ID")
    created_at: datetime = Field(..., description="创建时间")
    last_activity: datetime = Field(..., description="最后活动时间")
    message_count: int = Field(..., description="消息数量")
    is_active: bool = Field(..., description="是否活跃")

class HealthResponse(EnhancedBaseModel):
    """健康检查响应模型"""
    status: str = Field(..., description="服务状态")
    timestamp: datetime = Field(default_factory=datetime.now, description="检查时间")
    version: str = Field(..., description="API版本")
    components: Dict[str, str] = Field(..., description="各组件状态")

class ErrorResponse(EnhancedBaseModel):
    """错误响应模型"""
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误消息")
    detail: Optional[str] = Field(None, description="详细错误信息")
    timestamp: datetime = Field(default_factory=datetime.now, description="错误时间")

# 网络搜索相关模型
class WebSearchRequest(EnhancedBaseModel):
    """网络搜索请求模型"""
    query: str = Field(..., description="搜索查询")
    max_results: int = Field(default=5, ge=1, le=20, description="最大结果数量")
    engines: Optional[List[str]] = Field(None, description="指定搜索引擎")

class WebSearchResponse(EnhancedBaseModel):
    """网络搜索响应模型"""
    results: List[Dict[str, Any]] = Field(..., description="搜索结果")
    total: int = Field(..., description="结果总数")
    query: str = Field(..., description="搜索查询")
    engines_used: List[str] = Field(..., description="使用的搜索引擎")