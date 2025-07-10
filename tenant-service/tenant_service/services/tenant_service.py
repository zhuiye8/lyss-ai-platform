# -*- coding: utf-8 -*-
"""
租户业务逻辑服务

处理租户相关的业务逻辑和规则
"""

import uuid
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from ..repositories.tenant_repository import TenantRepository
from ..repositories.user_repository import UserRepository
from ..models.schemas.tenant import (
    TenantCreateRequest, 
    TenantUpdateRequest,
    TenantResponse,
    TenantDetailResponse,
    TenantStatsResponse,
    TenantListParams
)
from ..models.schemas.base import PaginatedResponse, PaginationInfo

logger = structlog.get_logger()


class TenantService:
    """租户服务类"""
    
    def __init__(self, db_session: AsyncSession):
        """
        初始化租户服务
        
        Args:
            db_session: 数据库会话
        """
        self.db = db_session
        self.tenant_repo = TenantRepository(db_session)
        self.user_repo = UserRepository(db_session)
    
    async def create_tenant(
        self, 
        request_data: TenantCreateRequest,
        request_id: str
    ) -> TenantResponse:
        """
        创建新租户
        
        Args:
            request_data: 租户创建请求数据
            request_id: 请求ID
            
        Returns:
            创建的租户信息
            
        Raises:
            ValueError: 当slug已存在时
        """
        logger.info(
            "开始创建租户",
            request_id=request_id,
            tenant_name=request_data.name,
            tenant_slug=request_data.slug,
            operation="create_tenant"
        )
        
        # 检查slug是否已存在
        if await self.tenant_repo.slug_exists(request_data.slug):
            logger.warning(
                "租户创建失败：slug已存在",
                request_id=request_id,
                tenant_slug=request_data.slug,
                operation="create_tenant"
            )
            raise ValueError(f"租户标识符 '{request_data.slug}' 已存在")
        
        # 创建租户
        try:
            tenant = await self.tenant_repo.create(
                name=request_data.name,
                slug=request_data.slug,
                subscription_plan=request_data.subscription_plan,
                max_users=request_data.max_users,
                settings=request_data.settings or {},
                status="active"
            )
            
            await self.db.commit()
            
            logger.info(
                "租户创建成功",
                request_id=request_id,
                tenant_id=str(tenant.id),
                tenant_name=tenant.name,
                tenant_slug=tenant.slug,
                operation="create_tenant"
            )
            
            # 转换为响应模型
            return TenantResponse(
                id=tenant.id,
                name=tenant.name,
                slug=tenant.slug,
                status=tenant.status,
                subscription_plan=tenant.subscription_plan,
                max_users=tenant.max_users,
                settings=tenant.settings,
                created_at=tenant.created_at,
                updated_at=tenant.updated_at,
                current_users_count=0  # 新租户没有用户
            )
            
        except Exception as e:
            await self.db.rollback()
            logger.error(
                "租户创建失败",
                request_id=request_id,
                tenant_name=request_data.name,
                error=str(e),
                operation="create_tenant"
            )
            raise
    
    async def get_tenant_by_id(
        self, 
        tenant_id: uuid.UUID,
        request_id: str,
        include_stats: bool = False
    ) -> Optional[TenantResponse]:
        """
        根据ID获取租户信息
        
        Args:
            tenant_id: 租户ID
            request_id: 请求ID
            include_stats: 是否包含统计信息
            
        Returns:
            租户信息或None
        """
        logger.info(
            "获取租户信息",
            request_id=request_id,
            tenant_id=str(tenant_id),
            include_stats=include_stats,
            operation="get_tenant"
        )
        
        tenant = await self.tenant_repo.get_by_id(tenant_id)
        
        if not tenant:
            logger.warning(
                "租户不存在",
                request_id=request_id,
                tenant_id=str(tenant_id),
                operation="get_tenant"
            )
            return None
        
        # 如果需要统计信息，获取详细数据
        if include_stats:
            stats = await self.tenant_repo.get_tenant_stats(tenant_id)
            return TenantDetailResponse(
                id=tenant.id,
                name=tenant.name,
                slug=tenant.slug,
                status=tenant.status,
                subscription_plan=tenant.subscription_plan,
                max_users=tenant.max_users,
                settings=tenant.settings,
                created_at=tenant.created_at,
                updated_at=tenant.updated_at,
                current_users_count=stats.get("total_users", 0),
                active_users_count=stats.get("active_users", 0),
                inactive_users_count=stats.get("total_users", 0) - stats.get("active_users", 0),
                total_conversations=stats.get("total_conversations", 0),
                total_api_calls=0,  # 需要从audit_logs计算
                total_tokens_used=0  # 需要从使用记录计算
            )
        else:
            # 获取基本用户统计
            user_count = await self.user_repo.count_users_by_tenant(tenant_id)
            
            return TenantResponse(
                id=tenant.id,
                name=tenant.name,
                slug=tenant.slug,
                status=tenant.status,
                subscription_plan=tenant.subscription_plan,
                max_users=tenant.max_users,
                settings=tenant.settings,
                created_at=tenant.created_at,
                updated_at=tenant.updated_at,
                current_users_count=user_count
            )
    
    async def get_tenant_list(
        self,
        params: TenantListParams,
        request_id: str
    ) -> PaginatedResponse[TenantResponse]:
        """
        获取租户列表
        
        Args:
            params: 查询参数
            request_id: 请求ID
            
        Returns:
            分页的租户列表
        """
        logger.info(
            "获取租户列表",
            request_id=request_id,
            page=params.page,
            page_size=params.page_size,
            operation="get_tenant_list"
        )
        
        # 构建过滤条件
        filters = {}
        if params.status:
            filters['status'] = params.status
        if params.subscription_plan:
            filters['subscription_plan'] = params.subscription_plan
        
        # 计算偏移量
        offset = (params.page - 1) * params.page_size
        
        # 获取租户列表（包含统计信息）
        tenants_data = await self.tenant_repo.get_tenants_with_stats(
            filters=filters,
            search=params.search,
            order_by=params.sort_by,
            order_desc=(params.sort_order == "desc"),
            limit=params.page_size,
            offset=offset
        )
        
        # 统计总数
        total_count = await self.tenant_repo.count_tenants(
            filters=filters,
            search=params.search
        )
        
        # 转换为响应模型
        tenant_list = []
        for data in tenants_data:
            tenant_list.append(TenantResponse(
                id=data['id'],
                name=data['name'],
                slug=data['slug'],
                status=data['status'],
                subscription_plan=data['subscription_plan'],
                max_users=data['max_users'],
                settings=data['settings'] or {},
                created_at=data['created_at'],
                updated_at=data['updated_at'],
                current_users_count=data.get('current_users_count', 0),
                total_conversations=data.get('total_conversations', 0)
            ))
        
        # 计算分页信息
        total_pages = (total_count + params.page_size - 1) // params.page_size
        pagination = PaginationInfo(
            page=params.page,
            page_size=params.page_size,
            total_items=total_count,
            total_pages=total_pages,
            has_next=params.page < total_pages,
            has_prev=params.page > 1
        )
        
        logger.info(
            "租户列表获取成功",
            request_id=request_id,
            total_count=total_count,
            returned_count=len(tenant_list),
            operation="get_tenant_list"
        )
        
        return PaginatedResponse[TenantResponse](
            items=tenant_list,
            pagination=pagination
        )
    
    async def update_tenant(
        self,
        tenant_id: uuid.UUID,
        request_data: TenantUpdateRequest,
        request_id: str
    ) -> Optional[TenantResponse]:
        """
        更新租户信息
        
        Args:
            tenant_id: 租户ID
            request_data: 更新请求数据
            request_id: 请求ID
            
        Returns:
            更新后的租户信息或None
        """
        logger.info(
            "开始更新租户",
            request_id=request_id,
            tenant_id=str(tenant_id),
            operation="update_tenant"
        )
        
        # 检查租户是否存在
        existing_tenant = await self.tenant_repo.get_by_id(tenant_id)
        if not existing_tenant:
            logger.warning(
                "租户更新失败：租户不存在",
                request_id=request_id,
                tenant_id=str(tenant_id),
                operation="update_tenant"
            )
            return None
        
        # 构建更新字典
        updates = {}
        if request_data.name is not None:
            updates['name'] = request_data.name
        if request_data.status is not None:
            updates['status'] = request_data.status
        if request_data.subscription_plan is not None:
            updates['subscription_plan'] = request_data.subscription_plan
        if request_data.max_users is not None:
            updates['max_users'] = request_data.max_users
        if request_data.settings is not None:
            updates['settings'] = request_data.settings
        
        if not updates:
            # 没有需要更新的字段
            logger.info(
                "租户更新跳过：没有需要更新的字段",
                request_id=request_id,
                tenant_id=str(tenant_id),
                operation="update_tenant"
            )
            return await self.get_tenant_by_id(tenant_id, request_id)
        
        try:
            # 执行更新
            updated_tenant = await self.tenant_repo.update(tenant_id, updates)
            await self.db.commit()
            
            logger.info(
                "租户更新成功",
                request_id=request_id,
                tenant_id=str(tenant_id),
                updated_fields=list(updates.keys()),
                operation="update_tenant"
            )
            
            # 返回更新后的租户信息
            return await self.get_tenant_by_id(tenant_id, request_id)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(
                "租户更新失败",
                request_id=request_id,
                tenant_id=str(tenant_id),
                error=str(e),
                operation="update_tenant"
            )
            raise
    
    async def delete_tenant(
        self,
        tenant_id: uuid.UUID,
        request_id: str
    ) -> bool:
        """
        删除租户（软删除，设置为inactive状态）
        
        Args:
            tenant_id: 租户ID
            request_id: 请求ID
            
        Returns:
            是否删除成功
        """
        logger.info(
            "开始删除租户",
            request_id=request_id,
            tenant_id=str(tenant_id),
            operation="delete_tenant"
        )
        
        # 检查租户是否存在
        existing_tenant = await self.tenant_repo.get_by_id(tenant_id)
        if not existing_tenant:
            logger.warning(
                "租户删除失败：租户不存在",
                request_id=request_id,
                tenant_id=str(tenant_id),
                operation="delete_tenant"
            )
            return False
        
        try:
            # 软删除：设置状态为inactive
            success = await self.tenant_repo.update_tenant_status(tenant_id, "inactive")
            await self.db.commit()
            
            logger.info(
                "租户删除成功",
                request_id=request_id,
                tenant_id=str(tenant_id),
                operation="delete_tenant"
            )
            
            return success
            
        except Exception as e:
            await self.db.rollback()
            logger.error(
                "租户删除失败",
                request_id=request_id,
                tenant_id=str(tenant_id),
                error=str(e),
                operation="delete_tenant"
            )
            raise
    
    async def get_tenant_stats(
        self,
        tenant_id: uuid.UUID,
        request_id: str
    ) -> Optional[TenantStatsResponse]:
        """
        获取租户详细统计信息
        
        Args:
            tenant_id: 租户ID
            request_id: 请求ID
            
        Returns:
            租户统计信息或None
        """
        logger.info(
            "获取租户统计信息",
            request_id=request_id,
            tenant_id=str(tenant_id),
            operation="get_tenant_stats"
        )
        
        # 检查租户是否存在
        tenant = await self.tenant_repo.get_by_id(tenant_id)
        if not tenant:
            return None
        
        # 获取统计数据
        stats = await self.tenant_repo.get_tenant_stats(tenant_id)
        
        return TenantStatsResponse(
            tenant_id=tenant_id,
            total_users=stats.get("total_users", 0),
            active_users=stats.get("active_users", 0),
            total_conversations=stats.get("total_conversations", 0),
            total_messages=stats.get("total_messages", 0),
            api_calls_today=stats.get("api_calls_today", 0),
            api_calls_this_month=stats.get("api_calls_this_month", 0),
            storage_used_mb=stats.get("storage_used_mb", 0),
            last_activity_at=stats.get("last_activity_at")
        )