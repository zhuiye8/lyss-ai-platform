"""
认证中间件

负责JWT验证和用户身份信息注入
"""

import time
from typing import Optional, Dict, Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from fastapi import status

from ..core.security import jwt_manager, AuthHeaders
from ..core.logging import get_logger, log_auth_event
from ..utils.helpers import build_error_response, get_client_ip, parse_user_agent
from ..utils.constants import CUSTOM_HEADERS, ROUTE_PREFIXES
from ..config import settings


logger = get_logger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """认证中间件"""
    
    def __init__(self, app, skip_paths: Optional[list] = None):
        """
        初始化认证中间件
        
        Args:
            app: FastAPI应用实例
            skip_paths: 跳过认证的路径列表
        """
        super().__init__(app)
        self.skip_paths = skip_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico"
        ]
    
    async def dispatch(self, request: Request, call_next):
        """
        处理认证逻辑
        
        Args:
            request: 请求对象
            call_next: 下一个中间件或路由处理器
            
        Returns:
            响应对象
        """
        start_time = time.time()
        request_id = getattr(request.state, "request_id", "")
        path = request.url.path
        
        # 检查是否需要跳过认证
        if self._should_skip_auth(path):
            return await call_next(request)
        
        # 检查路由是否需要认证
        require_auth = self._check_route_requires_auth(path)
        
        if not require_auth:
            # 不需要认证，直接继续
            return await call_next(request)
        
        # 提取认证头部
        authorization = request.headers.get("Authorization")
        if not authorization:
            return await self._create_auth_error_response(
                "缺少认证头部",
                "2001",
                request_id,
                {"path": path}
            )
        
        # 提取Bearer令牌
        token = AuthHeaders.extract_bearer_token(authorization)
        if not token:
            return await self._create_auth_error_response(
                "无效的认证头部格式",
                "2003",
                request_id,
                {"authorization": authorization[:20] + "..."}
            )
        
        # 验证JWT令牌
        try:
            user_info = jwt_manager.extract_user_info(token)
            
            # 记录认证成功事件
            log_auth_event(
                logger,
                "jwt_validation",
                user_info.get("user_id"),
                user_info.get("tenant_id"),
                request_id,
                success=True,
                data={
                    "path": path,
                    "method": request.method,
                    "user_role": user_info.get("role")
                }
            )
            
            # 将用户信息注入到请求状态
            request.state.user_info = user_info
            request.state.authenticated = True
            
            # 记录认证成功，但不在这里修改请求头
            # 让proxy_service负责添加认证头部
            
        except Exception as e:
            # 提取具体的错误信息
            error_message = str(e)
            if hasattr(e, 'detail'):
                error_message = str(e.detail)
            elif hasattr(e, 'message'):
                error_message = str(e.message)
            
            # 记录认证失败事件
            log_auth_event(
                logger,
                "jwt_validation",
                None,
                None,
                request_id,
                success=False,
                error_code="2003",
                data={
                    "path": path,
                    "method": request.method,
                    "error": error_message,
                    "exception_type": type(e).__name__
                }
            )
            
            return await self._create_auth_error_response(
                f"认证失败: {error_message}",
                "2003",
                request_id,
                {"path": path}
            )
        
        # 继续处理请求
        response = await call_next(request)
        
        # 记录认证处理时间
        duration_ms = int((time.time() - start_time) * 1000)
        if duration_ms > 100:  # 如果认证耗时超过100ms，记录警告
            logger.warning(
                f"认证处理耗时较长: {duration_ms}ms",
                extra={
                    "request_id": request_id,
                    "path": path,
                    "duration_ms": duration_ms
                }
            )
        
        return response
    
    def _should_skip_auth(self, path: str) -> bool:
        """
        检查是否应该跳过认证
        
        Args:
            path: 请求路径
            
        Returns:
            是否跳过认证
        """
        # 检查跳过路径列表
        for skip_path in self.skip_paths:
            if path.startswith(skip_path):
                return True
        
        # 检查静态文件路径
        static_extensions = ['.ico', '.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg']
        if any(path.endswith(ext) for ext in static_extensions):
            return True
        
        return False
    
    def _check_route_requires_auth(self, path: str) -> bool:
        """
        检查路由是否需要认证
        
        Args:
            path: 请求路径
            
        Returns:
            是否需要认证
        """
        route_config = settings.route_config
        
        # 检查每个路由前缀
        for route_prefix, config in route_config.items():
            if path.startswith(route_prefix):
                return config.require_auth
        
        # 默认需要认证
        return True
    
    async def _create_auth_error_response(
        self,
        message: str,
        error_code: str,
        request_id: str,
        details: Optional[Dict[str, Any]] = None
    ) -> JSONResponse:
        """
        创建认证错误响应
        
        Args:
            message: 错误消息
            error_code: 错误代码
            request_id: 请求ID
            details: 错误详情
            
        Returns:
            JSON错误响应
        """
        error_response = build_error_response(
            error_code=error_code,
            message=message,
            details=details,
            request_id=request_id
        )
        
        return JSONResponse(
            content=error_response,
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"}
        )


class TenantContextMiddleware(BaseHTTPMiddleware):
    """租户上下文中间件"""
    
    async def dispatch(self, request: Request, call_next):
        """
        注入租户上下文信息
        
        Args:
            request: 请求对象
            call_next: 下一个中间件或路由处理器
            
        Returns:
            响应对象
        """
        # 获取用户信息
        user_info = getattr(request.state, "user_info", {})
        
        # 注入租户上下文
        if user_info:
            request.state.tenant_id = user_info.get("tenant_id")
            request.state.user_id = user_info.get("user_id")
            request.state.user_role = user_info.get("role")
            request.state.user_email = user_info.get("email")
        
        # 继续处理请求
        response = await call_next(request)
        
        return response


def get_current_user_from_request(request: Request) -> Dict[str, Any]:
    """
    从请求中获取当前用户信息
    
    Args:
        request: 请求对象
        
    Returns:
        用户信息字典
    """
    return getattr(request.state, "user_info", {})


def get_current_tenant_id_from_request(request: Request) -> Optional[str]:
    """
    从请求中获取当前租户ID
    
    Args:
        request: 请求对象
        
    Returns:
        租户ID或None
    """
    return getattr(request.state, "tenant_id", None)


def is_authenticated(request: Request) -> bool:
    """
    检查请求是否已认证
    
    Args:
        request: 请求对象
        
    Returns:
        是否已认证
    """
    return getattr(request.state, "authenticated", False)


def has_role(request: Request, required_role: str) -> bool:
    """
    检查用户是否具有指定角色
    
    Args:
        request: 请求对象
        required_role: 需要的角色
        
    Returns:
        是否具有角色
    """
    user_role = getattr(request.state, "user_role", "")
    
    # 角色级别：end_user < tenant_admin < super_admin
    role_levels = {
        "end_user": 1,
        "tenant_admin": 2,
        "super_admin": 3
    }
    
    current_level = role_levels.get(user_role, 0)
    required_level = role_levels.get(required_role, 0)
    
    return current_level >= required_level