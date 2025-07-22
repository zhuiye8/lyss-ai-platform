"""
依赖注入系统

为FastAPI路由提供统一的依赖注入服务，管理所有核心组件的生命周期。
包括JWT管理器、认证管理器、RBAC管理器、会话管理器等核心服务的依赖注入。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from .config import Settings, get_settings
from .core.jwt_manager import JWTManager
from .core.auth_manager import AuthManager
from .core.rbac_manager import RBACManager
from .core.session_manager import SessionManager
from .core.oauth2_manager import OAuth2Manager
from .core.mfa_manager import MFAManager
from .core.security_policy_manager import SecurityPolicyManager
from .utils.redis_client import RedisClient, get_redis_client
from .utils.logging import get_logger

logger = get_logger(__name__)


# =====================================================
# 核心管理器依赖注入
# =====================================================

@lru_cache
def get_jwt_manager(
    settings: Annotated[Settings, Depends(get_settings)],
    redis_client: Annotated[RedisClient, Depends(get_redis_client)]
) -> JWTManager:
    """获取JWT管理器实例"""
    return JWTManager(
        secret_key=settings.secret_key,
        algorithm=settings.algorithm,
        redis_client=redis_client,
        settings=settings
    )


@lru_cache
def get_rbac_manager(
    redis_client: Annotated[RedisClient, Depends(get_redis_client)]
) -> RBACManager:
    """获取RBAC管理器实例"""
    return RBACManager(redis_client=redis_client)


@lru_cache
def get_session_manager(
    settings: Annotated[Settings, Depends(get_settings)],
    redis_client: Annotated[RedisClient, Depends(get_redis_client)]
) -> SessionManager:
    """获取会话管理器实例"""
    return SessionManager(
        redis_client=redis_client,
        settings=settings
    )


@lru_cache
def get_oauth2_manager(
    settings: Annotated[Settings, Depends(get_settings)],
    redis_client: Annotated[RedisClient, Depends(get_redis_client)]
) -> OAuth2Manager:
    """获取OAuth2管理器实例"""
    return OAuth2Manager(
        redis_client=redis_client,
        settings=settings
    )


@lru_cache
def get_mfa_manager(
    settings: Annotated[Settings, Depends(get_settings)],
    redis_client: Annotated[RedisClient, Depends(get_redis_client)]
) -> MFAManager:
    """获取MFA管理器实例"""
    return MFAManager(
        redis_client=redis_client,
        settings=settings
    )


@lru_cache
def get_security_policy_manager(
    settings: Annotated[Settings, Depends(get_settings)],
    redis_client: Annotated[RedisClient, Depends(get_redis_client)]
) -> SecurityPolicyManager:
    """获取安全策略管理器实例"""
    return SecurityPolicyManager(
        redis_client=redis_client,
        settings=settings
    )


@lru_cache
def get_auth_manager(
    settings: Annotated[Settings, Depends(get_settings)],
    redis_client: Annotated[RedisClient, Depends(get_redis_client)],
    jwt_manager: Annotated[JWTManager, Depends(get_jwt_manager)],
    rbac_manager: Annotated[RBACManager, Depends(get_rbac_manager)],
    session_manager: Annotated[SessionManager, Depends(get_session_manager)]
) -> AuthManager:
    """获取认证管理器实例"""
    return AuthManager(
        jwt_manager=jwt_manager,
        rbac_manager=rbac_manager,
        session_manager=session_manager,
        redis_client=redis_client,
        settings=settings
    )


# =====================================================
# 快捷依赖注入类型别名
# =====================================================

# 用于路由函数参数的类型注解
JWTManagerDep = Annotated[JWTManager, Depends(get_jwt_manager)]
AuthManagerDep = Annotated[AuthManager, Depends(get_auth_manager)]
RBACManagerDep = Annotated[RBACManager, Depends(get_rbac_manager)]
SessionManagerDep = Annotated[SessionManager, Depends(get_session_manager)]
OAuth2ManagerDep = Annotated[OAuth2Manager, Depends(get_oauth2_manager)]
MFAManagerDep = Annotated[MFAManager, Depends(get_mfa_manager)]
SecurityPolicyManagerDep = Annotated[SecurityPolicyManager, Depends(get_security_policy_manager)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
RedisClientDep = Annotated[RedisClient, Depends(get_redis_client)]


# =====================================================
# 认证中间件依赖
# =====================================================

async def verify_token_dependency(
    jwt_manager: JWTManagerDep,
    token: str
) -> dict:
    """
    令牌验证依赖函数
    
    用于需要认证的路由中验证JWT令牌的有效性
    """
    validation_result = await jwt_manager.verify_token(token, "access")
    
    if not validation_result.is_valid:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=validation_result.error_message,
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return validation_result.payload.dict()


async def require_permission(
    required_permission: str,
    rbac_manager: RBACManagerDep,
    current_user: dict = Depends(verify_token_dependency)
) -> dict:
    """
    权限验证依赖函数
    
    用于需要特定权限的路由中验证用户权限
    """
    from .models.auth_models import TokenPayload
    token_payload = TokenPayload(**current_user)
    
    permission_result = await rbac_manager.check_permission(
        token_payload,
        required_permission
    )
    
    if not permission_result.granted:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"需要权限: {required_permission}"
        )
    
    return current_user


# =====================================================
# 权限装饰器工厂
# =====================================================

def require_permissions(*permissions: str):
    """
    权限装饰器工厂
    
    创建一个依赖函数，要求用户拥有指定的多个权限
    
    Args:
        *permissions: 所需的权限列表
        
    Returns:
        依赖函数，用于FastAPI路由的Depends参数
    """
    async def permission_checker(
        rbac_manager: RBACManagerDep,
        current_user: dict = Depends(verify_token_dependency)
    ) -> dict:
        from .models.auth_models import TokenPayload
        token_payload = TokenPayload(**current_user)
        
        # 检查所有权限
        for permission in permissions:
            permission_result = await rbac_manager.check_permission(
                token_payload,
                permission
            )
            
            if not permission_result.granted:
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"需要权限: {permission}"
                )
        
        return current_user
    
    return permission_checker


def require_roles(*roles: str):
    """
    角色装饰器工厂
    
    创建一个依赖函数，要求用户拥有指定角色之一
    
    Args:
        *roles: 所需的角色列表
        
    Returns:
        依赖函数，用于FastAPI路由的Depends参数
    """
    async def role_checker(
        current_user: dict = Depends(verify_token_dependency)
    ) -> dict:
        user_role = current_user.get("role")
        
        if user_role not in roles:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要角色: {', '.join(roles)}"
            )
        
        return current_user
    
    return role_checker


# =====================================================
# 高级依赖组合
# =====================================================

def admin_required():
    """管理员权限依赖"""
    return require_permissions("system:admin", "tenant:manage")


def tenant_admin_required():
    """租户管理员权限依赖"""
    return require_permissions("tenant:manage")


def user_management_required():
    """用户管理权限依赖"""
    return require_permissions("user:manage")


def monitoring_required():
    """监控权限依赖"""
    return require_permissions("system:monitor")


# =====================================================
# 日志和调试依赖
# =====================================================

async def get_request_context(
    settings: SettingsDep,
    current_user: dict = None
) -> dict:
    """
    获取请求上下文信息
    
    用于日志记录和调试
    """
    context = {
        "environment": settings.environment,
        "debug": settings.debug,
        "timestamp": None,  # 会在中间件中设置
        "request_id": None,  # 会在中间件中设置
    }
    
    if current_user:
        context.update({
            "user_id": current_user.get("sub"),
            "tenant_id": current_user.get("tenant_id"),
            "user_role": current_user.get("role")
        })
    
    return context


# =====================================================
# 资源依赖注入
# =====================================================

class DependencyManager:
    """
    依赖管理器
    
    集中管理所有依赖注入相关的配置和状态
    """
    
    def __init__(self):
        self._managers = {}
    
    def register_manager(self, name: str, manager_instance):
        """注册管理器实例"""
        self._managers[name] = manager_instance
        logger.info(f"依赖管理器已注册: {name}")
    
    def get_manager(self, name: str):
        """获取管理器实例"""
        return self._managers.get(name)
    
    def clear_cache(self):
        """清除依赖缓存"""
        get_jwt_manager.cache_clear()
        get_rbac_manager.cache_clear()
        get_session_manager.cache_clear()
        get_auth_manager.cache_clear()
        logger.info("依赖注入缓存已清除")
    
    def health_check(self) -> dict:
        """依赖健康检查"""
        status = {
            "registered_managers": len(self._managers),
            "cache_info": {
                "jwt_manager": get_jwt_manager.cache_info(),
                "rbac_manager": get_rbac_manager.cache_info(),
                "session_manager": get_session_manager.cache_info(),
                "auth_manager": get_auth_manager.cache_info(),
            }
        }
        return status


# 全局依赖管理器实例
dependency_manager = DependencyManager()