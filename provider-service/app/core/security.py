"""
安全认证和权限管理

处理JWT认证、租户上下文提取、权限验证等安全相关功能。
与auth-service集成，提供统一的认证机制。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt.exceptions import InvalidTokenError
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)
security = HTTPBearer()


class JWTHandler:
    """JWT处理器"""
    
    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """
        解码JWT令牌
        
        Args:
            token: JWT令牌字符串
            
        Returns:
            Dict: 解码后的载荷信息
            
        Raises:
            HTTPException: 令牌无效或已过期
        """
        try:
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.algorithm]
            )
            
            # 检查令牌是否过期
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="令牌已过期"
                )
            
            return payload
            
        except InvalidTokenError as e:
            logger.warning(f"JWT令牌解码失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证令牌"
            )
    
    @staticmethod
    def extract_tenant_id(payload: Dict[str, Any]) -> str:
        """
        从JWT载荷中提取租户ID
        
        Args:
            payload: JWT载荷
            
        Returns:
            str: 租户ID
            
        Raises:
            HTTPException: 缺少租户信息
        """
        tenant_id = payload.get("tenant_id")
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="令牌中缺少租户信息"
            )
        return tenant_id
    
    @staticmethod
    def extract_user_id(payload: Dict[str, Any]) -> str:
        """
        从JWT载荷中提取用户ID
        
        Args:
            payload: JWT载荷
            
        Returns:
            str: 用户ID
        """
        return payload.get("sub") or payload.get("user_id", "")


async def get_current_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    获取当前请求的JWT令牌
    
    Args:
        credentials: HTTP授权凭据
        
    Returns:
        str: JWT令牌
    """
    return credentials.credentials


async def get_current_payload(
    token: str = Depends(get_current_token)
) -> Dict[str, Any]:
    """
    获取当前请求的JWT载荷
    
    Args:
        token: JWT令牌
        
    Returns:
        Dict: JWT载荷信息
    """
    return JWTHandler.decode_token(token)


async def get_current_tenant_id(
    payload: Dict[str, Any] = Depends(get_current_payload)
) -> str:
    """
    获取当前请求的租户ID
    
    Args:
        payload: JWT载荷
        
    Returns:
        str: 租户ID
    """
    return JWTHandler.extract_tenant_id(payload)


async def get_current_user_id(
    payload: Dict[str, Any] = Depends(get_current_payload)
) -> str:
    """
    获取当前请求的用户ID
    
    Args:
        payload: JWT载荷
        
    Returns:
        str: 用户ID
    """
    return JWTHandler.extract_user_id(payload)


class PermissionChecker:
    """权限检查器"""
    
    @staticmethod
    def check_admin_permission(payload: Dict[str, Any]) -> bool:
        """
        检查管理员权限
        
        Args:
            payload: JWT载荷
            
        Returns:
            bool: 是否具有管理员权限
        """
        role = payload.get("role", "")
        return role in ["super_admin", "tenant_admin"]
    
    @staticmethod
    def check_tenant_access(payload: Dict[str, Any], required_tenant_id: str) -> bool:
        """
        检查租户访问权限
        
        Args:
            payload: JWT载荷
            required_tenant_id: 要求的租户ID
            
        Returns:
            bool: 是否具有访问权限
        """
        token_tenant_id = payload.get("tenant_id")
        return token_tenant_id == required_tenant_id


async def require_admin_permission(
    payload: Dict[str, Any] = Depends(get_current_payload)
) -> Dict[str, Any]:
    """
    要求管理员权限的依赖注入
    
    Args:
        payload: JWT载荷
        
    Returns:
        Dict: JWT载荷（验证通过）
        
    Raises:
        HTTPException: 权限不足
    """
    if not PermissionChecker.check_admin_permission(payload):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足：需要管理员权限"
        )
    return payload


class TenantContext:
    """租户上下文"""
    
    def __init__(self, tenant_id: str, user_id: str, role: str):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.role = role
    
    @property
    def is_admin(self) -> bool:
        """是否为管理员"""
        return self.role in ["super_admin", "tenant_admin"]


async def get_tenant_context(
    payload: Dict[str, Any] = Depends(get_current_payload)
) -> TenantContext:
    """
    获取租户上下文
    
    Args:
        payload: JWT载荷
        
    Returns:
        TenantContext: 租户上下文对象
    """
    return TenantContext(
        tenant_id=JWTHandler.extract_tenant_id(payload),
        user_id=JWTHandler.extract_user_id(payload),
        role=payload.get("role", "end_user")
    )