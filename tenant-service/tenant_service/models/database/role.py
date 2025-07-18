# -*- coding: utf-8 -*-
"""
角色数据模型

定义系统角色和权限的数据库表结构
"""

from typing import Any, Dict, List
from sqlalchemy import String, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class Role(BaseModel):
    """角色表"""
    
    __tablename__ = "roles"
    
    # 角色名称（唯一）
    name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        comment="角色名称"
    )
    
    # 显示名称
    display_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="显示名称"
    )
    
    # 角色描述
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="角色描述"
    )
    
    # 权限列表（JSON格式）
    permissions: Mapped[List[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
        comment="权限列表"
    )
    
    # 是否为系统角色
    is_system_role: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否为系统角色"
    )
    
    # 定义索引
    __table_args__ = (
        Index("idx_roles_name", "name"),
        Index("idx_roles_system", "is_system_role"),
    )
    
    # 用户关系（使用字符串引用避免循环导入）
    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="role",
        lazy="select"
    )
    
    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name={self.name}, display_name={self.display_name})>"