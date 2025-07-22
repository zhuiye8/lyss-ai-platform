"""
RBAC权限管理器

实现基于角色的访问控制系统，包括：
- 角色管理（创建、更新、删除角色）
- 权限管理（权限定义、分配、验证）
- 用户角色关联（分配、撤销、查询）
- 权限缓存优化（Redis缓存权限信息）

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import json
from typing import Dict, List, Set, Optional, Union
from dataclasses import dataclass
from enum import Enum

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.orm import selectinload

from ..config import AuthServiceSettings
from ..models.auth_models import TokenPayload


class PermissionAction(str, Enum):
    """权限操作枚举"""
    CREATE = "create"
    READ = "read" 
    UPDATE = "update"
    DELETE = "delete"
    MANAGE = "manage"
    ACCESS = "access"
    VIEW = "view"
    EDIT = "edit"
    CONFIG = "config"


class PermissionResource(str, Enum):
    """权限资源枚举"""
    TENANT = "tenant"
    USER = "user"
    ROLE = "role"
    PROVIDER = "provider"
    CHANNEL = "channel"
    CHAT = "chat"
    MEMORY = "memory"
    TOOL = "tool"
    SYSTEM = "system"
    PROFILE = "profile"
    PREFERENCE = "preference"


@dataclass
class Permission:
    """权限定义"""
    resource: str
    action: str
    scope: Optional[str] = None  # tenant, global
    
    def __str__(self) -> str:
        """权限字符串表示：resource:action[:scope]"""
        if self.scope:
            return f"{self.resource}:{self.action}:{self.scope}"
        return f"{self.resource}:{self.action}"
    
    @classmethod
    def from_string(cls, permission_str: str) -> 'Permission':
        """从字符串解析权限"""
        parts = permission_str.split(':')
        if len(parts) == 2:
            return cls(resource=parts[0], action=parts[1])
        elif len(parts) == 3:
            return cls(resource=parts[0], action=parts[1], scope=parts[2])
        else:
            raise ValueError(f"无效的权限格式: {permission_str}")


@dataclass
class Role:
    """角色定义"""
    id: str
    name: str
    display_name: str
    description: Optional[str] = None
    permissions: List[str] = None
    is_system_role: bool = False
    
    def __post_init__(self):
        if self.permissions is None:
            self.permissions = []


@dataclass
class PermissionCheck:
    """权限检查结果"""
    granted: bool
    reason: Optional[str] = None
    required_permission: Optional[str] = None
    user_permissions: Optional[List[str]] = None


class RBACManager:
    """
    RBAC权限管理器
    
    功能特性：
    1. 角色管理 - 创建、更新、删除角色
    2. 权限验证 - 检查用户是否拥有特定权限
    3. 权限缓存 - Redis缓存用户权限，提高验证性能
    4. 层级权限 - 支持权限继承和层级控制
    5. 租户隔离 - 支持多租户权限隔离
    """
    
    def __init__(self, settings: AuthServiceSettings, redis_client: redis.Redis):
        self.settings = settings
        self.redis = redis_client
        
        # Redis缓存键前缀
        self.USER_PERMISSIONS_PREFIX = "auth:permissions:user:"
        self.ROLE_PERMISSIONS_PREFIX = "auth:permissions:role:"
        self.CACHE_TTL = 3600  # 缓存1小时
        
        # 预定义权限
        self._init_predefined_permissions()
    
    def _init_predefined_permissions(self):
        """初始化预定义权限"""
        self.PREDEFINED_PERMISSIONS = {
            # 系统级权限
            "system:config": "系统配置管理",
            "system:monitor": "系统监控查看",
            
            # 租户管理权限
            "tenant:create": "创建租户",
            "tenant:delete": "删除租户", 
            "tenant:manage": "管理租户",
            "tenant:view": "查看租户信息",
            
            # 用户管理权限
            "user:create": "创建用户",
            "user:manage": "管理用户",
            "user:manage_all": "管理所有用户",
            "user:view": "查看用户信息",
            "user:delete": "删除用户",
            
            # 角色权限管理
            "role:create": "创建角色",
            "role:manage": "管理角色",
            "role:assign": "分配角色",
            "role:view": "查看角色",
            
            # Provider管理权限
            "provider:manage": "管理供应商配置",
            "provider:view": "查看供应商信息",
            "provider:create": "创建供应商配置",
            "provider:delete": "删除供应商配置",
            
            # Channel管理权限
            "channel:manage": "管理Channel配置",
            "channel:view": "查看Channel信息",
            "channel:create": "创建Channel",
            "channel:delete": "删除Channel",
            
            # 对话功能权限
            "chat:access": "访问AI对话功能",
            "chat:manage": "管理对话历史",
            "chat:delete": "删除对话记录",
            
            # 记忆管理权限
            "memory:view": "查看记忆数据",
            "memory:manage": "管理记忆数据",
            "memory:delete": "删除记忆数据",
            
            # 工具配置权限
            "tool:config": "配置工具开关",
            "tool:manage": "管理工具设置",
            
            # 个人设置权限
            "profile:edit": "编辑个人资料",
            "preference:manage": "管理个人偏好设置"
        }
    
    async def check_permission(
        self, 
        user_token: TokenPayload, 
        required_permission: str,
        resource_owner_id: Optional[str] = None
    ) -> PermissionCheck:
        """
        检查用户权限
        
        Args:
            user_token: 用户令牌信息
            required_permission: 所需权限，格式：resource:action
            resource_owner_id: 资源所有者ID（用于资源级权限控制）
            
        Returns:
            PermissionCheck: 权限检查结果
        """
        try:
            # 获取用户权限列表
            user_permissions = await self._get_user_permissions(user_token.sub, user_token.tenant_id)
            
            # 检查是否拥有所需权限
            if self._has_permission(user_permissions, required_permission):
                return PermissionCheck(
                    granted=True,
                    user_permissions=user_permissions
                )
            
            # 检查是否为资源所有者（用户可以管理自己的资源）
            if resource_owner_id and user_token.sub == resource_owner_id:
                # 检查是否拥有对自己资源的基本权限
                if self._is_self_resource_permission(required_permission):
                    return PermissionCheck(
                        granted=True,
                        reason="资源所有者权限",
                        user_permissions=user_permissions
                    )
            
            return PermissionCheck(
                granted=False,
                reason="权限不足",
                required_permission=required_permission,
                user_permissions=user_permissions
            )
            
        except Exception as e:
            return PermissionCheck(
                granted=False,
                reason=f"权限检查失败: {str(e)}",
                required_permission=required_permission
            )
    
    async def check_multiple_permissions(
        self,
        user_token: TokenPayload,
        required_permissions: List[str],
        operator: str = "AND"  # "AND" 或 "OR"
    ) -> PermissionCheck:
        """
        检查用户是否拥有多个权限
        
        Args:
            user_token: 用户令牌信息
            required_permissions: 所需权限列表
            operator: 逻辑操作符，AND(所有权限) 或 OR(任一权限)
            
        Returns:
            PermissionCheck: 权限检查结果
        """
        user_permissions = await self._get_user_permissions(user_token.sub, user_token.tenant_id)
        
        granted_permissions = []
        missing_permissions = []
        
        for permission in required_permissions:
            if self._has_permission(user_permissions, permission):
                granted_permissions.append(permission)
            else:
                missing_permissions.append(permission)
        
        if operator.upper() == "AND":
            # 需要拥有所有权限
            granted = len(missing_permissions) == 0
            reason = None if granted else f"缺少权限: {', '.join(missing_permissions)}"
        else:
            # 只需拥有任一权限
            granted = len(granted_permissions) > 0
            reason = None if granted else f"缺少任一权限: {', '.join(required_permissions)}"
        
        return PermissionCheck(
            granted=granted,
            reason=reason,
            required_permission=", ".join(required_permissions),
            user_permissions=user_permissions
        )
    
    async def _get_user_permissions(self, user_id: str, tenant_id: str) -> List[str]:
        """获取用户权限列表（带缓存）"""
        cache_key = f"{self.USER_PERMISSIONS_PREFIX}{user_id}:{tenant_id}"
        
        # 尝试从Redis缓存获取
        cached_permissions = await self.redis.get(cache_key)
        if cached_permissions:
            return json.loads(cached_permissions.decode())
        
        # 从数据库查询用户权限（需要后续实现数据库查询）
        # 这里先返回模拟数据，实际需要查询数据库
        permissions = await self._query_user_permissions_from_db(user_id, tenant_id)
        
        # 缓存到Redis
        await self.redis.setex(
            cache_key,
            self.CACHE_TTL,
            json.dumps(permissions)
        )
        
        return permissions
    
    async def _query_user_permissions_from_db(self, user_id: str, tenant_id: str) -> List[str]:
        """从数据库查询用户权限（占位方法，需要在有数据库连接后实现）"""
        # 临时返回基于用户角色的模拟权限
        # 实际实现需要查询 auth_users -> auth_roles -> permissions
        
        # 这里返回一些默认权限用于测试
        return [
            "chat:access",
            "memory:view", 
            "preference:manage",
            "profile:edit"
        ]
    
    def _has_permission(self, user_permissions: List[str], required_permission: str) -> bool:
        """检查权限列表中是否包含所需权限"""
        # 直接匹配
        if required_permission in user_permissions:
            return True
        
        # 检查通配符权限
        permission_parts = required_permission.split(':')
        if len(permission_parts) >= 2:
            resource = permission_parts[0]
            
            # 检查资源级管理权限（如 user:manage 包含 user:create, user:update 等）
            if f"{resource}:manage" in user_permissions:
                return True
            
            # 检查全局管理权限
            if "system:config" in user_permissions:
                return True
        
        return False
    
    def _is_self_resource_permission(self, permission: str) -> bool:
        """检查是否为自身资源权限"""
        self_permissions = [
            "profile:edit",
            "preference:manage",
            "user:view"  # 用户可以查看自己的信息
        ]
        return permission in self_permissions
    
    async def invalidate_user_permissions_cache(self, user_id: str, tenant_id: str):
        """清除用户权限缓存"""
        cache_key = f"{self.USER_PERMISSIONS_PREFIX}{user_id}:{tenant_id}"
        await self.redis.delete(cache_key)
    
    async def invalidate_role_permissions_cache(self, role_id: str):
        """清除角色权限缓存"""
        cache_key = f"{self.ROLE_PERMISSIONS_PREFIX}{role_id}"
        await self.redis.delete(cache_key)
    
    async def get_role_permissions(self, role_name: str) -> List[str]:
        """获取角色权限列表"""
        # 预定义角色权限
        role_permissions = {
            "super_admin": [
                "system:config", "system:monitor",
                "tenant:create", "tenant:delete", "tenant:manage",
                "user:manage_all", "role:manage"
            ],
            "tenant_admin": [
                "user:create", "user:manage", "user:view", 
                "role:assign", "role:view",
                "provider:manage", "channel:manage",
                "tool:config", "memory:manage"
            ],
            "end_user": [
                "chat:access", "memory:view", 
                "preference:manage", "profile:edit"
            ]
        }
        
        return role_permissions.get(role_name, [])
    
    def get_all_permissions(self) -> Dict[str, str]:
        """获取所有预定义权限"""
        return self.PREDEFINED_PERMISSIONS.copy()
    
    def validate_permissions(self, permissions: List[str]) -> Dict[str, bool]:
        """验证权限格式是否正确"""
        result = {}
        for permission in permissions:
            try:
                Permission.from_string(permission)
                result[permission] = True
            except ValueError:
                result[permission] = False
        return result


# 权限装饰器
def require_permission(permission: str):
    """
    权限检查装饰器
    
    用于API端点的权限验证
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 这里需要从请求中获取用户令牌
            # 实际实现需要结合FastAPI的依赖注入
            pass
        return wrapper
    return decorator


def require_role(role: str):
    """
    角色检查装饰器
    
    用于API端点的角色验证
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 角色验证逻辑
            pass
        return wrapper
    return decorator