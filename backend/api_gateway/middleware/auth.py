"""
认证中间件
JWT令牌验证、租户上下文、权限检查等
"""
import time
import uuid
import os
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.types import ASGIApp
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import logging

from common.database import AsyncSessionLocal
from common.security import get_security_manager, SecurityManager
from common.models import User, Tenant, UserStatus, TenantStatus
from common.redis_client import redis_manager
from common.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
security_manager = get_security_manager()


class TenantContext:
    """租户上下文管理器"""
    
    def __init__(self):
        self._current_tenant_id: Optional[str] = None
        self._current_user_id: Optional[str] = None
        self._current_user_roles: List[str] = []
    
    def set_tenant_id(self, tenant_id: str):
        """设置当前租户ID"""
        self._current_tenant_id = tenant_id
    
    def get_tenant_id(self) -> Optional[str]:
        """获取当前租户ID"""
        return self._current_tenant_id
    
    def set_user_id(self, user_id: str):
        """设置当前用户ID"""
        self._current_user_id = user_id
    
    def get_user_id(self) -> Optional[str]:
        """获取当前用户ID"""
        return self._current_user_id
    
    def set_user_roles(self, roles: List[str]):
        """设置当前用户角色"""
        self._current_user_roles = roles
    
    def get_user_roles(self) -> List[str]:
        """获取当前用户角色"""
        return self._current_user_roles
    
    def clear(self):
        """清除上下文"""
        self._current_tenant_id = None
        self._current_user_id = None
        self._current_user_roles = []


# 全局租户上下文
tenant_context = TenantContext()


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """认证中间件"""
    
    def __init__(self, app: ASGIApp, exclude_paths: Optional[List[str]] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/api/v1/health",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
            "/static"
        ]
    
    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        # 记录请求开始时间
        start_time = time.time()
        
        # 生成请求ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # 清除上下文
        tenant_context.clear()
        
        # 检查是否需要认证
        if self._should_skip_auth(request):
            response = await call_next(request)
            return self._add_response_headers(response, request_id, start_time)
        
        # 验证认证
        try:
            await self._authenticate_request(request)
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "success": False,
                    "message": e.detail,
                    "request_id": request_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "errors": []
                }
            )
        except Exception as e:
            logger.error(f"认证中间件错误: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False,
                    "message": "内部服务器错误",
                    "request_id": request_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "errors": []
                }
            )
        
        # 处理请求
        response = await call_next(request)
        
        # 添加响应头
        return self._add_response_headers(response, request_id, start_time)
    
    def _should_skip_auth(self, request: Request) -> bool:
        """检查是否应该跳过认证"""
        path = request.url.path
        
        # 检查排除路径
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True
        
        # OPTIONS请求跳过认证
        if request.method == "OPTIONS":
            return True
        
        return False
    
    async def _authenticate_request(self, request: Request):
        """认证请求"""
        # 获取Authorization头
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少认证令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 解析Bearer令牌
        try:
            scheme, token = auth_header.split(" ", 1)
            if scheme.lower() != "bearer":
                raise ValueError("认证方案不正确")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="认证令牌格式错误",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 验证令牌
        token_data = security_manager.verify_token(token)
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌无效或已过期",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 检查令牌是否被撤销
        redis_client = redis_manager.get_client()
        is_revoked = await redis_client.get(f"revoked_token:{token_data.jti}")
        if is_revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌已被撤销",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 验证用户和租户
        await self._validate_user_and_tenant(token_data)
        
        # 设置上下文
        tenant_context.set_tenant_id(token_data.tenant_id)
        tenant_context.set_user_id(token_data.user_id)
        tenant_context.set_user_roles(token_data.roles)
        
        # 将用户信息添加到请求状态
        request.state.user_id = token_data.user_id
        request.state.tenant_id = token_data.tenant_id
        request.state.user_email = token_data.email
        request.state.user_roles = token_data.roles
        request.state.user_permissions = token_data.permissions
    
    async def _validate_user_and_tenant(self, token_data):
        """验证用户和租户"""
        async with async_session_maker() as session:
            # 检查用户是否存在且活跃
            user_stmt = select(User).where(
                and_(
                    User.user_id == uuid.UUID(token_data.user_id),
                    User.tenant_id == uuid.UUID(token_data.tenant_id),
                    User.status == UserStatus.ACTIVE
                )
            )
            user_result = await session.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="用户不存在或已被禁用"
                )
            
            # 检查租户是否存在且活跃
            tenant_stmt = select(Tenant).where(
                and_(
                    Tenant.tenant_id == uuid.UUID(token_data.tenant_id),
                    Tenant.status == TenantStatus.ACTIVE
                )
            )
            tenant_result = await session.execute(tenant_stmt)
            tenant = tenant_result.scalar_one_or_none()
            
            if not tenant:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="租户不存在或已被暂停"
                )
    
    def _add_response_headers(self, response: Response, request_id: str, start_time: float) -> Response:
        """添加响应头"""
        process_time = time.time() - start_time
        
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Tenant-ID"] = tenant_context.get_tenant_id() or ""
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """速率限制中间件"""
    
    def __init__(self, app: ASGIApp, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_size = 60  # 60秒窗口
    
    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        # 如果禁用了速率限制，直接通过
        if settings.is_development and os.getenv("DISABLE_RATE_LIMITING"):
            return await call_next(request)
        
        # 获取客户端标识
        client_id = self._get_client_id(request)
        
        # 检查速率限制
        if await self._is_rate_limited(client_id):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "success": False,
                    "message": "请求频率过高，请稍后再试",
                    "request_id": getattr(request.state, 'request_id', ''),
                    "timestamp": datetime.utcnow().isoformat(),
                    "errors": [
                        {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": f"每分钟最多允许 {self.requests_per_minute} 次请求"
                        }
                    ]
                },
                headers={
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time() + self.window_size))
                }
            )
        
        return await call_next(request)
    
    def _get_client_id(self, request: Request) -> str:
        """获取客户端标识"""
        # 优先使用用户ID
        if hasattr(request.state, 'user_id'):
            return f"user:{request.state.user_id}"
        
        # 其次使用租户ID
        if hasattr(request.state, 'tenant_id'):
            return f"tenant:{request.state.tenant_id}"
        
        # 最后使用IP地址
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"
    
    async def _is_rate_limited(self, client_id: str) -> bool:
        """检查是否达到速率限制"""
        redis_client = redis_manager.get_client()
        
        # 使用滑动窗口计数器
        current_time = int(time.time())
        window_start = current_time - self.window_size
        
        # 清除过期的请求记录
        await redis_client.zremrangebyscore(
            f"rate_limit:{client_id}",
            0,
            window_start
        )
        
        # 获取当前窗口内的请求数
        current_requests = await redis_client.zcard(f"rate_limit:{client_id}")
        
        if current_requests >= self.requests_per_minute:
            return True
        
        # 记录当前请求
        await redis_client.zadd(
            f"rate_limit:{client_id}",
            {str(current_time): current_time}
        )
        
        # 设置过期时间
        await redis_client.expire(f"rate_limit:{client_id}", self.window_size)
        
        return False


class CORSMiddleware(BaseHTTPMiddleware):
    """CORS中间件"""
    
    def __init__(self, app: ASGIApp, allow_origins: List[str] = None):
        super().__init__(app)
        self.allow_origins = allow_origins or ["*"]
    
    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        # 处理预检请求
        if request.method == "OPTIONS":
            return self._create_preflight_response()
        
        # 处理正常请求
        response = await call_next(request)
        
        # 添加CORS头
        self._add_cors_headers(response)
        
        return response
    
    def _create_preflight_response(self) -> Response:
        """创建预检响应"""
        response = Response(status_code=200)
        self._add_cors_headers(response)
        return response
    
    def _add_cors_headers(self, response: Response):
        """添加CORS头"""
        response.headers["Access-Control-Allow-Origin"] = ",".join(self.allow_origins)
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Requested-With"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Max-Age"] = "86400"  # 24小时


class AuditLogMiddleware(BaseHTTPMiddleware):
    """审计日志中间件"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        # 记录请求信息
        request_info = {
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": dict(request.headers),
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", ""),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 添加用户信息（如果存在）
        if hasattr(request.state, 'user_id'):
            request_info.update({
                "user_id": request.state.user_id,
                "tenant_id": request.state.tenant_id,
                "user_email": request.state.user_email
            })
        
        # 处理请求
        response = await call_next(request)
        
        # 记录响应信息
        response_info = {
            "status_code": response.status_code,
            "headers": dict(response.headers)
        }
        
        # 异步记录审计日志
        await self._log_audit_event(request_info, response_info)
        
        return response
    
    async def _log_audit_event(self, request_info: Dict[str, Any], response_info: Dict[str, Any]):
        """记录审计事件"""
        try:
            # 过滤敏感信息
            filtered_headers = {
                k: v for k, v in request_info["headers"].items()
                if k.lower() not in ["authorization", "cookie", "x-api-key"]
            }
            request_info["headers"] = filtered_headers
            
            # 构造审计日志
            audit_log = {
                "request": request_info,
                "response": response_info,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # 存储到Redis（异步）
            redis_client = redis_manager.get_client()
            await redis_client.lpush(
                "audit_logs",
                json.dumps(audit_log)
            )
            
            # 限制队列长度
            await redis_client.ltrim("audit_logs", 0, 9999)
            
        except Exception as e:
            logger.error(f"审计日志记录失败: {str(e)}")


def get_current_tenant_id() -> Optional[str]:
    """获取当前租户ID"""
    return tenant_context.get_tenant_id()


def get_current_user_id() -> Optional[str]:
    """获取当前用户ID"""
    return tenant_context.get_user_id()


def get_current_user_roles() -> List[str]:
    """获取当前用户角色"""
    return tenant_context.get_user_roles()