# -*- coding: utf-8 -*-
"""
基础Repository类

提供通用的数据库操作方法和多租户数据隔离机制
"""

import uuid
from typing import Any, Dict, List, Optional, Type, TypeVar, Union
from sqlalchemy import and_, select, func, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base

from ..models.database.base import Base

T = TypeVar('T', bound=Base)


class BaseRepository:
    """基础Repository类"""
    
    def __init__(self, session: AsyncSession, model: Type[T]):
        """
        初始化Repository
        
        Args:
            session: 数据库会话
            model: SQLAlchemy模型类
        """
        self.session = session
        self.model = model
    
    async def get_by_id(self, id: uuid.UUID, tenant_id: Optional[uuid.UUID] = None) -> Optional[T]:
        """
        根据ID获取单条记录
        
        Args:
            id: 记录ID
            tenant_id: 租户ID（如果是多租户表）
            
        Returns:
            模型实例或None
        """
        conditions = [self.model.id == id]
        
        # 如果模型有tenant_id字段，强制添加租户过滤
        if hasattr(self.model, 'tenant_id') and tenant_id is not None:
            conditions.append(self.model.tenant_id == tenant_id)
        
        query = select(self.model).where(and_(*conditions))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_field(self, field_name: str, value: Any, tenant_id: Optional[uuid.UUID] = None) -> Optional[T]:
        """
        根据字段值获取单条记录
        
        Args:
            field_name: 字段名
            value: 字段值
            tenant_id: 租户ID（如果是多租户表）
            
        Returns:
            模型实例或None
        """
        field = getattr(self.model, field_name)
        conditions = [field == value]
        
        # 多租户过滤
        if hasattr(self.model, 'tenant_id') and tenant_id is not None:
            conditions.append(self.model.tenant_id == tenant_id)
        
        query = select(self.model).where(and_(*conditions))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all(
        self, 
        tenant_id: Optional[uuid.UUID] = None,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[T]:
        """
        获取记录列表
        
        Args:
            tenant_id: 租户ID（如果是多租户表）
            filters: 过滤条件字典
            order_by: 排序字段
            order_desc: 是否降序
            limit: 限制数量
            offset: 偏移量
            
        Returns:
            模型实例列表
        """
        conditions = []
        
        # 多租户过滤
        if hasattr(self.model, 'tenant_id') and tenant_id is not None:
            conditions.append(self.model.tenant_id == tenant_id)
        
        # 应用过滤条件
        if filters:
            for field_name, value in filters.items():
                if hasattr(self.model, field_name):
                    field = getattr(self.model, field_name)
                    conditions.append(field == value)
        
        query = select(self.model)
        
        # 添加WHERE条件
        if conditions:
            query = query.where(and_(*conditions))
        
        # 排序
        if order_by and hasattr(self.model, order_by):
            order_field = getattr(self.model, order_by)
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
    
    async def count(
        self, 
        tenant_id: Optional[uuid.UUID] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        统计记录数量
        
        Args:
            tenant_id: 租户ID（如果是多租户表）
            filters: 过滤条件字典
            
        Returns:
            记录数量
        """
        conditions = []
        
        # 多租户过滤
        if hasattr(self.model, 'tenant_id') and tenant_id is not None:
            conditions.append(self.model.tenant_id == tenant_id)
        
        # 应用过滤条件
        if filters:
            for field_name, value in filters.items():
                if hasattr(self.model, field_name):
                    field = getattr(self.model, field_name)
                    conditions.append(field == value)
        
        query = select(func.count(self.model.id))
        
        # 添加WHERE条件
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    async def create(self, **kwargs) -> T:
        """
        创建新记录
        
        Args:
            **kwargs: 字段值
            
        Returns:
            创建的模型实例
        """
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance
    
    async def update(
        self, 
        id: uuid.UUID, 
        updates: Dict[str, Any],
        tenant_id: Optional[uuid.UUID] = None
    ) -> Optional[T]:
        """
        更新记录
        
        Args:
            id: 记录ID
            updates: 更新字段字典
            tenant_id: 租户ID（如果是多租户表）
            
        Returns:
            更新后的模型实例或None
        """
        conditions = [self.model.id == id]
        
        # 多租户过滤
        if hasattr(self.model, 'tenant_id') and tenant_id is not None:
            conditions.append(self.model.tenant_id == tenant_id)
        
        query = update(self.model).where(and_(*conditions)).values(**updates)
        await self.session.execute(query)
        
        # 返回更新后的实例
        return await self.get_by_id(id, tenant_id)
    
    async def delete(self, id: uuid.UUID, tenant_id: Optional[uuid.UUID] = None) -> bool:
        """
        删除记录
        
        Args:
            id: 记录ID
            tenant_id: 租户ID（如果是多租户表）
            
        Returns:
            是否删除成功
        """
        conditions = [self.model.id == id]
        
        # 多租户过滤
        if hasattr(self.model, 'tenant_id') and tenant_id is not None:
            conditions.append(self.model.tenant_id == tenant_id)
        
        query = delete(self.model).where(and_(*conditions))
        result = await self.session.execute(query)
        return result.rowcount > 0
    
    async def exists(self, id: uuid.UUID, tenant_id: Optional[uuid.UUID] = None) -> bool:
        """
        检查记录是否存在
        
        Args:
            id: 记录ID
            tenant_id: 租户ID（如果是多租户表）
            
        Returns:
            是否存在
        """
        instance = await self.get_by_id(id, tenant_id)
        return instance is not None