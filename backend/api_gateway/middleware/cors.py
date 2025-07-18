"""
CORS中间件

处理跨域请求和安全头部
"""

from typing import Dict, List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ..config import settings
from ..utils.constants import SECURITY_HEADERS


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全头部中间件"""
    
    async def dispatch(self, request: Request, call_next):
        """添加安全头部"""
        response = await call_next(request)
        
        # 添加安全头部
        security_headers = settings.security_headers
        for header_name, header_value in security_headers.items():
            response.headers[header_name] = header_value
        
        return response


def setup_cors_middleware(app: FastAPI) -> None:
    """
    设置CORS中间件
    
    Args:
        app: FastAPI应用实例
    """
    
    # 添加CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
        allow_headers=["*"],
        expose_headers=[
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset"
        ]
    )
    
    # 添加安全头部中间件
    app.add_middleware(SecurityHeadersMiddleware)
    
    # 添加可信主机中间件（生产环境）
    if settings.environment == "production":
        allowed_hosts = ["*"]  # 可以根据需要配置具体的主机
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)


def get_cors_config() -> Dict[str, any]:
    """
    获取CORS配置
    
    Returns:
        CORS配置字典
    """
    return {
        "allow_origins": settings.cors_origins,
        "allow_credentials": settings.cors_allow_credentials,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
        "allow_headers": ["*"],
        "expose_headers": [
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset"
        ]
    }


def is_cors_preflight(request: Request) -> bool:
    """
    检查是否为CORS预检请求
    
    Args:
        request: 请求对象
        
    Returns:
        是否为预检请求
    """
    return (
        request.method == "OPTIONS" and
        "Origin" in request.headers and
        "Access-Control-Request-Method" in request.headers
    )


def get_origin_from_request(request: Request) -> str:
    """
    从请求中获取Origin
    
    Args:
        request: 请求对象
        
    Returns:
        Origin值
    """
    return request.headers.get("Origin", "")


def is_origin_allowed(origin: str) -> bool:
    """
    检查Origin是否被允许
    
    Args:
        origin: Origin值
        
    Returns:
        是否允许
    """
    if not origin:
        return False
    
    allowed_origins = settings.cors_origins
    
    # 如果允许所有来源
    if "*" in allowed_origins:
        return True
    
    # 检查是否在允许列表中
    return origin in allowed_origins