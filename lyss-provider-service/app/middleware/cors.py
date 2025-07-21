"""
CORS跨域中间件

处理跨域资源共享（CORS）请求，支持开发和生产环境的不同配置。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import logging
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response

from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def get_cors_config() -> dict:
    """
    获取CORS配置
    
    根据运行环境返回不同的CORS配置。
    
    Returns:
        dict: CORS配置参数
    """
    if settings.environment == "development":
        # 开发环境：允许所有来源
        return {
            "allow_origins": ["*"],
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
            "expose_headers": [
                "X-Request-ID",
                "X-Response-Time", 
                "X-RateLimit-Limit",
                "X-RateLimit-Remaining",
                "X-RateLimit-Reset"
            ]
        }
    
    elif settings.environment == "staging":
        # 测试环境：允许特定测试域名
        return {
            "allow_origins": [
                "http://localhost:3000",
                "http://localhost:3001", 
                "https://staging.lyss.dev",
                "https://test.lyss.dev"
            ],
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
            "allow_headers": [
                "Content-Type",
                "Authorization",
                "Accept",
                "Origin",
                "User-Agent",
                "X-Requested-With",
                "X-Request-ID"
            ],
            "expose_headers": [
                "X-Request-ID",
                "X-Response-Time",
                "X-RateLimit-Limit", 
                "X-RateLimit-Remaining",
                "X-RateLimit-Reset"
            ]
        }
    
    else:
        # 生产环境：严格的CORS策略
        return {
            "allow_origins": [
                "https://lyss.dev",
                "https://www.lyss.dev",
                "https://app.lyss.dev"
            ],
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH"],
            "allow_headers": [
                "Content-Type",
                "Authorization", 
                "Accept",
                "Origin",
                "X-Request-ID"
            ],
            "expose_headers": [
                "X-Request-ID",
                "X-Response-Time"
            ]
        }


def setup_cors_middleware(app):
    """
    设置CORS中间件
    
    Args:
        app: FastAPI应用实例
    """
    cors_config = get_cors_config()
    
    logger.info(f"配置CORS中间件 - 环境: {settings.environment}")
    logger.debug(f"CORS配置: {cors_config}")
    
    app.add_middleware(
        CORSMiddleware,
        **cors_config
    )


async def cors_middleware(request: Request, call_next):
    """
    自定义CORS中间件
    
    提供更精细的CORS控制，支持动态origin验证。
    
    Args:
        request: FastAPI请求对象
        call_next: 下一个中间件或路由处理器
        
    Returns:
        Response: 处理后的响应
    """
    origin = request.headers.get("origin")
    
    # 处理预检请求
    if request.method == "OPTIONS":
        if _is_allowed_origin(origin):
            response = Response()
            _add_cors_headers(response, origin)
            return response
    
    # 处理普通请求
    response = await call_next(request)
    
    if _is_allowed_origin(origin):
        _add_cors_headers(response, origin)
    
    return response


def _is_allowed_origin(origin: str) -> bool:
    """
    检查origin是否被允许
    
    Args:
        origin: 请求来源
        
    Returns:
        bool: 是否允许此来源
    """
    if not origin:
        return False
    
    cors_config = get_cors_config()
    allowed_origins = cors_config.get("allow_origins", [])
    
    # 如果允许所有来源
    if "*" in allowed_origins:
        return True
    
    # 检查是否在允许列表中
    if origin in allowed_origins:
        return True
    
    # 检查是否匹配通配符模式（如果需要）
    for allowed_origin in allowed_origins:
        if _match_origin_pattern(origin, allowed_origin):
            return True
    
    logger.warning(f"不允许的origin: {origin}")
    return False


def _match_origin_pattern(origin: str, pattern: str) -> bool:
    """
    匹配origin模式
    
    Args:
        origin: 实际来源
        pattern: 模式字符串
        
    Returns:
        bool: 是否匹配
    """
    # 简单的通配符匹配（可以根据需要扩展）
    if pattern.startswith("*."):
        domain = pattern[2:]
        return origin.endswith(f".{domain}") or origin == domain
    
    return origin == pattern


def _add_cors_headers(response: Response, origin: str):
    """
    添加CORS响应头
    
    Args:
        response: 响应对象
        origin: 请求来源
    """
    cors_config = get_cors_config()
    
    # 设置允许的来源
    if "*" in cors_config.get("allow_origins", []):
        response.headers["Access-Control-Allow-Origin"] = "*"
    else:
        response.headers["Access-Control-Allow-Origin"] = origin
    
    # 设置允许的方法
    allow_methods = cors_config.get("allow_methods", [])
    if allow_methods:
        if "*" in allow_methods:
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
        else:
            response.headers["Access-Control-Allow-Methods"] = ", ".join(allow_methods)
    
    # 设置允许的头部
    allow_headers = cors_config.get("allow_headers", [])
    if allow_headers:
        if "*" in allow_headers:
            response.headers["Access-Control-Allow-Headers"] = "*"
        else:
            response.headers["Access-Control-Allow-Headers"] = ", ".join(allow_headers)
    
    # 设置暴露的头部
    expose_headers = cors_config.get("expose_headers", [])
    if expose_headers:
        response.headers["Access-Control-Expose-Headers"] = ", ".join(expose_headers)
    
    # 设置是否允许凭证
    if cors_config.get("allow_credentials", False):
        response.headers["Access-Control-Allow-Credentials"] = "true"
    
    # 设置预检请求的缓存时间
    response.headers["Access-Control-Max-Age"] = "86400"  # 24小时


def log_cors_request(request: Request):
    """
    记录CORS请求日志
    
    Args:
        request: 请求对象
    """
    origin = request.headers.get("origin")
    method = request.method
    
    if origin:
        logger.debug(f"CORS请求 - Origin: {origin}, Method: {method}, Path: {request.url.path}")
    
    if method == "OPTIONS":
        logger.debug(f"预检请求 - Origin: {origin}, Path: {request.url.path}")