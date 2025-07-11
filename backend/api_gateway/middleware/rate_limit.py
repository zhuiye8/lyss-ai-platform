"""
速率限制中间件

实现基于IP和用户的请求速率限制
"""

import time
from typing import Dict, Optional
from collections import defaultdict, deque
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from fastapi import status

from ..core.logging import get_logger
from ..utils.helpers import build_error_response, get_client_ip
from ..utils.constants import RATE_LIMIT_CONFIG
from ..config import settings


logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """速率限制中间件"""
    
    def __init__(self, app):
        """
        初始化速率限制中间件
        
        Args:
            app: FastAPI应用实例
        """
        super().__init__(app)
        
        # 存储每个IP的请求记录
        self.ip_requests: Dict[str, deque] = defaultdict(deque)
        
        # 存储每个用户的请求记录
        self.user_requests: Dict[str, deque] = defaultdict(deque)
        
        # 配置
        self.requests_per_minute = settings.rate_limit_requests
        self.window_seconds = settings.rate_limit_window
        
        # 清理间隔
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5分钟清理一次
    
    async def dispatch(self, request: Request, call_next):
        """
        处理速率限制逻辑
        
        Args:
            request: 请求对象
            call_next: 下一个中间件或路由处理器
            
        Returns:
            响应对象
        """
        request_id = getattr(request.state, "request_id", "")
        
        # 定期清理过期记录
        await self._cleanup_expired_records()
        
        # 检查IP级别限制
        client_ip = get_client_ip(dict(request.headers))
        if await self._is_rate_limited_by_ip(client_ip):
            return await self._create_rate_limit_response(
                "IP请求频率超限",
                request_id,
                {"client_ip": client_ip}
            )
        
        # 检查用户级别限制
        user_id = getattr(request.state, "user_id", None)
        if user_id and await self._is_rate_limited_by_user(user_id):
            return await self._create_rate_limit_response(
                "用户请求频率超限",
                request_id,
                {"user_id": user_id}
            )
        
        # 记录请求
        await self._record_request(client_ip, user_id)
        
        # 继续处理请求
        response = await call_next(request)
        
        # 添加速率限制头部
        await self._add_rate_limit_headers(response, client_ip, user_id)
        
        return response
    
    async def _is_rate_limited_by_ip(self, client_ip: str) -> bool:
        """
        检查IP是否被限制
        
        Args:
            client_ip: 客户端IP
            
        Returns:
            是否被限制
        """
        current_time = time.time()
        ip_requests = self.ip_requests[client_ip]
        
        # 清理过期请求
        while ip_requests and current_time - ip_requests[0] > self.window_seconds:
            ip_requests.popleft()
        
        # 检查是否超过限制
        return len(ip_requests) >= self.requests_per_minute
    
    async def _is_rate_limited_by_user(self, user_id: str) -> bool:
        """
        检查用户是否被限制
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否被限制
        """
        current_time = time.time()
        user_requests = self.user_requests[user_id]
        
        # 清理过期请求
        while user_requests and current_time - user_requests[0] > self.window_seconds:
            user_requests.popleft()
        
        # 检查是否超过限制
        return len(user_requests) >= self.requests_per_minute
    
    async def _record_request(self, client_ip: str, user_id: Optional[str] = None):
        """
        记录请求
        
        Args:
            client_ip: 客户端IP
            user_id: 用户ID
        """
        current_time = time.time()
        
        # 记录IP请求
        self.ip_requests[client_ip].append(current_time)
        
        # 记录用户请求
        if user_id:
            self.user_requests[user_id].append(current_time)
    
    async def _add_rate_limit_headers(
        self,
        response: Response,
        client_ip: str,
        user_id: Optional[str] = None
    ):
        """
        添加速率限制头部
        
        Args:
            response: 响应对象
            client_ip: 客户端IP
            user_id: 用户ID
        """
        # 计算剩余请求数
        ip_remaining = max(0, self.requests_per_minute - len(self.ip_requests[client_ip]))
        
        # 添加头部
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(ip_remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + self.window_seconds)
        
        # 如果有用户信息，添加用户级别的限制头部
        if user_id:
            user_remaining = max(0, self.requests_per_minute - len(self.user_requests[user_id]))
            response.headers["X-RateLimit-User-Remaining"] = str(user_remaining)
    
    async def _cleanup_expired_records(self):
        """清理过期记录"""
        current_time = time.time()
        
        # 如果距离上次清理时间超过清理间隔，执行清理
        if current_time - self.last_cleanup > self.cleanup_interval:
            self.last_cleanup = current_time
            
            # 清理IP记录
            for ip in list(self.ip_requests.keys()):
                requests = self.ip_requests[ip]
                while requests and current_time - requests[0] > self.window_seconds:
                    requests.popleft()
                
                # 如果没有请求记录了，删除这个IP
                if not requests:
                    del self.ip_requests[ip]
            
            # 清理用户记录
            for user_id in list(self.user_requests.keys()):
                requests = self.user_requests[user_id]
                while requests and current_time - requests[0] > self.window_seconds:
                    requests.popleft()
                
                # 如果没有请求记录了，删除这个用户
                if not requests:
                    del self.user_requests[user_id]
    
    async def _create_rate_limit_response(
        self,
        message: str,
        request_id: str,
        details: Optional[Dict] = None
    ) -> JSONResponse:
        """
        创建速率限制错误响应
        
        Args:
            message: 错误消息
            request_id: 请求ID
            details: 错误详情
            
        Returns:
            JSON错误响应
        """
        error_response = build_error_response(
            error_code="1005",
            message=message,
            details=details,
            request_id=request_id
        )
        
        return JSONResponse(
            content=error_response,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={
                "X-RateLimit-Limit": str(self.requests_per_minute),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time()) + self.window_seconds),
                "Retry-After": str(self.window_seconds)
            }
        )


class AdaptiveRateLimitMiddleware(BaseHTTPMiddleware):
    """自适应速率限制中间件"""
    
    def __init__(self, app):
        """
        初始化自适应速率限制中间件
        
        Args:
            app: FastAPI应用实例
        """
        super().__init__(app)
        
        # 不同路径的限制配置
        self.path_limits = {
            "/api/v1/auth/login": 10,  # 登录接口限制更严格
            "/api/v1/auth/register": 5,  # 注册接口限制更严格
            "/health": 1000,  # 健康检查接口限制宽松
            "default": settings.rate_limit_requests
        }
        
        # 不同角色的限制配置
        self.role_limits = {
            "end_user": settings.rate_limit_requests,
            "tenant_admin": settings.rate_limit_requests * 2,
            "super_admin": settings.rate_limit_requests * 5
        }
    
    async def dispatch(self, request: Request, call_next):
        """
        处理自适应速率限制逻辑
        
        Args:
            request: 请求对象
            call_next: 下一个中间件或路由处理器
            
        Returns:
            响应对象
        """
        # 获取路径特定的限制
        path = request.url.path
        path_limit = self._get_path_limit(path)
        
        # 获取角色特定的限制
        user_role = getattr(request.state, "user_role", "end_user")
        role_limit = self.role_limits.get(user_role, self.role_limits["end_user"])
        
        # 使用更宽松的限制
        effective_limit = max(path_limit, role_limit)
        
        # 临时设置限制
        original_limit = settings.rate_limit_requests
        settings.rate_limit_requests = effective_limit
        
        try:
            # 继续处理请求
            response = await call_next(request)
            return response
        finally:
            # 恢复原始限制
            settings.rate_limit_requests = original_limit
    
    def _get_path_limit(self, path: str) -> int:
        """
        获取路径特定的限制
        
        Args:
            path: 请求路径
            
        Returns:
            限制数量
        """
        for pattern, limit in self.path_limits.items():
            if pattern != "default" and path.startswith(pattern):
                return limit
        
        return self.path_limits["default"]