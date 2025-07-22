"""
认证中间件

提供自动令牌验证、用户上下文注入和权限预检功能。
支持Bearer令牌、API Key等多种认证方式。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

from typing import Optional, Callable, List
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import HTTPException, status
import time
import json

from ..dependencies import get_jwt_manager, get_rbac_manager
from ..utils.logging import get_logger

logger = get_logger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    认证中间件
    
    功能特性：
    - 自动从请求头提取JWT令牌
    - 验证令牌有效性和黑名单状态
    - 注入用户上下文到请求对象
    - 支持公开路径白名单
    - 提供详细的认证失败日志
    """
    
    def __init__(
        self,
        app,
        public_paths: Optional[List[str]] = None,
        jwt_manager_factory: Optional[Callable] = None,
        require_auth_by_default: bool = True
    ):
        super().__init__(app)
        self.public_paths = public_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/password/reset/request",
            "/api/v1/auth/password/policy"
        ]
        self.jwt_manager_factory = jwt_manager_factory or get_jwt_manager
        self.require_auth_by_default = require_auth_by_default
        
    async def dispatch(self, request: Request, call_next):
        """处理请求认证"""
        start_time = time.time()
        
        # 检查是否为公开路径
        if self._is_public_path(request.url.path):
            logger.debug(f"公开路径访问: {request.url.path}")
            return await call_next(request)
        
        # 提取认证信息
        auth_result = await self._extract_auth_info(request)
        
        # 如果需要认证但没有提供有效令牌
        if self.require_auth_by_default and not auth_result.get("authenticated"):
            return self._create_auth_error_response(
                auth_result.get("error", "缺少认证令牌"),
                auth_result.get("status_code", status.HTTP_401_UNAUTHORIZED)
            )
        
        # 注入用户上下文
        if auth_result.get("authenticated"):
            request.state.user = auth_result["user"]
            request.state.authenticated = True
            request.state.auth_context = auth_result.get("auth_context")
            
            logger.debug(
                f"用户认证成功: {auth_result['user'].get('email')}",
                operation="auth_middleware",
                data={
                    "user_id": auth_result["user"].get("sub"),
                    "tenant_id": auth_result["user"].get("tenant_id"),
                    "path": request.url.path
                }
            )
        else:
            request.state.user = None
            request.state.authenticated = False
            request.state.auth_context = None
        
        try:
            response = await call_next(request)
            
            # 记录请求处理时间
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except HTTPException as e:
            logger.warning(
                f"请求处理HTTP异常: {e.detail}",
                operation="auth_middleware",
                data={
                    "status_code": e.status_code,
                    "path": request.url.path,
                    "user_id": auth_result.get("user", {}).get("sub")
                }
            )
            raise
        except Exception as e:
            logger.error(
                f"认证中间件异常: {str(e)}",
                operation="auth_middleware",
                data={
                    "path": request.url.path,
                    "error": str(e),
                    "user_id": auth_result.get("user", {}).get("sub")
                }
            )
            raise
    
    def _is_public_path(self, path: str) -> bool:
        """检查是否为公开路径"""
        # 精确匹配
        if path in self.public_paths:
            return True
        
        # 前缀匹配（用于静态资源等）
        public_prefixes = ["/static/", "/assets/", "/favicon"]
        for prefix in public_prefixes:
            if path.startswith(prefix):
                return True
                
        return False
    
    async def _extract_auth_info(self, request: Request) -> dict:
        """提取认证信息"""
        try:
            # 提取Authorization header
            auth_header = request.headers.get("Authorization", "")
            
            if not auth_header:
                return {
                    "authenticated": False,
                    "error": "缺少Authorization头",
                    "status_code": status.HTTP_401_UNAUTHORIZED
                }
            
            # 解析Bearer令牌
            if not auth_header.startswith("Bearer "):
                return {
                    "authenticated": False,
                    "error": "无效的认证格式，需要Bearer令牌",
                    "status_code": status.HTTP_401_UNAUTHORIZED
                }
            
            token = auth_header[7:]  # 移除"Bearer "前缀
            
            if not token:
                return {
                    "authenticated": False,
                    "error": "空的认证令牌",
                    "status_code": status.HTTP_401_UNAUTHORIZED
                }
            
            # 验证JWT令牌
            jwt_manager = self.jwt_manager_factory()
            validation_result = await jwt_manager.verify_token(token, "access")
            
            if not validation_result.is_valid:
                return {
                    "authenticated": False,
                    "error": validation_result.error_message,
                    "status_code": status.HTTP_401_UNAUTHORIZED
                }
            
            # 构建用户上下文
            user_data = validation_result.payload.dict()
            auth_context = {
                "user_id": user_data["sub"],
                "tenant_id": user_data["tenant_id"],
                "session_id": user_data.get("session_id"),
                "permissions": user_data.get("permissions", []),
                "role": user_data.get("role"),
                "auth_method": "jwt_bearer"
            }
            
            return {
                "authenticated": True,
                "user": user_data,
                "auth_context": auth_context,
                "token": token
            }
            
        except Exception as e:
            logger.error(
                f"认证信息提取异常: {str(e)}",
                operation="extract_auth_info",
                data={
                    "path": request.url.path,
                    "error": str(e)
                }
            )
            return {
                "authenticated": False,
                "error": "认证服务异常",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR
            }
    
    def _create_auth_error_response(self, error_message: str, status_code: int) -> Response:
        """创建认证错误响应"""
        error_data = {
            "success": False,
            "error": {
                "code": "AUTH_ERROR",
                "message": error_message,
                "timestamp": time.time()
            }
        }
        
        return Response(
            content=json.dumps(error_data, ensure_ascii=False),
            status_code=status_code,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "WWW-Authenticate": "Bearer"
            }
        )


class PermissionMiddleware(BaseHTTPMiddleware):
    """
    权限中间件
    
    基于路径模式自动检查用户权限，支持细粒度的权限控制。
    """
    
    def __init__(
        self,
        app,
        permission_rules: Optional[dict] = None,
        rbac_manager_factory: Optional[Callable] = None
    ):
        super().__init__(app)
        self.permission_rules = permission_rules or {
            # 管理员接口权限规则
            "/api/v1/admin/*": ["system:admin"],
            "/api/v1/auth/statistics/*": ["system:monitor"],
            
            # 租户管理权限规则
            "/api/v1/tenants/*": ["tenant:manage"],
            "/api/v1/users/*/permissions": ["user:manage"],
            
            # 用户操作权限规则
            "/api/v1/users/*/sessions": ["user:sessions"],
        }
        self.rbac_manager_factory = rbac_manager_factory or get_rbac_manager
    
    async def dispatch(self, request: Request, call_next):
        """检查权限并处理请求"""
        # 跳过未认证的请求
        if not getattr(request.state, "authenticated", False):
            return await call_next(request)
        
        # 检查路径权限要求
        required_permissions = self._get_required_permissions(request.url.path, request.method)
        
        if required_permissions:
            user_data = getattr(request.state, "user", {})
            
            # 检查权限
            rbac_manager = self.rbac_manager_factory()
            
            from ..models.auth_models import TokenPayload
            token_payload = TokenPayload(**user_data)
            
            for permission in required_permissions:
                permission_result = await rbac_manager.check_permission(
                    token_payload,
                    permission
                )
                
                if not permission_result.granted:
                    logger.warning(
                        f"权限不足: 用户{user_data.get('email')}尝试访问需要{permission}权限的资源",
                        operation="permission_middleware",
                        data={
                            "user_id": user_data.get("sub"),
                            "required_permission": permission,
                            "user_permissions": user_data.get("permissions", []),
                            "path": request.url.path,
                            "method": request.method
                        }
                    )
                    
                    error_data = {
                        "success": False,
                        "error": {
                            "code": "PERMISSION_DENIED",
                            "message": f"需要权限: {permission}",
                            "timestamp": time.time()
                        }
                    }
                    
                    return Response(
                        content=json.dumps(error_data, ensure_ascii=False),
                        status_code=status.HTTP_403_FORBIDDEN,
                        headers={"Content-Type": "application/json; charset=utf-8"}
                    )
        
        return await call_next(request)
    
    def _get_required_permissions(self, path: str, method: str) -> List[str]:
        """获取路径所需的权限列表"""
        required_permissions = []
        
        for pattern, permissions in self.permission_rules.items():
            if self._match_path_pattern(path, pattern):
                # 可以根据HTTP方法细化权限
                if method == "GET":
                    # 读取权限通常较宽松
                    required_permissions.extend([p for p in permissions if ":read" in p or ":view" in p])
                elif method in ["POST", "PUT", "PATCH"]:
                    # 写入权限更严格
                    required_permissions.extend([p for p in permissions if ":write" in p or ":manage" in p])
                elif method == "DELETE":
                    # 删除权限最严格
                    required_permissions.extend([p for p in permissions if ":delete" in p or ":admin" in p])
                else:
                    # 默认要求所有权限
                    required_permissions.extend(permissions)
        
        return list(set(required_permissions))  # 去重
    
    def _match_path_pattern(self, path: str, pattern: str) -> bool:
        """匹配路径模式"""
        import fnmatch
        return fnmatch.fnmatch(path, pattern)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    安全头中间件
    
    自动添加安全相关的HTTP头，提升应用安全性。
    """
    
    def __init__(self, app, security_headers: Optional[dict] = None):
        super().__init__(app)
        self.security_headers = security_headers or {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        }
    
    async def dispatch(self, request: Request, call_next):
        """添加安全头并处理请求"""
        response = await call_next(request)
        
        # 添加安全头
        for header_name, header_value in self.security_headers.items():
            response.headers[header_name] = header_value
        
        # 移除可能泄露信息的头
        response.headers.pop("Server", None)
        
        return response