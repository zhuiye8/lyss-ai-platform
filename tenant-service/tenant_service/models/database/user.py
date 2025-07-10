# -*- coding: utf-8 -*-
"""
用户数据模型

定义用户相关的数据库表结构
"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, Index, UniqueConstraint, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import TenantAwareModel


class User(TenantAwareModel):
    """用户表"""
    
    __tablename__ = "users"
    
    # 邮箱地址
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="邮箱地址"
    )
    
    # 用户名（可选）
    username: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="用户名"
    )
    
    # 哈希密码
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="哈希密码"
    )
    
    # 姓名
    first_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="名字"
    )
    
    last_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="姓氏"
    )
    
    # 角色ID
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=False,
        comment="角色ID"
    )
    
    # 用户状态
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否激活"
    )
    
    # 邮箱验证状态
    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="邮箱是否验证"
    )
    
    # 最后登录时间
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="最后登录时间"
    )
    
    # 登录尝试次数
    login_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="登录尝试次数"
    )
    
    # 锁定截止时间
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="锁定截止时间"
    )
    
    # 定义约束和索引
    __table_args__ = (
        # 多租户唯一约束
        UniqueConstraint("tenant_id", "email", name="uk_users_tenant_email"),
        UniqueConstraint("tenant_id", "username", name="uk_users_tenant_username"),
        
        # 索引
        Index("idx_users_tenant_id", "tenant_id"),
        Index("idx_users_email", "email"),
        Index("idx_users_role_id", "role_id"),
        Index("idx_users_active", "is_active"),
    )
    
    # 租户关系（使用字符串引用避免循环导入）
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="users",
        lazy="select"
    )
    
    # 角色关系
    role: Mapped["Role"] = relationship(
        "Role",
        back_populates="users",
        lazy="select"
    )
    
    @property
    def full_name(self) -> str:
        """获取全名"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.username or self.email
    
    @property
    def is_locked(self) -> bool:
        """检查用户是否被锁定"""
        if not self.locked_until:
            return False
        return datetime.utcnow() < self.locked_until
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, tenant_id={self.tenant_id})>"