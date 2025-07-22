# -*- coding: utf-8 -*-
"""
租户数据模型

定义租户相关的数据库表结构
"""

from typing import Any, Dict
from sqlalchemy import String, Integer, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class Tenant(BaseModel):
    """租户表"""
    
    __tablename__ = "tenants"
    
    # 租户名称
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="租户名称"
    )
    
    # URL友好的标识符
    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        comment="租户标识符"
    )
    
    # 租户状态
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        nullable=False,
        comment="租户状态"
    )
    
    # 订阅计划
    subscription_plan: Mapped[str] = mapped_column(
        String(50),
        default="basic",
        nullable=False,
        comment="订阅计划"
    )
    
    # 最大用户数
    max_users: Mapped[int] = mapped_column(
        Integer,
        default=10,
        nullable=False,
        comment="最大用户数"
    )
    
    # 租户设置（JSON格式）
    settings: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="租户设置"
    )
    
    # 定义约束
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'suspended', 'inactive')",
            name="ck_tenants_status_valid"
        ),
        Index("idx_tenants_slug", "slug"),
        Index("idx_tenants_status", "status"),
    )
    
    # 用户关系（使用字符串引用避免循环导入）
    users: Mapped[list["User"]] = relationship(
        "User", 
        back_populates="tenant",
        foreign_keys="[User.tenant_id]",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    # 供应商凭证关系
    supplier_credentials: Mapped[list["SupplierCredential"]] = relationship(
        "SupplierCredential",
        back_populates="tenant",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    # 工具配置关系
    tool_configs: Mapped[list["TenantToolConfig"]] = relationship(
        "TenantToolConfig",
        back_populates="tenant",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name={self.name}, slug={self.slug})>"