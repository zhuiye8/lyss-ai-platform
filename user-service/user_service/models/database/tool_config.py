# -*- coding: utf-8 -*-
"""
工具配置数据模型

定义租户级别的EINO工具开关配置表结构
"""

from typing import Any, Dict
from sqlalchemy import String, Boolean, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import TenantAwareModel


class TenantToolConfig(TenantAwareModel):
    """租户工具配置表"""
    
    __tablename__ = "tenant_tool_configs"
    
    # 工作流名称
    workflow_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="工作流名称"
    )
    
    # 工具节点名称
    tool_node_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="工具节点名称"
    )
    
    # 是否启用
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否启用"
    )
    
    # 配置参数（JSON格式）
    config_params: Mapped[Dict[str, Any]] = mapped_column(
        default=dict,
        nullable=False,
        comment="配置参数"
    )
    
    # 定义约束和索引
    __table_args__ = (
        # 租户内工具配置唯一约束
        UniqueConstraint(
            "tenant_id", "workflow_name", "tool_node_name",
            name="uk_tool_config_tenant_workflow_tool"
        ),
        
        # 索引
        Index("idx_tool_configs_tenant_id", "tenant_id"),
        Index("idx_tool_configs_workflow", "workflow_name"),
    )
    
    # 关系定义
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="tool_configs"
    )
    
    def __repr__(self) -> str:
        return (
            f"<TenantToolConfig(id={self.id}, workflow={self.workflow_name}, "
            f"tool={self.tool_node_name}, tenant_id={self.tenant_id})>"
        )