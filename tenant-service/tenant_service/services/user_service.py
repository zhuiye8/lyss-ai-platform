# -*- coding: utf-8 -*-
"""
用户业务逻辑服务

处理用户相关的业务逻辑和规则
"""

import uuid
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
from passlib.context import CryptContext

from ..repositories.user_repository import UserRepository
from ..repositories.tenant_repository import TenantRepository
from ..models.schemas.user import (
    UserCreateRequest,
    UserUpdateRequest,
    UserResponse,
    UserDetailResponse,
    UserListParams
)
from ..models.database.user import User

logger = structlog.get_logger()

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    """用户服务类"""
    
    def __init__(self, db_session: AsyncSession):
        """
        初始化用户服务
        
        Args:
            db_session: 数据库会话
        """
        self.db = db_session
        self.user_repo = UserRepository(db_session)
        self.tenant_repo = TenantRepository(db_session)
    
    async def create_user(
        self,
        request_data: UserCreateRequest,
        tenant_id: str,
        request_id: str
    ) -> UserResponse:
        """
        创建新用户
        
        Args:
            request_data: 用户创建请求数据
            tenant_id: 租户ID
            request_id: 请求ID
            
        Returns:
            创建的用户信息
            
        Raises:
            ValueError: 当数据验证失败时
        """
        try:
            logger.info(
                "开始创建用户",
                request_id=request_id,
                tenant_id=tenant_id,
                email=request_data.email,
                operation="create_user"
            )
            
            # 验证租户是否存在
            tenant = await self.tenant_repo.get_by_id(uuid.UUID(tenant_id))
            if not tenant:
                raise ValueError("租户不存在")
            
            # 检查邮箱是否已存在（租户内唯一）
            existing_user = await self.user_repo.get_by_email_in_tenant(
                request_data.email, uuid.UUID(tenant_id)
            )
            if existing_user:
                raise ValueError("该邮箱已被使用")
            
            # 检查用户名是否已存在（如果提供了用户名）
            if request_data.username:
                existing_username = await self.user_repo.get_by_username_in_tenant(
                    request_data.username, uuid.UUID(tenant_id)
                )
                if existing_username:
                    raise ValueError("该用户名已被使用")
            
            # 获取角色ID
            role_id = await self._get_role_id_by_name(request_data.role)
            if not role_id:
                raise ValueError(f"角色 '{request_data.role}' 不存在")
            
            # 加密密码
            hashed_password = pwd_context.hash(request_data.password)
            
            # 创建用户数据
            user_data = {
                "email": request_data.email,
                "username": request_data.username,
                "hashed_password": hashed_password,
                "first_name": request_data.first_name,
                "last_name": request_data.last_name,
                "role_id": role_id,
                "tenant_id": uuid.UUID(tenant_id),
                "is_active": True,
                "email_verified": False
            }
            
            # 创建用户
            user = await self.user_repo.create(user_data)
            
            # 记录成功日志
            logger.info(
                "用户创建成功",
                request_id=request_id,
                tenant_id=tenant_id,
                user_id=str(user.id),
                email=user.email,
                operation="create_user"
            )
            
            # 转换为响应格式
            return await self._convert_to_user_response(user)
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(
                "用户创建失败",
                request_id=request_id,
                tenant_id=tenant_id,
                error=str(e),
                operation="create_user"
            )
            raise
    
    async def get_users_paginated(
        self,
        tenant_id: str,
        params: UserListParams,
        request_id: str
    ) -> Tuple[List[UserResponse], int]:
        """
        分页获取用户列表
        
        Args:
            tenant_id: 租户ID
            params: 查询参数
            request_id: 请求ID
            
        Returns:
            用户列表和总数的元组
        """
        try:
            # 构建过滤条件
            filters = {"tenant_id": uuid.UUID(tenant_id)}
            
            if params.role:
                filters["role"] = params.role
            if params.is_active is not None:
                filters["is_active"] = params.is_active
            
            # 计算偏移量
            offset = (params.page - 1) * params.page_size
            
            # 获取用户列表
            users = await self.user_repo.get_users_with_role(
                filters=filters,
                search=params.search,
                order_by=params.sort_by,
                order_desc=(params.sort_order == "desc"),
                limit=params.page_size,
                offset=offset
            )
            
            # 获取总数
            total_count = await self.user_repo.count_users(
                filters=filters,
                search=params.search
            )
            
            # 转换为响应格式
            user_responses = []
            for user in users:
                user_response = await self._convert_to_user_response(user)
                user_responses.append(user_response)
            
            logger.info(
                "用户列表获取成功",
                request_id=request_id,
                tenant_id=tenant_id,
                count=len(user_responses),
                total=total_count,
                operation="get_users_paginated"
            )
            
            return user_responses, total_count
            
        except Exception as e:
            logger.error(
                "获取用户列表失败",
                request_id=request_id,
                tenant_id=tenant_id,
                error=str(e),
                operation="get_users_paginated"
            )
            raise
    
    async def get_user_detail(
        self,
        user_id: uuid.UUID,
        tenant_id: str,
        request_id: str
    ) -> Optional[UserDetailResponse]:
        """
        获取用户详细信息
        
        Args:
            user_id: 用户ID
            tenant_id: 租户ID
            request_id: 请求ID
            
        Returns:
            用户详细信息或None
        """
        try:
            # 获取用户信息（包含角色）
            user = await self.user_repo.get_with_role(user_id, uuid.UUID(tenant_id))
            
            if not user:
                return None
            
            # 获取用户统计信息
            stats = await self.user_repo.get_user_stats(user_id)
            
            # 构建详细响应
            user_detail = UserDetailResponse(
                id=user.id,
                email=user.email,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                full_name=user.full_name,
                role=user.role.name if user.role else "end_user",
                role_display_name=user.role.display_name if user.role else "终端用户",
                tenant_id=user.tenant_id,
                is_active=user.is_active,
                email_verified=user.email_verified,
                last_login_at=user.last_login_at,
                login_attempts=user.login_attempts,
                locked_until=user.locked_until,
                is_locked=user.is_locked,
                created_at=user.created_at,
                updated_at=user.updated_at,
                # 统计信息
                total_conversations=stats.get("total_conversations", 0),
                total_messages=stats.get("total_messages", 0),
                last_activity_at=stats.get("last_activity_at")
            )
            
            logger.info(
                "用户详情获取成功",
                request_id=request_id,
                user_id=str(user_id),
                tenant_id=tenant_id,
                operation="get_user_detail"
            )
            
            return user_detail
            
        except Exception as e:
            logger.error(
                "获取用户详情失败",
                request_id=request_id,
                user_id=str(user_id),
                tenant_id=tenant_id,
                error=str(e),
                operation="get_user_detail"
            )
            raise
    
    async def update_user(
        self,
        user_id: uuid.UUID,
        request_data: UserUpdateRequest,
        tenant_id: str,
        request_id: str
    ) -> Optional[UserResponse]:
        """
        更新用户信息
        
        Args:
            user_id: 用户ID
            request_data: 更新请求数据
            tenant_id: 租户ID
            request_id: 请求ID
            
        Returns:
            更新后的用户信息或None
        """
        try:
            # 检查用户是否存在
            existing_user = await self.user_repo.get_with_role(user_id, uuid.UUID(tenant_id))
            if not existing_user:
                return None
            
            # 准备更新数据
            update_data = {}
            
            # 处理基本信息更新
            if request_data.first_name is not None:
                update_data["first_name"] = request_data.first_name
            if request_data.last_name is not None:
                update_data["last_name"] = request_data.last_name
            if request_data.username is not None:
                # 检查用户名是否已被其他用户使用
                existing_username = await self.user_repo.get_by_username_in_tenant(
                    request_data.username, uuid.UUID(tenant_id)
                )
                if existing_username and existing_username.id != user_id:
                    raise ValueError("该用户名已被使用")
                update_data["username"] = request_data.username
            
            # 处理角色更新
            if request_data.role:
                role_id = await self._get_role_id_by_name(request_data.role)
                if not role_id:
                    raise ValueError(f"角色 '{request_data.role}' 不存在")
                update_data["role_id"] = role_id
            
            # 处理密码更新
            if request_data.password:
                update_data["hashed_password"] = pwd_context.hash(request_data.password)
            
            # 处理状态更新
            if request_data.is_active is not None:
                update_data["is_active"] = request_data.is_active
            
            # 执行更新
            if update_data:
                user = await self.user_repo.update(user_id, update_data)
                
                logger.info(
                    "用户更新成功",
                    request_id=request_id,
                    user_id=str(user_id),
                    tenant_id=tenant_id,
                    updated_fields=list(update_data.keys()),
                    operation="update_user"
                )
                
                return await self._convert_to_user_response(user)
            
            # 没有更新数据，返回原用户信息
            return await self._convert_to_user_response(existing_user)
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(
                "用户更新失败",
                request_id=request_id,
                user_id=str(user_id),
                tenant_id=tenant_id,
                error=str(e),
                operation="update_user"
            )
            raise
    
    async def delete_user(
        self,
        user_id: uuid.UUID,
        tenant_id: str,
        request_id: str
    ) -> bool:
        """
        删除用户（软删除）
        
        Args:
            user_id: 用户ID
            tenant_id: 租户ID
            request_id: 请求ID
            
        Returns:
            是否删除成功
        """
        try:
            # 检查用户是否存在
            user = await self.user_repo.get_by_id_in_tenant(user_id, uuid.UUID(tenant_id))
            if not user:
                return False
            
            # 执行软删除（设置为不活跃）
            success = await self.user_repo.soft_delete(user_id)
            
            if success:
                logger.info(
                    "用户删除成功",
                    request_id=request_id,
                    user_id=str(user_id),
                    tenant_id=tenant_id,
                    operation="delete_user"
                )
            
            return success
            
        except Exception as e:
            logger.error(
                "用户删除失败",
                request_id=request_id,
                user_id=str(user_id),
                tenant_id=tenant_id,
                error=str(e),
                operation="delete_user"
            )
            raise
    
    async def update_user_status(
        self,
        user_id: uuid.UUID,
        is_active: bool,
        tenant_id: str,
        request_id: str
    ) -> Optional[UserResponse]:
        """
        更新用户激活状态
        
        Args:
            user_id: 用户ID
            is_active: 是否激活
            tenant_id: 租户ID
            request_id: 请求ID
            
        Returns:
            更新后的用户信息或None
        """
        try:
            # 检查用户是否存在
            existing_user = await self.user_repo.get_with_role(user_id, uuid.UUID(tenant_id))
            if not existing_user:
                return None
            
            # 更新激活状态
            user = await self.user_repo.update(user_id, {"is_active": is_active})
            
            status_text = "激活" if is_active else "禁用"
            logger.info(
                f"用户{status_text}成功",
                request_id=request_id,
                user_id=str(user_id),
                tenant_id=tenant_id,
                is_active=is_active,
                operation="update_user_status"
            )
            
            return await self._convert_to_user_response(user)
            
        except Exception as e:
            logger.error(
                "用户状态更新失败",
                request_id=request_id,
                user_id=str(user_id),
                tenant_id=tenant_id,
                error=str(e),
                operation="update_user_status"
            )
            raise
    
    async def _get_role_id_by_name(self, role_name: str) -> Optional[uuid.UUID]:
        """
        根据角色名称获取角色ID
        
        Args:
            role_name: 角色名称
            
        Returns:
            角色ID或None
        """
        from ..repositories.base import BaseRepository
        from ..models.database.role import Role
        from sqlalchemy import select
        
        query = select(Role.id).where(Role.name == role_name)
        result = await self.db.execute(query)
        role_id = result.scalar_one_or_none()
        return role_id
    
    async def _convert_to_user_response(self, user: User) -> UserResponse:
        """
        将用户实体转换为响应格式
        
        Args:
            user: 用户实体
            
        Returns:
            用户响应格式
        """
        return UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            full_name=user.full_name,
            role=user.role.name if user.role else "end_user",
            role_display_name=user.role.display_name if user.role else "终端用户",
            tenant_id=user.tenant_id,
            is_active=user.is_active,
            email_verified=user.email_verified,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
            updated_at=user.updated_at
        )