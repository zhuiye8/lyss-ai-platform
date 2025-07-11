"""
依赖注入模块

提供FastAPI依赖注入函数，用于认证、权限验证等
"""

from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .security import jwt_manager, AuthHeaders
from ..config import settings


security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """
    获取当前用户信息
    
    Args:
        request: FastAPI请求对象
        credentials: HTTP认证凭证
        
    Returns:
        用户信息字典
        
    Raises:
        HTTPException: 认证失败
    """
    # 检查是否需要认证
    path = request.url.path
    route_config = settings.route_config
    
    # 查找匹配的路由配置
    require_auth = True
    for route_prefix, config in route_config.items():
        if path.startswith(route_prefix):
            require_auth = config.require_auth
            break
    
    # 如果不需要认证，返回空用户信息
    if not require_auth:
        return {}
    
    # 提取Bearer令牌
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少认证令牌",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证令牌为空",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # 验证并提取用户信息
    try:
        user_info = jwt_manager.extract_user_info(token)
        return user_info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"认证失败: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取当前活跃用户信息
    
    Args:
        current_user: 当前用户信息
        
    Returns:
        活跃用户信息字典
    """
    # 如果用户信息为空（无需认证的路由），直接返回
    if not current_user:
        return current_user
    
    # TODO: 这里可以添加用户状态检查逻辑
    # 比如检查用户是否被禁用、租户是否过期等
    
    return current_user


async def get_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    获取管理员用户信息
    
    Args:
        current_user: 当前用户信息
        
    Returns:
        管理员用户信息字典
        
    Raises:
        HTTPException: 权限不足
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要认证"
        )
    
    user_role = current_user.get("role", "")
    if user_role not in ["tenant_admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足：需要管理员角色"
        )
    
    return current_user


async def get_super_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    获取超级管理员用户信息
    
    Args:
        current_user: 当前用户信息
        
    Returns:
        超级管理员用户信息字典
        
    Raises:
        HTTPException: 权限不足
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要认证"
        )
    
    user_role = current_user.get("role", "")
    if user_role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足：需要超级管理员角色"
        )
    
    return current_user


def get_request_id(request: Request) -> str:
    """
    获取请求ID
    
    Args:
        request: FastAPI请求对象
        
    Returns:
        请求ID字符串
    """
    return getattr(request.state, "request_id", "")


def get_tenant_id(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Optional[str]:
    """
    获取租户ID
    
    Args:
        current_user: 当前用户信息
        
    Returns:
        租户ID或None
    """
    if not current_user:
        return None
    return current_user.get("tenant_id")