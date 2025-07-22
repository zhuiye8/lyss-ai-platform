# -*- coding: utf-8 -*-
"""
用户管理器模块

负责用户生命周期管理的核心业务逻辑，包括：
- 用户创建、激活、更新、删除
- 多租户用户关联管理
- 用户状态和权限管理
- 用户数据验证和安全处理

基于架构文档的完整实现，支持异步操作和事务管理。
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union
from sqlalchemy import and_, or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ..models.database.user import User, UserStatus
from ..models.schemas.user import UserCreate, UserUpdate, UserResponse
from ..core.database_engine import get_db_session
from ..utils.validators import validate_email, validate_phone, validate_user_name
from ..utils.email_service import send_verification_email, send_welcome_email
from ..utils.security import generate_verification_token, verify_token
from ..services.notification_service import notification_service
from .lifecycle import UserLifecycleManager
from .validator import UserDataValidator

logger = logging.getLogger(__name__)

class UserManager:
    """
    用户管理器 - 用户生命周期管理的核心类
    
    提供完整的用户管理功能：
    - 用户CRUD操作
    - 多租户关联管理
    - 状态管理和验证
    - 安全策略执行
    """
    
    def __init__(self):
        self.lifecycle_manager = UserLifecycleManager()
        self.data_validator = UserDataValidator()
        self.verification_expire_hours = 24
        self.inactive_threshold_days = 90
        
    async def create_user(
        self,
        user_data: UserCreate,
        tenant_id: str,
        created_by: Optional[str] = None,
        auto_activate: bool = False,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        创建新用户
        
        Args:
            user_data: 用户创建数据
            tenant_id: 租户ID
            created_by: 创建者ID
            auto_activate: 是否自动激活
            db: 数据库会话
            
        Returns:
            Dict[str, Any]: 创建结果
            
        Raises:
            ValueError: 数据验证失败
            IntegrityError: 用户已存在
        """
        db_session = db
        if db is None:
            async with get_db_session() as session:
                return await self._create_user_impl(
                    user_data, tenant_id, created_by, auto_activate, session
                )
        else:
            return await self._create_user_impl(
                user_data, tenant_id, created_by, auto_activate, db_session
            )
    
    async def _create_user_impl(
        self,
        user_data: UserCreate,
        tenant_id: str,
        created_by: Optional[str],
        auto_activate: bool,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """用户创建实现"""
        try:
            # 1. 数据验证
            await self.data_validator.validate_create_data(user_data, db)
            
            # 2. 检查用户是否已存在
            existing_result = await self._handle_existing_user(
                user_data.email, tenant_id, created_by, db
            )
            if existing_result:
                return existing_result
            
            # 3. 创建用户记录
            user_id = str(uuid.uuid4())
            
            new_user = User(
                id=user_id,
                email=user_data.email,
                name=user_data.name,
                phone=user_data.phone,
                avatar_url=user_data.avatar_url,
                bio=user_data.bio,
                tenant_id=tenant_id,
                status=UserStatus.ACTIVE if auto_activate else UserStatus.PENDING,
                email_verified=auto_activate,
                created_by=created_by,
                created_at=datetime.utcnow()
            )
            
            db.add(new_user)
            await db.flush()  # 获取ID但不提交
            
            # 4. 创建用户画像（委托给profile服务）
            await self._create_user_profile(user_id, user_data, db)
            
            # 5. 执行生命周期回调
            await self.lifecycle_manager.on_user_created(
                user_id, tenant_id, user_data.dict(), created_by
            )
            
            # 6. 发送验证邮件（如果需要）
            if not auto_activate and user_data.email:
                await self._send_verification_email(
                    user_id, user_data.email, user_data.name
                )
            
            # 7. 发送欢迎通知（如果自动激活）
            if auto_activate:
                await notification_service.send_welcome_notification(user_id)
            
            # 8. 记录用户创建事件
            await self._log_user_event(
                user_id, "user_created", 
                {
                    "tenant_id": tenant_id,
                    "created_by": created_by,
                    "auto_activate": auto_activate,
                    "email": user_data.email
                },
                db
            )
            
            await db.commit()
            
            logger.info(f"用户创建成功: {user_data.email} (ID: {user_id})")
            
            return {
                "success": True,
                "user_id": user_id,
                "email": user_data.email,
                "status": new_user.status.value,
                "requires_verification": not auto_activate,
                "message": "用户创建成功" + ("，请检查邮箱完成验证" if not auto_activate else "")
            }
            
        except IntegrityError as e:
            await db.rollback()
            logger.warning(f"用户创建失败 - 数据冲突: {e}")
            raise ValueError("邮箱已被使用")
            
        except Exception as e:
            await db.rollback()
            logger.error(f"用户创建失败: {e}")
            raise
    
    async def activate_user(
        self,
        user_id: str,
        verification_token: Optional[str] = None,
        activated_by: Optional[str] = None,
        tenant_id: Optional[str] = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        激活用户
        
        Args:
            user_id: 用户ID
            verification_token: 验证令牌
            activated_by: 激活操作者ID
            tenant_id: 租户ID（用于权限检查）
            db: 数据库会话
            
        Returns:
            Dict[str, Any]: 激活结果
        """
        if db is None:
            async with get_db_session() as session:
                return await self._activate_user_impl(
                    user_id, verification_token, activated_by, tenant_id, session
                )
        else:
            return await self._activate_user_impl(
                user_id, verification_token, activated_by, tenant_id, db
            )
    
    async def _activate_user_impl(
        self,
        user_id: str,
        verification_token: Optional[str],
        activated_by: Optional[str],
        tenant_id: Optional[str],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """用户激活实现"""
        try:
            # 1. 获取用户信息
            user = await self._get_user_by_id_and_tenant(user_id, tenant_id, db)
            if not user:
                raise ValueError("用户不存在")
            
            # 2. 检查用户状态
            if user.status == UserStatus.ACTIVE:
                return {
                    "success": True,
                    "message": "用户已经处于活跃状态",
                    "user_id": user_id
                }
            
            if user.status == UserStatus.BANNED:
                raise ValueError("用户已被禁用，无法激活")
            
            if user.status == UserStatus.DELETED:
                raise ValueError("用户已被删除，无法激活")
            
            # 3. 验证令牌（如果提供）
            if verification_token:
                token_valid = await self._verify_activation_token(
                    user_id, verification_token
                )
                if not token_valid:
                    raise ValueError("验证令牌无效或已过期")
            
            # 4. 执行激活
            user.status = UserStatus.ACTIVE
            user.email_verified = True
            user.activated_at = datetime.utcnow()
            user.activated_by = activated_by
            user.updated_at = datetime.utcnow()
            
            # 5. 生命周期回调
            await self.lifecycle_manager.on_user_activated(
                user_id, user.tenant_id, activated_by
            )
            
            # 6. 发送欢迎通知
            await notification_service.send_welcome_notification(user_id)
            
            # 7. 记录激活事件
            await self._log_user_event(
                user_id, "user_activated",
                {
                    "activated_by": activated_by,
                    "method": "email" if verification_token else "admin",
                    "tenant_id": user.tenant_id
                },
                db
            )
            
            await db.commit()
            
            logger.info(f"用户激活成功: {user.email} (ID: {user_id})")
            
            return {
                "success": True,
                "message": "用户激活成功",
                "user_id": user_id,
                "activated_at": user.activated_at.isoformat()
            }
            
        except Exception as e:
            await db.rollback()
            logger.error(f"用户激活失败: {e}")
            raise
    
    async def update_user(
        self,
        user_id: str,
        update_data: UserUpdate,
        updated_by: Optional[str] = None,
        tenant_id: Optional[str] = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        更新用户信息
        
        Args:
            user_id: 用户ID
            update_data: 更新数据
            updated_by: 更新操作者ID
            tenant_id: 租户ID
            db: 数据库会话
            
        Returns:
            Dict[str, Any]: 更新结果
        """
        if db is None:
            async with get_db_session() as session:
                return await self._update_user_impl(
                    user_id, update_data, updated_by, tenant_id, session
                )
        else:
            return await self._update_user_impl(
                user_id, update_data, updated_by, tenant_id, db
            )
    
    async def _update_user_impl(
        self,
        user_id: str,
        update_data: UserUpdate,
        updated_by: Optional[str],
        tenant_id: Optional[str],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """用户更新实现"""
        try:
            # 1. 获取用户
            user = await self._get_user_by_id_and_tenant(user_id, tenant_id, db)
            if not user:
                raise ValueError("用户不存在")
            
            # 2. 权限检查
            if updated_by and updated_by != user_id:
                await self._check_update_permission(updated_by, user_id, tenant_id)
            
            # 3. 数据验证
            update_dict = update_data.dict(exclude_unset=True)
            await self.data_validator.validate_update_data(
                update_dict, user_id, db
            )
            
            # 4. 识别敏感字段变更
            sensitive_fields = ["email", "phone"]
            sensitive_changes = {}
            
            for field in sensitive_fields:
                if field in update_dict and getattr(user, field) != update_dict[field]:
                    sensitive_changes[field] = {
                        "old": getattr(user, field),
                        "new": update_dict[field]
                    }
            
            # 5. 应用更新
            old_values = {}
            for field, value in update_dict.items():
                if hasattr(user, field):
                    old_values[field] = getattr(user, field)
                    setattr(user, field, value)
            
            user.updated_at = datetime.utcnow()
            user.updated_by = updated_by
            
            # 6. 处理敏感字段变更
            if sensitive_changes:
                await self._handle_sensitive_field_changes(
                    user, sensitive_changes, updated_by, db
                )
            
            # 7. 生命周期回调
            await self.lifecycle_manager.on_user_updated(
                user_id, tenant_id, old_values, update_dict, updated_by
            )
            
            # 8. 记录更新事件
            await self._log_user_event(
                user_id, "user_updated",
                {
                    "updated_by": updated_by,
                    "fields": list(update_dict.keys()),
                    "sensitive_changes": list(sensitive_changes.keys()),
                    "tenant_id": tenant_id
                },
                db
            )
            
            await db.commit()
            
            logger.info(f"用户信息更新成功: {user.email} (ID: {user_id})")
            
            return {
                "success": True,
                "message": "用户信息更新成功",
                "user_id": user_id,
                "updated_fields": list(update_dict.keys()),
                "requires_verification": bool(sensitive_changes)
            }
            
        except Exception as e:
            await db.rollback()
            logger.error(f"用户信息更新失败: {e}")
            raise
    
    async def deactivate_user(
        self,
        user_id: str,
        reason: Optional[str] = None,
        deactivated_by: Optional[str] = None,
        tenant_id: Optional[str] = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        停用用户
        
        Args:
            user_id: 用户ID
            reason: 停用原因
            deactivated_by: 停用操作者ID
            tenant_id: 租户ID
            db: 数据库会话
            
        Returns:
            Dict[str, Any]: 停用结果
        """
        if db is None:
            async with get_db_session() as session:
                return await self._deactivate_user_impl(
                    user_id, reason, deactivated_by, tenant_id, session
                )
        else:
            return await self._deactivate_user_impl(
                user_id, reason, deactivated_by, tenant_id, db
            )
    
    async def _deactivate_user_impl(
        self,
        user_id: str,
        reason: Optional[str],
        deactivated_by: Optional[str],
        tenant_id: Optional[str],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """用户停用实现"""
        try:
            user = await self._get_user_by_id_and_tenant(user_id, tenant_id, db)
            if not user:
                raise ValueError("用户不存在")
            
            if user.status == UserStatus.INACTIVE:
                return {
                    "success": True,
                    "message": "用户已经处于停用状态",
                    "user_id": user_id
                }
            
            # 更新用户状态
            user.status = UserStatus.INACTIVE
            user.deactivated_at = datetime.utcnow()
            user.deactivated_by = deactivated_by
            user.deactivation_reason = reason
            user.updated_at = datetime.utcnow()
            
            # 生命周期回调 - 撤销会话等
            await self.lifecycle_manager.on_user_deactivated(
                user_id, tenant_id, reason, deactivated_by
            )
            
            # 发送停用通知
            await notification_service.send_deactivation_notification(
                user_id, reason
            )
            
            # 记录停用事件
            await self._log_user_event(
                user_id, "user_deactivated",
                {
                    "deactivated_by": deactivated_by,
                    "reason": reason,
                    "tenant_id": tenant_id
                },
                db
            )
            
            await db.commit()
            
            logger.info(f"用户停用成功: {user.email} (ID: {user_id})")
            
            return {
                "success": True,
                "message": "用户停用成功",
                "user_id": user_id,
                "deactivated_at": user.deactivated_at.isoformat()
            }
            
        except Exception as e:
            await db.rollback()
            logger.error(f"用户停用失败: {e}")
            raise
    
    async def delete_user(
        self,
        user_id: str,
        delete_type: str = "soft",  # "soft", "hard", "anonymize"
        deleted_by: Optional[str] = None,
        tenant_id: Optional[str] = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        删除用户
        
        Args:
            user_id: 用户ID
            delete_type: 删除类型
            deleted_by: 删除操作者ID
            tenant_id: 租户ID
            db: 数据库会话
            
        Returns:
            Dict[str, Any]: 删除结果
        """
        if db is None:
            async with get_db_session() as session:
                return await self._delete_user_impl(
                    user_id, delete_type, deleted_by, tenant_id, session
                )
        else:
            return await self._delete_user_impl(
                user_id, delete_type, deleted_by, tenant_id, db
            )
    
    async def _delete_user_impl(
        self,
        user_id: str,
        delete_type: str,
        deleted_by: Optional[str],
        tenant_id: Optional[str],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """用户删除实现"""
        try:
            user = await self._get_user_by_id_and_tenant(user_id, tenant_id, db)
            if not user:
                raise ValueError("用户不存在")
            
            if delete_type == "soft":
                # 软删除 - 标记为已删除
                user.status = UserStatus.DELETED
                user.deleted_at = datetime.utcnow()
                user.deleted_by = deleted_by
                user.updated_at = datetime.utcnow()
                
            elif delete_type == "anonymize":
                # 数据匿名化
                await self._anonymize_user_data(user, db)
                user.status = UserStatus.ANONYMIZED
                user.deleted_at = datetime.utcnow()
                user.deleted_by = deleted_by
                user.updated_at = datetime.utcnow()
                
            elif delete_type == "hard":
                # 硬删除 - 物理删除记录
                await self._hard_delete_user_data(user_id, db)
                # 注意：这里会在生命周期回调后删除用户记录
                
            else:
                raise ValueError(f"不支持的删除类型: {delete_type}")
            
            # 生命周期回调
            await self.lifecycle_manager.on_user_deleted(
                user_id, tenant_id, delete_type, deleted_by
            )
            
            # 记录删除事件
            await self._log_user_event(
                user_id, "user_deleted",
                {
                    "deleted_by": deleted_by,
                    "delete_type": delete_type,
                    "tenant_id": tenant_id
                },
                db
            )
            
            # 硬删除时移除用户记录
            if delete_type == "hard":
                await db.delete(user)
            
            await db.commit()
            
            logger.info(f"用户删除成功: {user.email} (类型: {delete_type})")
            
            return {
                "success": True,
                "message": f"用户{delete_type}删除成功",
                "user_id": user_id,
                "delete_type": delete_type,
                "deleted_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            await db.rollback()
            logger.error(f"用户删除失败: {e}")
            raise
    
    async def get_user_by_id(
        self,
        user_id: str,
        tenant_id: Optional[str] = None,
        include_profile: bool = False,
        include_activity: bool = False,
        db: AsyncSession = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取用户详细信息
        
        Args:
            user_id: 用户ID
            tenant_id: 租户ID
            include_profile: 是否包含用户画像
            include_activity: 是否包含活动统计
            db: 数据库会话
            
        Returns:
            Optional[Dict[str, Any]]: 用户信息或None
        """
        if db is None:
            async with get_db_session() as session:
                return await self._get_user_by_id_impl(
                    user_id, tenant_id, include_profile, include_activity, session
                )
        else:
            return await self._get_user_by_id_impl(
                user_id, tenant_id, include_profile, include_activity, db
            )
    
    async def _get_user_by_id_impl(
        self,
        user_id: str,
        tenant_id: Optional[str],
        include_profile: bool,
        include_activity: bool,
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """获取用户信息实现"""
        try:
            user = await self._get_user_by_id_and_tenant(user_id, tenant_id, db)
            if not user:
                return None
            
            user_data = {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "phone": user.phone,
                "avatar_url": user.avatar_url,
                "bio": user.bio,
                "status": user.status.value,
                "email_verified": user.email_verified,
                "phone_verified": user.phone_verified,
                "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                "activated_at": user.activated_at.isoformat() if user.activated_at else None,
                "tenant_id": user.tenant_id
            }
            
            # 包含用户画像
            if include_profile:
                # 这里应该调用profile服务，暂时留空
                user_data["profile"] = await self._get_user_profile(user_id, db)
            
            # 包含活动统计
            if include_activity:
                # 这里应该调用activity服务，暂时留空
                user_data["activity"] = await self._get_user_activity_summary(user_id, db)
            
            return user_data
            
        except Exception as e:
            logger.error(f"获取用户信息失败: {e}")
            return None
    
    async def search_users(
        self,
        tenant_id: str,
        query: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        搜索用户
        
        Args:
            tenant_id: 租户ID
            query: 搜索查询
            status: 状态过滤
            limit: 每页数量
            offset: 偏移量
            sort_by: 排序字段
            sort_order: 排序方向
            db: 数据库会话
            
        Returns:
            Dict[str, Any]: 搜索结果
        """
        if db is None:
            async with get_db_session() as session:
                return await self._search_users_impl(
                    tenant_id, query, status, limit, offset, sort_by, sort_order, session
                )
        else:
            return await self._search_users_impl(
                tenant_id, query, status, limit, offset, sort_by, sort_order, db
            )
    
    async def _search_users_impl(
        self,
        tenant_id: str,
        query: Optional[str],
        status: Optional[str],
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """用户搜索实现"""
        try:
            # 构建查询条件
            conditions = [User.tenant_id == tenant_id]
            
            if query:
                query_condition = or_(
                    User.email.ilike(f"%{query}%"),
                    User.name.ilike(f"%{query}%")
                )
                conditions.append(query_condition)
            
            if status:
                try:
                    status_enum = UserStatus(status)
                    conditions.append(User.status == status_enum)
                except ValueError:
                    raise ValueError(f"无效的用户状态: {status}")
            
            # 总数查询
            count_query = select(func.count(User.id)).where(and_(*conditions))
            total_result = await db.execute(count_query)
            total_count = total_result.scalar()
            
            # 数据查询
            query_obj = select(User).where(and_(*conditions))
            
            # 排序
            if hasattr(User, sort_by):
                sort_column = getattr(User, sort_by)
                if sort_order.lower() == "desc":
                    query_obj = query_obj.order_by(sort_column.desc())
                else:
                    query_obj = query_obj.order_by(sort_column)
            
            # 分页
            query_obj = query_obj.limit(limit).offset(offset)
            
            result = await db.execute(query_obj)
            users = result.scalars().all()
            
            # 转换为字典格式
            user_list = []
            for user in users:
                user_list.append({
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "status": user.status.value,
                    "email_verified": user.email_verified,
                    "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
                    "created_at": user.created_at.isoformat(),
                    "avatar_url": user.avatar_url
                })
            
            return {
                "success": True,
                "users": user_list,
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            }
            
        except Exception as e:
            logger.error(f"用户搜索失败: {e}")
            raise
    
    # 私有方法
    async def _handle_existing_user(
        self,
        email: str,
        tenant_id: str,
        created_by: Optional[str],
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """处理已存在用户的情况"""
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            if existing_user.tenant_id == tenant_id:
                raise ValueError("用户已存在于该租户中")
            else:
                # 用户存在于其他租户，可以考虑创建租户关联
                # 这里简化处理，返回错误
                raise ValueError("该邮箱已被其他租户使用")
        
        return None
    
    async def _get_user_by_id_and_tenant(
        self,
        user_id: str,
        tenant_id: Optional[str],
        db: AsyncSession
    ) -> Optional[User]:
        """根据ID和租户获取用户"""
        conditions = [User.id == user_id]
        
        if tenant_id:
            conditions.append(User.tenant_id == tenant_id)
        
        stmt = select(User).where(and_(*conditions))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _create_user_profile(
        self,
        user_id: str,
        user_data: UserCreate,
        db: AsyncSession
    ):
        """创建用户画像（占位符方法）"""
        # 这里应该创建UserProfile记录或调用profile服务
        # 暂时留空，等待profile模块实现
        pass
    
    async def _send_verification_email(
        self,
        user_id: str,
        email: str,
        name: str
    ):
        """发送验证邮件"""
        verification_token = generate_verification_token(user_id)
        await send_verification_email(email, name, verification_token)
    
    async def _verify_activation_token(
        self,
        user_id: str,
        token: str
    ) -> bool:
        """验证激活令牌"""
        return verify_token(token, user_id, "activation", self.verification_expire_hours)
    
    async def _handle_sensitive_field_changes(
        self,
        user: User,
        sensitive_changes: Dict[str, Dict[str, Any]],
        updated_by: Optional[str],
        db: AsyncSession
    ):
        """处理敏感字段变更"""
        # 如果邮箱变更，需要重新验证
        if "email" in sensitive_changes:
            user.email_verified = False
            await self._send_verification_email(
                user.id, user.email, user.name
            )
        
        # 如果电话变更，需要重新验证
        if "phone" in sensitive_changes:
            user.phone_verified = False
            # 这里可以发送手机验证码
    
    async def _anonymize_user_data(self, user: User, db: AsyncSession):
        """匿名化用户数据"""
        timestamp = int(datetime.utcnow().timestamp())
        
        user.email = f"anonymized_{timestamp}@deleted.local"
        user.name = f"已删除用户_{timestamp}"
        user.phone = None
        user.avatar_url = None
        user.bio = None
    
    async def _hard_delete_user_data(self, user_id: str, db: AsyncSession):
        """硬删除用户相关数据"""
        # 这里应该删除用户相关的所有数据
        # 如用户画像、活动记录、通知等
        # 暂时留空，等待各模块实现
        pass
    
    async def _log_user_event(
        self,
        user_id: str,
        event_type: str,
        event_data: Dict[str, Any],
        db: AsyncSession
    ):
        """记录用户事件（占位符方法）"""
        # 这里应该调用activity服务记录事件
        # 或者直接写入user_events表
        pass
    
    async def _get_user_profile(self, user_id: str, db: AsyncSession) -> Dict[str, Any]:
        """获取用户画像（占位符方法）"""
        return {}
    
    async def _get_user_activity_summary(self, user_id: str, db: AsyncSession) -> Dict[str, Any]:
        """获取用户活动摘要（占位符方法）"""
        return {}
    
    async def _check_update_permission(
        self,
        requester_id: str,
        user_id: str,
        tenant_id: Optional[str]
    ):
        """检查更新权限（占位符方法）"""
        # 这里应该调用auth服务检查权限
        # 暂时允许所有操作
        pass

# 全局用户管理器实例
user_manager = UserManager()