"""API中间件模块
提供统一的异常处理、请求验证、限流等功能
"""

import time
import traceback
import hashlib
import secrets
import re
import ipaddress
from typing import Dict, Any, Optional, Set
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from datetime import datetime, timedelta
import asyncio
from collections import defaultdict

from api.models import ErrorResponse
from src.utils.logger import setup_logger
from src.config.settings import Settings

class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """统一异常处理中间件"""
    
    def __init__(self, app: ASGIApp, settings: Settings):
        super().__init__(app)
        self.settings = settings
        self.logger = setup_logger(settings)
    
    async def dispatch(self, request: Request, call_next):
        """处理请求并捕获异常"""
        try:
            response = await call_next(request)
            return response
        except HTTPException as e:
            return await self._handle_http_exception(request, e)
        except ValueError as e:
            return await self._handle_validation_error(request, e)
        except ConnectionError as e:
            return await self._handle_connection_error(request, e)
        except TimeoutError as e:
            return await self._handle_timeout_error(request, e)
        except Exception as e:
            return await self._handle_unknown_error(request, e)
    
    async def _handle_http_exception(self, request: Request, exc: HTTPException) -> JSONResponse:
        """处理HTTP异常"""
        error_response = ErrorResponse(
            error="HTTP_ERROR",
            message=exc.detail,
            detail=f"Status: {exc.status_code}",
            timestamp=datetime.now()
        )
        
        self.logger.warning(f"HTTP异常 {exc.status_code}: {exc.detail} - {request.url}")
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.model_dump()
        )
    
    async def _handle_validation_error(self, request: Request, exc: ValueError) -> JSONResponse:
        """处理参数验证错误"""
        error_response = ErrorResponse(
            error="VALIDATION_ERROR",
            message="请求参数验证失败",
            detail=str(exc),
            timestamp=datetime.now()
        )
        
        self.logger.warning(f"参数验证错误: {exc} - {request.url}")
        
        return JSONResponse(
            status_code=422,
            content=error_response.model_dump()
        )
    
    async def _handle_connection_error(self, request: Request, exc: ConnectionError) -> JSONResponse:
        """处理连接错误"""
        error_response = ErrorResponse(
            error="CONNECTION_ERROR",
            message="服务连接失败，请稍后重试",
            detail=str(exc) if self.settings.debug else None,
            timestamp=datetime.now()
        )
        
        self.logger.error(f"连接错误: {exc} - {request.url}")
        
        return JSONResponse(
            status_code=503,
            content=error_response.model_dump()
        )
    
    async def _handle_timeout_error(self, request: Request, exc: TimeoutError) -> JSONResponse:
        """处理超时错误"""
        error_response = ErrorResponse(
            error="TIMEOUT_ERROR",
            message="请求超时，请稍后重试",
            detail=str(exc) if self.settings.debug else None,
            timestamp=datetime.now()
        )
        
        self.logger.error(f"请求超时: {exc} - {request.url}")
        
        return JSONResponse(
            status_code=504,
            content=error_response.model_dump()
        )
    
    async def _handle_unknown_error(self, request: Request, exc: Exception) -> JSONResponse:
        """处理未知异常"""
        error_response = ErrorResponse(
            error="INTERNAL_ERROR",
            message="服务器内部错误",
            detail=str(exc) if self.settings.debug else None,
            timestamp=datetime.now()
        )
        
        self.logger.error(f"未知异常: {exc} - {request.url}\n{traceback.format_exc()}")
        
        return JSONResponse(
            status_code=500,
            content=error_response.model_dump()
        )

class RateLimitMiddleware(BaseHTTPMiddleware):
    """API限流中间件"""
    
    def __init__(self, app: ASGIApp, settings: Settings, requests_per_minute: int = 60):
        super().__init__(app)
        self.settings = settings
        self.requests_per_minute = requests_per_minute
        self.logger = setup_logger(settings)
        self.requests = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        """限流检查"""
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # 清理过期记录
        self.requests[client_ip] = [
            t for t in self.requests[client_ip] 
            if current_time - t < 60
        ]
        
        # 检查限流
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            error_response = ErrorResponse(
                error="RATE_LIMIT_EXCEEDED",
                message=f"请求过于频繁，每分钟最多{self.requests_per_minute}次",
                detail=None,
                timestamp=datetime.now()
            )
            
            return JSONResponse(
                status_code=429,
                content=error_response.model_dump(),
                headers={"Retry-After": "60"}
            )
        
        # 记录请求
        self.requests[client_ip].append(current_time)
        
        response = await call_next(request)
        
        # 添加限流头信息
        remaining = max(0, self.requests_per_minute - len(self.requests[client_ip]))
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(current_time + 60))
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"

class SecurityMiddleware(BaseHTTPMiddleware):
    """安全中间件"""
    
    def __init__(self, app: ASGIApp, settings: Settings):
        super().__init__(app)
        self.settings = settings
        self.logger = setup_logger(settings)
    
    async def dispatch(self, request: Request, call_next):
        """安全检查"""
        response = await call_next(request)
        
        # 添加安全头
        self._add_security_headers(response)
        
        return response
    
    def _add_security_headers(self, response: Response):
        """添加安全响应头"""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # HTTPS相关
        if not self.settings.debug:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # 内容安全策略
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self';"
        )
        response.headers["Content-Security-Policy"] = csp_policy

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    
    def __init__(self, app: ASGIApp, settings: Settings):
        super().__init__(app)
        self.settings = settings
        self.logger = setup_logger(settings)
    
    async def dispatch(self, request: Request, call_next):
        """记录请求日志"""
        start_time = time.time()
        
        self.logger.info(f"请求开始: {request.method} {request.url}")
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        self.logger.info(
            f"请求完成: {request.method} {request.url} - "
            f"状态码: {response.status_code} - 耗时: {process_time:.3f}s"
        )
        
        response.headers["X-Process-Time"] = str(process_time)
        
        return response