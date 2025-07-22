# -*- coding: utf-8 -*-
"""
SQLAlchemy数据库模型统一导入

导入所有数据库模型以确保正确的关系映射
"""

from .base import Base, BaseModel, TenantAwareModel
from .tenant import Tenant
from .role import Role
from .user import User
from .supplier_credential import SupplierCredential
from .tool_config import TenantToolConfig
from .user_preference import UserPreference

# 导出所有模型
__all__ = [
    "Base",
    "BaseModel", 
    "TenantAwareModel",
    "Tenant",
    "Role",
    "User",
    "SupplierCredential",
    "TenantToolConfig",
    "UserPreference",
]