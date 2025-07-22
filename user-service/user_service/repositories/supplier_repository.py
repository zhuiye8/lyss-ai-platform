# -*- coding: utf-8 -*-
"""
供应商凭证数据访问层

提供供应商凭证相关的数据库操作方法
"""

import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy import and_, or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from ..models.database.supplier_credential import SupplierCredential


class SupplierRepository(BaseRepository):
    """供应商凭证Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, SupplierCredential)
    
    async def get_by_provider_and_display_name(
        self,
        tenant_id: uuid.UUID,
        provider_name: str,
        display_name: str
    ) -> Optional[SupplierCredential]:
        """
        根据供应商名称和显示名称获取凭证
        
        Args:
            tenant_id: 租户ID
            provider_name: 供应商名称
            display_name: 显示名称
            
        Returns:
            凭证实例或None
        """
        query = select(SupplierCredential).where(
            and_(
                SupplierCredential.tenant_id == tenant_id,
                SupplierCredential.provider_name == provider_name,
                SupplierCredential.display_name == display_name
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_id_in_tenant(
        self,
        credential_id: uuid.UUID,
        tenant_id: uuid.UUID
    ) -> Optional[SupplierCredential]:
        """
        在指定租户内根据ID获取凭证
        
        Args:
            credential_id: 凭证ID
            tenant_id: 租户ID
            
        Returns:
            凭证实例或None
        """
        query = select(SupplierCredential).where(
            and_(
                SupplierCredential.id == credential_id,
                SupplierCredential.tenant_id == tenant_id
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_credentials_by_tenant(
        self,
        tenant_id: uuid.UUID,
        provider_name: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[SupplierCredential]:
        """
        获取租户的所有凭证
        
        Args:
            tenant_id: 租户ID
            provider_name: 供应商名称过滤
            is_active: 激活状态过滤
            
        Returns:
            凭证列表
        """
        conditions = [SupplierCredential.tenant_id == tenant_id]
        
        if provider_name:
            conditions.append(SupplierCredential.provider_name == provider_name)
        
        if is_active is not None:
            conditions.append(SupplierCredential.is_active == is_active)
        
        query = select(SupplierCredential).where(and_(*conditions))
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_credentials_by_filters(
        self,
        filters: Optional[Dict[str, Any]] = None,
        order_by: str = "created_at",
        order_desc: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[SupplierCredential]:
        """
        根据过滤条件获取凭证列表
        
        Args:
            filters: 过滤条件
            order_by: 排序字段
            order_desc: 是否降序
            limit: 限制数量
            offset: 偏移量
            
        Returns:
            凭证列表
        """
        conditions = []
        
        # 应用过滤条件
        if filters:
            for field_name, value in filters.items():
                if hasattr(SupplierCredential, field_name):
                    field = getattr(SupplierCredential, field_name)
                    conditions.append(field == value)
        
        query = select(SupplierCredential)
        
        # 添加WHERE条件
        if conditions:
            query = query.where(and_(*conditions))
        
        # 排序
        if hasattr(SupplierCredential, order_by):
            order_field = getattr(SupplierCredential, order_by)
            if order_desc:
                order_field = order_field.desc()
            query = query.order_by(order_field)
        
        # 分页
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def count_credentials_by_filters(
        self,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        根据过滤条件统计凭证数量
        
        Args:
            filters: 过滤条件
            
        Returns:
            凭证数量
        """
        conditions = []
        
        # 应用过滤条件
        if filters:
            for field_name, value in filters.items():
                if hasattr(SupplierCredential, field_name):
                    field = getattr(SupplierCredential, field_name)
                    conditions.append(field == value)
        
        query = select(func.count(SupplierCredential.id))
        
        # 添加WHERE条件
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    async def get_active_credentials_by_provider(
        self,
        tenant_id: uuid.UUID,
        provider_name: str
    ) -> List[SupplierCredential]:
        """
        获取指定供应商的活跃凭证
        
        Args:
            tenant_id: 租户ID
            provider_name: 供应商名称
            
        Returns:
            活跃凭证列表
        """
        query = select(SupplierCredential).where(
            and_(
                SupplierCredential.tenant_id == tenant_id,
                SupplierCredential.provider_name == provider_name,
                SupplierCredential.is_active == True
            )
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def update_credential_status(
        self,
        credential_id: uuid.UUID,
        is_active: bool
    ) -> bool:
        """
        更新凭证激活状态
        
        Args:
            credential_id: 凭证ID
            is_active: 是否激活
            
        Returns:
            是否更新成功
        """
        updates = {"is_active": is_active}
        result = await self.update(credential_id, updates)
        return result is not None
    
    async def get_credential_stats(self, credential_id: uuid.UUID) -> Dict[str, Any]:
        """
        获取凭证统计信息
        
        Args:
            credential_id: 凭证ID
            
        Returns:
            统计信息字典
        """
        # 这里可以统计凭证的使用次数、错误次数等
        # 暂时返回基础统计信息
        return {
            "last_used_at": None,
            "usage_count": 0,
            "error_count": 0,
            "last_error_at": None,
            "last_error_message": None
        }
    
    async def provider_exists_in_tenant(
        self,
        tenant_id: uuid.UUID,
        provider_name: str,
        display_name: str,
        exclude_credential_id: Optional[uuid.UUID] = None
    ) -> bool:
        """
        检查供应商配置是否在租户内已存在
        
        Args:
            tenant_id: 租户ID
            provider_name: 供应商名称
            display_name: 显示名称
            exclude_credential_id: 排除的凭证ID（用于更新时检查）
            
        Returns:
            是否存在
        """
        conditions = [
            SupplierCredential.tenant_id == tenant_id,
            SupplierCredential.provider_name == provider_name,
            SupplierCredential.display_name == display_name
        ]
        
        if exclude_credential_id:
            conditions.append(SupplierCredential.id != exclude_credential_id)
        
        query = select(func.count(SupplierCredential.id)).where(and_(*conditions))
        result = await self.session.execute(query)
        count = result.scalar() or 0
        return count > 0
    
    async def get_all_providers_in_tenant(self, tenant_id: uuid.UUID) -> List[str]:
        """
        获取租户内所有使用的供应商名称
        
        Args:
            tenant_id: 租户ID
            
        Returns:
            供应商名称列表
        """
        query = select(SupplierCredential.provider_name).where(
            and_(
                SupplierCredential.tenant_id == tenant_id,
                SupplierCredential.is_active == True
            )
        ).distinct()
        
        result = await self.session.execute(query)
        return [row[0] for row in result.fetchall()]