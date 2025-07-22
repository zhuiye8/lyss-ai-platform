# -*- coding: utf-8 -*-
"""
安全相关功能

包含密码验证、权限检查等安全功能
"""

import re
from typing import List
from passlib.context import CryptContext
from fastapi import HTTPException, status

from ..config import get_settings

settings = get_settings()

# 密码加密上下文
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)


class PasswordManager:
    """密码管理器"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        哈希密码
        
        Args:
            password: 明文密码
            
        Returns:
            哈希后的密码
        """
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        验证密码
        
        Args:
            plain_password: 明文密码
            hashed_password: 哈希密码
            
        Returns:
            验证结果
        """
        try:
            if not plain_password or not hashed_password:
                return False
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return False
    
    @staticmethod
    def validate_password_strength(password: str) -> None:
        """
        验证密码强度
        
        Args:
            password: 待验证的密码
            
        Raises:
            HTTPException: 密码不符合要求时抛出
        """
        errors = []
        
        # 检查密码长度
        if len(password) < settings.min_password_length:
            errors.append(f"密码长度不能少于{settings.min_password_length}个字符")
        
        # 检查是否包含数字
        if settings.require_numbers and not re.search(r'\d', password):
            errors.append("密码必须包含至少一个数字")
        
        # 检查是否包含大写字母
        if settings.require_uppercase and not re.search(r'[A-Z]', password):
            errors.append("密码必须包含至少一个大写字母")
        
        # 检查是否包含特殊字符
        if settings.require_special_chars and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("密码必须包含至少一个特殊字符")
        
        if errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "1003",
                    "message": "密码强度不符合要求",
                    "details": {"errors": errors}
                }
            )


class RolePermissionManager:
    """角色权限管理器"""
    
    # 系统角色定义
    SUPER_ADMIN = "super_admin"
    TENANT_ADMIN = "tenant_admin"
    END_USER = "end_user"
    
    # 权限定义
    PERMISSIONS = {
        # 租户管理权限
        "tenant:create": "创建租户",
        "tenant:delete": "删除租户",
        "tenant:manage": "管理租户",
        
        # 用户管理权限
        "user:create": "创建用户",
        "user:manage": "管理用户",
        "user:manage_all": "管理所有用户",
        
        # 供应商管理权限
        "supplier:manage": "管理供应商凭证",
        
        # 工具配置权限
        "tool:config": "配置工具",
        
        # 记忆管理权限
        "memory:manage": "管理记忆",
        "memory:view": "查看记忆",
        
        # 偏好管理权限
        "preference:manage": "管理偏好",
        
        # 对话权限
        "chat:access": "访问对话",
        
        # 系统配置权限
        "system:config": "系统配置"
    }
    
    # 角色权限映射
    ROLE_PERMISSIONS = {
        SUPER_ADMIN: [
            "tenant:create", "tenant:delete", "tenant:manage",
            "user:manage_all", "system:config"
        ],
        TENANT_ADMIN: [
            "user:create", "user:manage", "supplier:manage",
            "tool:config", "memory:manage", "preference:manage"
        ],
        END_USER: [
            "chat:access", "memory:view", "preference:manage"
        ]
    }
    
    @classmethod
    def get_role_permissions(cls, role_name: str) -> List[str]:
        """
        获取角色的权限列表
        
        Args:
            role_name: 角色名称
            
        Returns:
            权限列表
        """
        return cls.ROLE_PERMISSIONS.get(role_name, [])
    
    @classmethod
    def has_permission(cls, role_name: str, permission: str) -> bool:
        """
        检查角色是否有指定权限
        
        Args:
            role_name: 角色名称
            permission: 权限名称
            
        Returns:
            是否有权限
        """
        role_permissions = cls.get_role_permissions(role_name)
        return permission in role_permissions
    
    @classmethod
    def require_permission(cls, role_name: str, permission: str) -> None:
        """
        要求指定权限，没有权限时抛出异常
        
        Args:
            role_name: 角色名称
            permission: 权限名称
            
        Raises:
            HTTPException: 权限不足时抛出
        """
        if not cls.has_permission(role_name, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "2004",
                    "message": "权限不足，无法执行此操作",
                    "details": {
                        "required_permission": permission,
                        "user_role": role_name
                    }
                }
            )


def require_roles(allowed_roles: List[str]):
    """
    权限装饰器：要求指定角色
    
    Args:
        allowed_roles: 允许的角色列表
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 这里应该从请求上下文中获取用户角色
            # 在实际使用中，会从JWT token中解析用户角色
            user_role = "end_user"  # 示例，实际应该从上下文获取
            
            if user_role not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error_code": "2004",
                        "message": "权限不足，无法执行此操作",
                        "details": {
                            "allowed_roles": allowed_roles,
                            "user_role": user_role
                        }
                    }
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator