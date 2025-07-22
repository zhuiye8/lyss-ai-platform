# -*- coding: utf-8 -*-
"""
供应商凭证数据模型

定义供应商API密钥的加密存储表结构
"""

from typing import Any, Dict
from sqlalchemy import String, Boolean, LargeBinary, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import TenantAwareModel


class SupplierCredential(TenantAwareModel):
    """供应商凭证表"""
    
    __tablename__ = "supplier_credentials"
    
    # 供应商名称
    provider_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="供应商名称"
    )
    
    # 显示名称
    display_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="显示名称"
    )
    
    # 加密的API密钥
    encrypted_api_key: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
        comment="加密的API密钥"
    )
    
    # 基础URL
    base_url: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="基础URL"
    )
    
    # 模型配置（JSON格式）
    model_configs: Mapped[Dict[str, Any]] = mapped_column(
        default=dict,
        nullable=False,
        comment="模型配置"
    )
    
    # 是否激活
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否激活"
    )
    
    # 定义约束和索引
    __table_args__ = (
        # 租户内供应商配置唯一约束
        UniqueConstraint(
            "tenant_id", "provider_name", "display_name",
            name="uk_supplier_tenant_provider_display"
        ),
        
        # 索引
        Index("idx_supplier_credentials_tenant_id", "tenant_id"),
        Index("idx_supplier_credentials_provider", "provider_name"),
        Index("idx_supplier_credentials_active", "is_active"),
    )
    
    # 关系定义
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="supplier_credentials"
    )
    
    def __repr__(self) -> str:
        return (
            f"<SupplierCredential(id={self.id}, provider={self.provider_name}, "
            f"display_name={self.display_name}, tenant_id={self.tenant_id})>"
        )