# -*- coding: utf-8 -*-
"""
SQLAlchemy基础模型

定义所有数据库模型的基础类和通用字段
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List
from sqlalchemy import DateTime, String, Boolean, text, UUID
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from sqlalchemy.dialects.postgresql import JSONB


class Base(DeclarativeBase):
    """SQLAlchemy基础模型类"""
    
    type_annotation_map = {
        dict[str, Any]: JSONB,
        Dict[str, Any]: JSONB,
        list[str]: JSONB,
        List[str]: JSONB,
        list: JSONB,
        List: JSONB,
    }


class BaseModel(Base):
    """通用基础模型，包含标准字段"""
    
    __abstract__ = True
    
    # 主键ID
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="主键ID"
    )
    
    # 时间戳字段
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("NOW()"),
        nullable=False,
        comment="创建时间"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("NOW()"),
        onupdate=datetime.utcnow,
        nullable=False,
        comment="更新时间"
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            column.key: getattr(self, column.key)
            for column in self.__table__.columns
        }
    
    def __repr__(self) -> str:
        """字符串表示"""
        return f"<{self.__class__.__name__}(id={self.id})>"


class TenantAwareModel(BaseModel):
    """多租户感知模型，包含租户隔离字段"""
    
    __abstract__ = True
    
    # 租户ID（必需字段，用于数据隔离）
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="租户ID"
    )