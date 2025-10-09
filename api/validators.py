"""请求验证装饰器和参数校验增强模块"""

import re
import functools
from typing import Any, Callable, Dict, List, Optional, Union
from datetime import datetime
from fastapi import HTTPException, Request
from pydantic import BaseModel, validator
import asyncio
import time
from collections import defaultdict


class ValidationError(Exception):
    """自定义验证异常"""
    def __init__(self, message: str, field: str = None, code: str = None):
        self.message = message
        self.field = field
        self.code = code
        super().__init__(message)


class RequestValidator:
    """请求验证器基类"""
    
    @staticmethod
    def validate_session_id(session_id: str) -> bool:
        """验证会话ID格式"""
        if not session_id or len(session_id) < 8:
            raise ValidationError("会话ID长度不能少于8位", "session_id", "INVALID_SESSION_ID")
        
        # 检查是否包含非法字符
        if not re.match(r'^[a-zA-Z0-9_-]+$', session_id):
            raise ValidationError("会话ID只能包含字母、数字、下划线和连字符", "session_id", "INVALID_SESSION_ID")
        
        return True
    
    @staticmethod
    def validate_message_content(content: str) -> bool:
        """验证消息内容"""
        if not content or not content.strip():
            raise ValidationError("消息内容不能为空", "content", "EMPTY_CONTENT")
        
        if len(content) > 10000:
            raise ValidationError("消息内容长度不能超过10000字符", "content", "CONTENT_TOO_LONG")
        
        # 检查是否包含恶意内容（简单示例）
        malicious_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
        ]
        
        for pattern in malicious_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                raise ValidationError("消息内容包含不安全的脚本", "content", "MALICIOUS_CONTENT")
        
        return True
    
    @staticmethod
    def validate_file_upload(filename: str, content_type: str, file_size: int) -> bool:
        """验证文件上传"""
        # 验证文件名
        if not filename or not filename.strip():
            raise ValidationError("文件名不能为空", "filename", "EMPTY_FILENAME")
        
        # 验证文件扩展名
        allowed_extensions = ['.pdf', '.docx', '.csv', '.txt']
        file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
        if f'.{file_ext}' not in allowed_extensions:
            raise ValidationError(
                f"不支持的文件类型: {file_ext}，支持的类型: {', '.join(allowed_extensions)}",
                "filename",
                "UNSUPPORTED_FILE_TYPE"
            )
        
        # 验证文件大小（10MB限制）
        max_size = 10 * 1024 * 1024  # 10MB
        if file_size > max_size:
            raise ValidationError(
                f"文件大小超过限制，最大允许{max_size // (1024*1024)}MB",
                "file_size",
                "FILE_TOO_LARGE"
            )
        
        # 验证MIME类型
        allowed_mime_types = {
            'application/pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/csv',
            'text/plain'
        }
        
        if content_type not in allowed_mime_types:
            raise ValidationError(
                f"不支持的MIME类型: {content_type}",
                "content_type",
                "UNSUPPORTED_MIME_TYPE"
            )
        
        return True
    
    @staticmethod
    def validate_search_query(query: str, max_length: int = 500) -> bool:
        """验证搜索查询"""
        if not query or not query.strip():
            raise ValidationError("搜索查询不能为空", "query", "EMPTY_QUERY")
        
        if len(query) > max_length:
            raise ValidationError(
                f"搜索查询长度不能超过{max_length}字符",
                "query",
                "QUERY_TOO_LONG"
            )
        
        return True


class RateLimiter:
    """请求频率限制器"""
    
    def __init__(self):
        self.requests = defaultdict(list)
        self.lock = asyncio.Lock()
    
    async def is_allowed(self, identifier: str, max_requests: int, time_window: int) -> bool:
        """检查是否允许请求"""
        async with self.lock:
            now = time.time()
            
            # 清理过期的请求记录
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier]
                if now - req_time < time_window
            ]
            
            # 检查是否超过限制
            if len(self.requests[identifier]) >= max_requests:
                return False
            
            # 记录当前请求
            self.requests[identifier].append(now)
            return True


# 全局频率限制器实例
rate_limiter = RateLimiter()


def validate_request(
    session_id: bool = False,
    message_content: bool = False,
    file_upload: bool = False,
    search_query: bool = False,
    rate_limit: Optional[Dict[str, int]] = None
):
    """请求验证装饰器
    
    Args:
        session_id: 是否验证会话ID
        message_content: 是否验证消息内容
        file_upload: 是否验证文件上传
        search_query: 是否验证搜索查询
        rate_limit: 频率限制配置 {"max_requests": 10, "time_window": 60}
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取请求对象
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            # 频率限制检查
            if rate_limit and request:
                client_ip = request.client.host
                max_requests = rate_limit.get("max_requests", 10)
                time_window = rate_limit.get("time_window", 60)
                
                if not await rate_limiter.is_allowed(client_ip, max_requests, time_window):
                    raise HTTPException(
                        status_code=429,
                        detail=f"请求过于频繁，每{time_window}秒最多{max_requests}次请求"
                    )
            
            # 参数验证
            try:
                # 从kwargs中获取需要验证的参数
                if session_id and 'session_id' in kwargs:
                    RequestValidator.validate_session_id(kwargs['session_id'])
                
                if message_content:
                    # 尝试从request对象中获取消息内容
                    if 'request' in kwargs and hasattr(kwargs['request'], 'message'):
                        RequestValidator.validate_message_content(kwargs['request'].message)
                
                if file_upload and 'file' in kwargs:
                    file = kwargs['file']
                    if hasattr(file, 'filename') and hasattr(file, 'content_type'):
                        # 获取文件大小
                        file_size = getattr(file, 'size', 0)
                        if file_size == 0 and hasattr(file, 'file'):
                            # 尝试获取文件大小
                            current_pos = file.file.tell()
                            file.file.seek(0, 2)  # 移动到文件末尾
                            file_size = file.file.tell()
                            file.file.seek(current_pos)  # 恢复原位置
                        
                        RequestValidator.validate_file_upload(
                            file.filename,
                            file.content_type,
                            file_size
                        )
                
                if search_query:
                    if 'request' in kwargs and hasattr(kwargs['request'], 'query'):
                        RequestValidator.validate_search_query(kwargs['request'].query)
                    elif 'query' in kwargs:
                        RequestValidator.validate_search_query(kwargs['query'])
                
            except ValidationError as e:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": e.message,
                        "field": e.field,
                        "code": e.code
                    }
                )
            
            # 调用原函数
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def validate_json_schema(schema: Dict[str, Any]):
    """JSON Schema验证装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 这里可以添加JSON Schema验证逻辑
            # 暂时跳过具体实现
            return await func(*args, **kwargs)
        return wrapper
    return decorator


class EnhancedBaseModel(BaseModel):
    """增强的Pydantic基础模型"""
    
    class Config:
        # 启用字段验证
        validate_assignment = True
        # 允许额外字段但忽略它们
        extra = "ignore"
        # 使用枚举值而不是名称
        use_enum_values = True
    
    @validator('*', pre=True)
    def strip_strings(cls, v):
        """自动去除字符串首尾空格"""
        if isinstance(v, str):
            return v.strip()
        return v
    
    def dict_exclude_none(self, **kwargs):
        """排除None值的字典表示"""
        return self.dict(exclude_none=True, **kwargs)


# 常用验证装饰器的预定义配置
validate_chat = validate_request(
    session_id=True,
    message_content=True,
    rate_limit={"max_requests": 30, "time_window": 60}
)

validate_upload = validate_request(
    file_upload=True,
    rate_limit={"max_requests": 5, "time_window": 60}
)

validate_search = validate_request(
    search_query=True,
    rate_limit={"max_requests": 20, "time_window": 60}
)

validate_session = validate_request(
    session_id=True,
    rate_limit={"max_requests": 50, "time_window": 60}
)