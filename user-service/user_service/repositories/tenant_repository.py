# -*- coding: utf-8 -*-
"""
租户数据访问层

提供租户相关的数据库操作方法
"""

import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy import and_, or_, select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from ..models.database.tenant import Tenant


class TenantRepository(BaseRepository):
    """租户Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Tenant)
    
    async def get_by_slug(self, slug: str) -> Optional[Tenant]:
        """
        根据slug获取租户
        
        Args:
            slug: 租户标识符
            
        Returns:
            租户实例或None
        """
        query = select(Tenant).where(Tenant.slug == slug)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def slug_exists(self, slug: str, exclude_tenant_id: Optional[uuid.UUID] = None) -> bool:
        """
        检查slug是否已存在
        
        Args:
            slug: 租户标识符
            exclude_tenant_id: 排除的租户ID（用于更新时检查）
            
        Returns:
            是否存在
        """
        conditions = [Tenant.slug == slug]
        
        if exclude_tenant_id:
            conditions.append(Tenant.id != exclude_tenant_id)
        
        query = select(func.count(Tenant.id)).where(and_(*conditions))
        result = await self.session.execute(query)
        count = result.scalar() or 0
        return count > 0
    
    async def get_tenants_with_stats(
        self,
        filters: Optional[Dict[str, Any]] = None,
        search: Optional[str] = None,
        order_by: str = "created_at",
        order_desc: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        获取租户列表及其统计信息
        
        Args:
            filters: 过滤条件
            search: 搜索关键词
            order_by: 排序字段
            order_desc: 是否降序
            limit: 限制数量
            offset: 偏移量
            
        Returns:
            包含统计信息的租户列表
        """
        # 构建基础查询
        query_parts = [
            "SELECT t.*, ",
            "COALESCE(u.user_count, 0) as current_users_count, ",
            "COALESCE(c.conversation_count, 0) as total_conversations ",
            "FROM tenants t ",
            "LEFT JOIN (",
            "  SELECT tenant_id, COUNT(*) as user_count ",
            "  FROM users WHERE is_active = true ",
            "  GROUP BY tenant_id",
            ") u ON t.id = u.tenant_id ",
            "LEFT JOIN (",
            "  SELECT tenant_id, COUNT(*) as conversation_count ",
            "  FROM conversations ",
            "  GROUP BY tenant_id",
            ") c ON t.id = c.tenant_id "
        ]
        
        # 构建WHERE条件
        where_conditions = []
        params = {}
        
        # 应用过滤条件
        if filters:
            for field_name, value in filters.items():
                if field_name in ['status', 'subscription_plan']:
                    where_conditions.append(f"t.{field_name} = :{field_name}")
                    params[field_name] = value
        
        # 搜索条件
        if search:
            where_conditions.append("(t.name ILIKE :search OR t.slug ILIKE :search)")
            params['search'] = f"%{search}%"
        
        # 添加WHERE子句
        if where_conditions:
            query_parts.append("WHERE " + " AND ".join(where_conditions) + " ")
        
        # 排序
        if order_by in ['name', 'slug', 'status', 'subscription_plan', 'created_at', 'updated_at']:
            order_direction = "DESC" if order_desc else "ASC"
            query_parts.append(f"ORDER BY t.{order_by} {order_direction} ")
        
        # 分页
        if limit is not None:
            query_parts.append(f"LIMIT {limit} ")
        if offset is not None:
            query_parts.append(f"OFFSET {offset} ")
        
        # 执行查询
        sql = "".join(query_parts)
        result = await self.session.execute(text(sql), params)
        
        # 转换结果为字典列表
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]
    
    async def count_tenants(
        self,
        filters: Optional[Dict[str, Any]] = None,
        search: Optional[str] = None
    ) -> int:
        """
        统计租户数量
        
        Args:
            filters: 过滤条件
            search: 搜索关键词
            
        Returns:
            租户数量
        """
        conditions = []
        
        # 应用过滤条件
        if filters:
            for field_name, value in filters.items():
                if hasattr(Tenant, field_name):
                    field = getattr(Tenant, field_name)
                    conditions.append(field == value)
        
        # 搜索条件
        if search:
            search_condition = or_(
                Tenant.name.ilike(f"%{search}%"),
                Tenant.slug.ilike(f"%{search}%")
            )
            conditions.append(search_condition)
        
        query = select(func.count(Tenant.id))
        
        # 添加WHERE条件
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    async def get_tenant_stats(self, tenant_id: uuid.UUID) -> Dict[str, Any]:
        """
        获取租户的详细统计信息
        
        Args:
            tenant_id: 租户ID
            
        Returns:
            租户统计信息字典
        """
        # 使用复杂查询获取统计信息
        sql = text("""
        SELECT 
            t.id as tenant_id,
            COALESCE(total_users.count, 0) as total_users,
            COALESCE(active_users.count, 0) as active_users,
            COALESCE(conversations.count, 0) as total_conversations,
            COALESCE(messages.count, 0) as total_messages,
            t.created_at,
            t.updated_at
        FROM tenants t
        LEFT JOIN (
            SELECT tenant_id, COUNT(*) as count 
            FROM users 
            WHERE tenant_id = :tenant_id
            GROUP BY tenant_id
        ) total_users ON t.id = total_users.tenant_id
        LEFT JOIN (
            SELECT tenant_id, COUNT(*) as count 
            FROM users 
            WHERE tenant_id = :tenant_id AND is_active = true
            GROUP BY tenant_id
        ) active_users ON t.id = active_users.tenant_id
        LEFT JOIN (
            SELECT tenant_id, COUNT(*) as count 
            FROM conversations 
            WHERE tenant_id = :tenant_id
            GROUP BY tenant_id
        ) conversations ON t.id = conversations.tenant_id
        LEFT JOIN (
            SELECT c.tenant_id, COUNT(m.id) as count 
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            WHERE c.tenant_id = :tenant_id
            GROUP BY c.tenant_id
        ) messages ON t.id = messages.tenant_id
        WHERE t.id = :tenant_id
        """)
        
        result = await self.session.execute(sql, {"tenant_id": tenant_id})
        row = result.fetchone()
        
        if not row:
            return {}
        
        return {
            "tenant_id": row.tenant_id,
            "total_users": row.total_users,
            "active_users": row.active_users,
            "total_conversations": row.total_conversations,
            "total_messages": row.total_messages,
            "api_calls_today": 0,  # 需要从audit_logs表计算
            "api_calls_this_month": 0,  # 需要从audit_logs表计算
            "storage_used_mb": 0,  # 需要计算存储使用量
            "last_activity_at": None  # 需要从audit_logs表获取
        }
    
    async def update_tenant_status(self, tenant_id: uuid.UUID, status: str) -> bool:
        """
        更新租户状态
        
        Args:
            tenant_id: 租户ID
            status: 新状态
            
        Returns:
            是否更新成功
        """
        updates = {"status": status}
        result = await self.update(tenant_id, updates)
        return result is not None
    
    async def get_active_tenants(self) -> List[Tenant]:
        """
        获取所有活跃租户
        
        Returns:
            活跃租户列表
        """
        query = select(Tenant).where(Tenant.status == "active")
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_tenants_by_subscription_plan(self, plan: str) -> List[Tenant]:
        """
        根据订阅计划获取租户
        
        Args:
            plan: 订阅计划
            
        Returns:
            租户列表
        """
        query = select(Tenant).where(Tenant.subscription_plan == plan)
        result = await self.session.execute(query)
        return list(result.scalars().all())