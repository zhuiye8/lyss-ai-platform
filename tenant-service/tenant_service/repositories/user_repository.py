# -*- coding: utf-8 -*-
"""
用户数据访问层

提供用户相关的数据库操作方法
"""

import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy import and_, or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .base import BaseRepository
from ..models.database.user import User
from ..models.database.role import Role


class UserRepository(BaseRepository):
    """用户Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)
    
    async def get_by_email(self, email: str, tenant_id: Optional[uuid.UUID] = None) -> Optional[User]:
        """
        根据邮箱获取用户
        
        Args:
            email: 用户邮箱
            tenant_id: 租户ID
            
        Returns:
            用户实例或None
        """
        conditions = [User.email == email]
        
        if tenant_id is not None:
            conditions.append(User.tenant_id == tenant_id)
        
        query = select(User).where(and_(*conditions))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_username(self, username: str, tenant_id: Optional[uuid.UUID] = None) -> Optional[User]:
        """
        根据用户名获取用户
        
        Args:
            username: 用户名
            tenant_id: 租户ID
            
        Returns:
            用户实例或None
        """
        conditions = [User.username == username]
        
        if tenant_id is not None:
            conditions.append(User.tenant_id == tenant_id)
        
        query = select(User).where(and_(*conditions))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_email_or_username(self, identifier: str, tenant_id: Optional[uuid.UUID] = None) -> Optional[User]:
        """
        根据邮箱或用户名获取用户（用于登录验证）
        
        Args:
            identifier: 邮箱或用户名
            tenant_id: 租户ID
            
        Returns:
            用户实例或None
        """
        conditions = [
            or_(
                User.email == identifier,
                User.username == identifier
            )
        ]
        
        if tenant_id is not None:
            conditions.append(User.tenant_id == tenant_id)
        
        query = select(User).options(selectinload(User.role)).where(and_(*conditions))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_with_role(self, user_id: uuid.UUID, tenant_id: Optional[uuid.UUID] = None) -> Optional[User]:
        """
        获取用户及其角色信息
        
        Args:
            user_id: 用户ID
            tenant_id: 租户ID
            
        Returns:
            包含角色信息的用户实例或None
        """
        conditions = [User.id == user_id]
        
        if tenant_id is not None:
            conditions.append(User.tenant_id == tenant_id)
        
        query = select(User).options(selectinload(User.role)).where(and_(*conditions))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_users_by_tenant(
        self,
        tenant_id: uuid.UUID,
        filters: Optional[Dict[str, Any]] = None,
        search: Optional[str] = None,
        order_by: str = "created_at",
        order_desc: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[User]:
        """
        获取租户下的用户列表
        
        Args:
            tenant_id: 租户ID
            filters: 过滤条件
            search: 搜索关键词（搜索邮箱和用户名）
            order_by: 排序字段
            order_desc: 是否降序
            limit: 限制数量
            offset: 偏移量
            
        Returns:
            用户列表
        """
        conditions = [User.tenant_id == tenant_id]
        
        # 应用过滤条件
        if filters:
            for field_name, value in filters.items():
                if hasattr(User, field_name):
                    field = getattr(User, field_name)
                    conditions.append(field == value)
        
        # 搜索条件
        if search:
            search_condition = or_(
                User.email.ilike(f"%{search}%"),
                User.username.ilike(f"%{search}%"),
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%")
            )
            conditions.append(search_condition)
        
        query = select(User).options(selectinload(User.role)).where(and_(*conditions))
        
        # 排序
        if hasattr(User, order_by):
            order_field = getattr(User, order_by)
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
    
    async def count_users_by_tenant(
        self,
        tenant_id: uuid.UUID,
        filters: Optional[Dict[str, Any]] = None,
        search: Optional[str] = None
    ) -> int:
        """
        统计租户下的用户数量
        
        Args:
            tenant_id: 租户ID
            filters: 过滤条件
            search: 搜索关键词
            
        Returns:
            用户数量
        """
        conditions = [User.tenant_id == tenant_id]
        
        # 应用过滤条件
        if filters:
            for field_name, value in filters.items():
                if hasattr(User, field_name):
                    field = getattr(User, field_name)
                    conditions.append(field == value)
        
        # 搜索条件
        if search:
            search_condition = or_(
                User.email.ilike(f"%{search}%"),
                User.username.ilike(f"%{search}%"),
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%")
            )
            conditions.append(search_condition)
        
        query = select(func.count(User.id)).where(and_(*conditions))
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    async def email_exists(self, email: str, tenant_id: uuid.UUID, exclude_user_id: Optional[uuid.UUID] = None) -> bool:
        """
        检查邮箱是否在租户内已存在
        
        Args:
            email: 邮箱地址
            tenant_id: 租户ID
            exclude_user_id: 排除的用户ID（用于更新时检查）
            
        Returns:
            是否存在
        """
        conditions = [
            User.email == email,
            User.tenant_id == tenant_id
        ]
        
        if exclude_user_id:
            conditions.append(User.id != exclude_user_id)
        
        query = select(func.count(User.id)).where(and_(*conditions))
        result = await self.session.execute(query)
        count = result.scalar() or 0
        return count > 0
    
    async def username_exists(self, username: str, tenant_id: uuid.UUID, exclude_user_id: Optional[uuid.UUID] = None) -> bool:
        """
        检查用户名是否在租户内已存在
        
        Args:
            username: 用户名
            tenant_id: 租户ID
            exclude_user_id: 排除的用户ID（用于更新时检查）
            
        Returns:
            是否存在
        """
        if not username:
            return False
        
        conditions = [
            User.username == username,
            User.tenant_id == tenant_id
        ]
        
        if exclude_user_id:
            conditions.append(User.id != exclude_user_id)
        
        query = select(func.count(User.id)).where(and_(*conditions))
        result = await self.session.execute(query)
        count = result.scalar() or 0
        return count > 0
    
    async def update_last_login(self, user_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        """
        更新用户最后登录时间
        
        Args:
            user_id: 用户ID
            tenant_id: 租户ID
            
        Returns:
            是否更新成功
        """
        from datetime import datetime
        
        updates = {"last_login_at": datetime.utcnow()}
        result = await self.update(user_id, updates, tenant_id)
        return result is not None
    
    async def get_by_email_in_tenant(self, email: str, tenant_id: uuid.UUID) -> Optional[User]:
        """
        在指定租户内根据邮箱获取用户
        
        Args:
            email: 用户邮箱
            tenant_id: 租户ID
            
        Returns:
            用户实例或None
        """
        return await self.get_by_email(email, tenant_id)
    
    async def get_by_username_in_tenant(self, username: str, tenant_id: uuid.UUID) -> Optional[User]:
        """
        在指定租户内根据用户名获取用户
        
        Args:
            username: 用户名
            tenant_id: 租户ID
            
        Returns:
            用户实例或None
        """
        return await self.get_by_username(username, tenant_id)
    
    async def get_by_id_in_tenant(self, user_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[User]:
        """
        在指定租户内根据ID获取用户
        
        Args:
            user_id: 用户ID
            tenant_id: 租户ID
            
        Returns:
            用户实例或None
        """
        return await self.get_with_role(user_id, tenant_id)
    
    async def get_users_with_role(
        self,
        filters: Optional[Dict[str, Any]] = None,
        search: Optional[str] = None,
        order_by: str = "created_at",
        order_desc: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[User]:
        """
        获取用户列表（包含角色信息）
        
        Args:
            filters: 过滤条件
            search: 搜索关键词
            order_by: 排序字段
            order_desc: 是否降序
            limit: 限制数量
            offset: 偏移量
            
        Returns:
            用户列表
        """
        if not filters or "tenant_id" not in filters:
            raise ValueError("必须提供tenant_id过滤条件")
        
        tenant_id = filters["tenant_id"]
        return await self.get_users_by_tenant(
            tenant_id, filters, search, order_by, order_desc, limit, offset
        )
    
    async def count_users(
        self,
        filters: Optional[Dict[str, Any]] = None,
        search: Optional[str] = None
    ) -> int:
        """
        统计用户数量
        
        Args:
            filters: 过滤条件
            search: 搜索关键词
            
        Returns:
            用户数量
        """
        if not filters or "tenant_id" not in filters:
            raise ValueError("必须提供tenant_id过滤条件")
        
        tenant_id = filters["tenant_id"]
        return await self.count_users_by_tenant(tenant_id, filters, search)
    
    async def get_user_stats(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """
        获取用户统计信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户统计信息字典
        """
        # 这里可以统计用户的对话数、消息数等
        # 暂时返回基础统计信息
        return {
            "total_conversations": 0,
            "total_messages": 0,
            "last_activity_at": None
        }
    
    async def soft_delete(self, user_id: uuid.UUID) -> bool:
        """
        软删除用户（设置为不活跃）
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否删除成功
        """
        updates = {"is_active": False}
        result = await self.update(user_id, updates)
        return result is not None
    
    async def update_last_login(self, user_id: uuid.UUID) -> Optional[User]:
        """
        更新用户最后登录时间
        
        Args:
            user_id: 用户ID
            
        Returns:
            更新后的用户对象，如果用户不存在则返回None
        """
        from datetime import datetime, timezone
        
        # 更新最后登录时间为当前UTC时间
        updates = {"last_login_at": datetime.now(timezone.utc)}
        return await self.update(user_id, updates)