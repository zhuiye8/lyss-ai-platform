"""
JWT认证中间件

集成租户认证和权限验证功能。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import logging
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
security = HTTPBearer()


async def auth_middleware(request: Request, call_next):
    """
    JWT认证中间件
    
    验证请求中的JWT令牌并提取租户信息。
    
    Args:
        request: FastAPI请求对象
        call_next: 下一个中间件或路由处理器
        
    Returns:
        Response: 处理后的响应
        
    Raises:
        HTTPException 401: 认证失败
    """
    # 跳过不需要认证的路径
    exempt_paths = [
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc"
    ]
    
    if request.url.path in exempt_paths:
        return await call_next(request)
    
    try:
        # 获取Authorization头
        authorization = request.headers.get("Authorization")
        
        if not authorization or not authorization.startswith("Bearer "):
            logger.warning(f"缺少Authorization头 - 路径: {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少认证令牌",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # 提取JWT令牌
        token = authorization.split(" ")[1]
        
        # 验证JWT令牌
        try:
            payload = jwt.decode(
                token, 
                settings.secret_key, 
                algorithms=[settings.jwt_algorithm]
            )
            
            # 提取用户和租户信息
            user_id = payload.get("sub")
            tenant_id = payload.get("tenant_id") 
            user_email = payload.get("email")
            user_role = payload.get("role")
            
            if not user_id or not tenant_id:
                logger.warning("JWT令牌缺少必要字段")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="无效的认证令牌"
                )
            
            # 将认证信息添加到请求状态
            request.state.user_id = user_id
            request.state.tenant_id = tenant_id
            request.state.user_email = user_email
            request.state.user_role = user_role
            
            logger.debug(f"用户认证成功 - user_id: {user_id}, tenant_id: {tenant_id}")
            
        except JWTError as e:
            logger.warning(f"JWT令牌验证失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证令牌",
                headers={"WWW-Authenticate": "Bearer"}
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"认证中间件处理失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="认证服务错误"
        )
    
    # 继续处理请求
    response = await call_next(request)
    return response


def verify_tenant_access(required_tenant_id: str, current_tenant_id: str) -> bool:
    """
    验证租户访问权限
    
    Args:
        required_tenant_id: 要求的租户ID
        current_tenant_id: 当前用户的租户ID
        
    Returns:
        bool: 是否有访问权限
    """
    # 超级管理员可以访问所有租户数据
    if current_tenant_id == "super-admin":
        return True
    
    # 普通用户只能访问自己租户的数据
    return required_tenant_id == current_tenant_id


def require_role(allowed_roles: list):
    """
    角色权限装饰器
    
    Args:
        allowed_roles: 允许的角色列表
        
    Returns:
        装饰器函数
    """
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            user_role = getattr(request.state, "user_role", None)
            
            if not user_role or user_role not in allowed_roles:
                logger.warning(f"权限不足 - 当前角色: {user_role}, 需要角色: {allowed_roles}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="权限不足"
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator