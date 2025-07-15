"""
代理路由模块

处理所有需要代理的API请求
"""

from typing import Union, Optional, Dict, Any
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import Response
from starlette.responses import StreamingResponse

from ..services.proxy_service import proxy_service
# 移除不再使用的依赖注入导入
from ..core.logging import get_logger
from ..utils.exceptions import InvalidInputError
from ..config import settings


logger = get_logger(__name__)
router = APIRouter()


# 移除不再使用的get_conditional_user函数
# 现在认证完全由认证中间件处理


@router.api_route(
    "/api/v1/auth/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    response_model=None
)
async def proxy_auth_requests(
    path: str,
    request: Request
):
    """
    代理认证服务请求
    
    Args:
        path: 请求路径
        request: FastAPI请求对象
        
    Returns:
        HTTP响应或流式响应
    """
    full_path = f"/api/v1/auth/{path}" if path else "/api/v1/auth"
    return await proxy_service.route_request(request, full_path, request.method)


@router.api_route(
    "/api/v1/admin/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    response_model=None
)
async def proxy_admin_requests(
    path: str,
    request: Request
):
    """
    代理管理服务请求
    
    Args:
        path: 请求路径
        request: FastAPI请求对象
        
    Returns:
        HTTP响应或流式响应
    """
    full_path = f"/api/v1/admin/{path}" if path else "/api/v1/admin"
    return await proxy_service.route_request(request, full_path, request.method)


@router.api_route(
    "/api/v1/chat/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    response_model=None
)
async def proxy_chat_requests(
    path: str,
    request: Request
):
    """
    代理聊天服务请求
    
    Args:
        path: 请求路径
        request: FastAPI请求对象
        current_user: 当前用户信息
        
    Returns:
        HTTP响应或流式响应
    """
    full_path = f"/api/v1/chat/{path}" if path else "/api/v1/chat"
    return await proxy_service.route_request(request, full_path, request.method)


@router.api_route(
    "/api/v1/memory/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    response_model=None
)
async def proxy_memory_requests(
    path: str,
    request: Request
):
    """
    代理记忆服务请求
    
    Args:
        path: 请求路径
        request: FastAPI请求对象
        current_user: 当前用户信息
        
    Returns:
        HTTP响应或流式响应
    """
    full_path = f"/api/v1/memory/{path}" if path else "/api/v1/memory"
    return await proxy_service.route_request(request, full_path, request.method)


# 处理根路径的认证请求
@router.api_route(
    "/api/v1/auth",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    response_model=None
)
async def proxy_auth_root(
    request: Request
):
    """
    代理认证服务根路径请求
    
    Args:
        request: FastAPI请求对象
        current_user: 当前用户信息（条件性）
        
    Returns:
        HTTP响应或流式响应
    """
    return await proxy_service.route_request(request, "/api/v1/auth", request.method)


# 处理根路径的管理请求
@router.api_route(
    "/api/v1/admin",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    response_model=None
)
async def proxy_admin_root(
    request: Request
):
    """
    代理管理服务根路径请求
    
    Args:
        request: FastAPI请求对象
        current_user: 当前用户信息
        
    Returns:
        HTTP响应或流式响应
    """
    return await proxy_service.route_request(request, "/api/v1/admin", request.method)


# 处理根路径的聊天请求
@router.api_route(
    "/api/v1/chat",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    response_model=None
)
async def proxy_chat_root(
    request: Request
):
    """
    代理聊天服务根路径请求
    
    Args:
        request: FastAPI请求对象
        current_user: 当前用户信息
        
    Returns:
        HTTP响应或流式响应
    """
    return await proxy_service.route_request(request, "/api/v1/chat", request.method)


# 处理根路径的记忆请求
@router.api_route(
    "/api/v1/memory",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    response_model=None
)
async def proxy_memory_root(
    request: Request
):
    """
    代理记忆服务根路径请求
    
    Args:
        request: FastAPI请求对象
        current_user: 当前用户信息
        
    Returns:
        HTTP响应或流式响应
    """
    return await proxy_service.route_request(request, "/api/v1/memory", request.method)