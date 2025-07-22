# -*- coding: utf-8 -*-
"""
用户偏好数据模型

定义用户个性化设置的数据库表结构
"""

import uuid
from typing import Any, Dict
from sqlalchemy import String, Boolean, ForeignKey, Index, UniqueConstraint, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import TenantAwareModel


class UserPreference(TenantAwareModel):
    """用户偏好设置表"""
    
    __tablename__ = "user_preferences"
    
    # 用户ID
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="用户ID"
    )
    
    # 记忆功能开关
    active_memory_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="记忆功能是否启用"
    )
    
    # 首选语言
    preferred_language: Mapped[str] = mapped_column(
        String(10),
        default="zh",
        nullable=False,
        comment="首选语言"
    )
    
    # 主题设置
    theme: Mapped[str] = mapped_column(
        String(20),
        default="light",
        nullable=False,
        comment="主题设置"
    )
    
    # 通知设置（JSON格式）
    notification_settings: Mapped[Dict[str, Any]] = mapped_column(
        default=dict,
        nullable=False,
        comment="通知设置"
    )
    
    # AI模型偏好（JSON格式）
    ai_model_preferences: Mapped[Dict[str, Any]] = mapped_column(
        default=dict,
        nullable=False,
        comment="AI模型偏好"
    )
    
    # 定义约束和索引
    __table_args__ = (
        # 用户偏好唯一约束
        UniqueConstraint(
            "user_id", "tenant_id",
            name="uk_user_preferences_user_tenant"
        ),
        
        # 索引
        Index("idx_user_preferences_user_id", "user_id"),
        Index("idx_user_preferences_tenant_id", "tenant_id"),
    )
    
    # 关系定义
    user: Mapped["User"] = relationship(
        "User",
        back_populates="preferences"
    )
    
    def __repr__(self) -> str:
        return (
            f"<UserPreference(id={self.id}, user_id={self.user_id}, "
            f"tenant_id={self.tenant_id}, memory_enabled={self.active_memory_enabled})>"
        )