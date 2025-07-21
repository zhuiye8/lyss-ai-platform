# Lyss User Service - 用户管理服务

## 📋 服务概述

**lyss-user-service** 是平台的用户管理核心服务，负责用户生命周期管理、用户画像分析、偏好设置和用户活动追踪。该服务从原有的tenant-service中分离出用户管理逻辑，建立清晰的服务边界，采用SQLAlchemy优化并发性能，参考OpenWebUI的用户管理最佳实践。

---

## 🎯 核心功能

### **1. 用户生命周期管理**
- **用户注册**: 邮箱验证、手机验证、邀请注册
- **用户激活**: 邮箱确认、管理员审批、自动激活
- **用户禁用**: 暂时禁用、永久禁用、批量操作
- **用户删除**: 软删除、硬删除、数据匿名化

### **2. 用户画像和偏好**
- **基础画像**: 个人信息、联系方式、头像管理
- **行为画像**: 使用习惯、偏好模型、活跃度分析
- **智能推荐**: 基于使用历史的个性化推荐
- **偏好设置**: 界面主题、语言设置、通知偏好

### **3. 租户关联管理**
- **多租户归属**: 用户可属于多个租户
- **权限继承**: 从租户继承基础权限
- **角色映射**: 租户内角色分配和管理
- **跨租户访问**: 安全的跨租户用户访问

### **4. 用户活动分析**
- **行为追踪**: 登录频率、功能使用、会话时长
- **使用统计**: 模型使用偏好、对话频次、成本统计
- **异常检测**: 异常登录、行为异常、风险评估
- **活跃度评分**: 用户活跃度量化和分级

### **5. 用户关系管理**
- **邀请机制**: 用户邀请、邀请码管理、奖励机制
- **团队协作**: 团队创建、成员管理、协作权限
- **社交功能**: 用户关注、分享、评价反馈
- **通知系统**: 站内信、邮件通知、推送消息

---

## 🏗️ 技术架构

### **架构设计图**
```
┌─────────────────────────────────────────────────────────┐
│                    API Gateway                          │
│                 (用户请求路由)                            │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│                User Service                             │
│  ┌─────────────────┬─────────────────┬─────────────────┐ │
│  │  User Manager   │ Profile Manager │ Activity Tracker │ │
│  │   ·生命周期      │   ·用户画像     │   ·行为分析      │ │
│  │   ·基础信息      │   ·偏好设置     │   ·统计报告      │ │
│  │   ·状态管理      │   ·个性化推荐   │   ·异常检测      │ │
│  └─────────────────┼─────────────────┼─────────────────┘ │
└──────────────────┬─┴─────────────────┴─┬─────────────────┘
                   │                     │
    ┌──────────────▼──────────────┐ ┌───▼──────────────┐
    │    User Database            │ │  Analytics DB    │
    │  ·用户基础信息               │ │  ·行为数据       │
    │  ·偏好配置                  │ │  ·使用统计       │
    │  ·关系数据                  │ │  ·活跃度分析     │
    │  ·审计日志                  │ │  ·个性化数据     │
    └─────────────────────────────┘ └─────────────────┘
```

### **核心模块架构**

```python
# 服务架构概览
lyss-user-service/
├── main.py                     # FastAPI应用入口
├── app/
│   ├── __init__.py
│   ├── core/                   # 核心配置
│   │   ├── config.py          # 服务配置
│   │   ├── database.py        # 数据库配置
│   │   ├── security.py        # 安全配置
│   │   └── cache.py           # 缓存配置
│   ├── users/                  # 用户管理
│   │   ├── __init__.py
│   │   ├── manager.py         # 用户管理器
│   │   ├── lifecycle.py       # 生命周期管理
│   │   ├── validator.py       # 用户数据验证
│   │   └── repository.py      # 数据访问层
│   ├── profiles/               # 用户画像
│   │   ├── __init__.py
│   │   ├── manager.py         # 画像管理器
│   │   ├── analyzer.py        # 行为分析器
│   │   ├── recommender.py     # 推荐引擎
│   │   └── preferences.py     # 偏好管理
│   ├── activities/             # 活动追踪
│   │   ├── __init__.py
│   │   ├── tracker.py         # 活动追踪器
│   │   ├── analyzer.py        # 活动分析器
│   │   ├── detector.py        # 异常检测器
│   │   └── reporter.py        # 报告生成器
│   ├── relationships/          # 用户关系
│   │   ├── __init__.py
│   │   ├── manager.py         # 关系管理器
│   │   ├── invitations.py     # 邀请管理
│   │   ├── teams.py           # 团队管理
│   │   └── social.py          # 社交功能
│   ├── notifications/          # 通知系统
│   │   ├── __init__.py
│   │   ├── manager.py         # 通知管理器
│   │   ├── channels.py        # 通知渠道
│   │   ├── templates.py       # 消息模板
│   │   └── scheduler.py       # 定时任务
│   ├── models/                 # 数据模型
│   │   ├── __init__.py
│   │   ├── user.py           # 用户模型
│   │   ├── profile.py        # 画像模型
│   │   ├── activity.py       # 活动模型
│   │   └── relationship.py   # 关系模型
│   ├── api/                   # API接口
│   │   ├── __init__.py
│   │   ├── v1/               # V1版本API
│   │   │   ├── users.py      # 用户管理API
│   │   │   ├── profiles.py   # 用户画像API
│   │   │   ├── activities.py # 活动统计API
│   │   │   └── relationships.py # 关系管理API
│   │   └── middleware.py      # 中间件
│   ├── services/              # 业务服务
│   │   ├── __init__.py
│   │   ├── user_service.py   # 用户服务
│   │   ├── profile_service.py # 画像服务
│   │   ├── activity_service.py # 活动服务
│   │   └── notification_service.py # 通知服务
│   └── utils/                 # 工具类
│       ├── __init__.py
│       ├── email.py          # 邮件工具
│       ├── avatar.py         # 头像工具
│       ├── analytics.py      # 分析工具
│       └── validators.py     # 验证工具
├── config/                    # 配置文件
│   ├── notification_templates/ # 通知模板
│   └── user_settings.yaml    # 用户设置配置
├── tests/                     # 测试
│   ├── test_users.py
│   ├── test_profiles.py
│   ├── test_activities.py
│   └── test_relationships.py
├── requirements.txt           # 依赖
├── Dockerfile                # Docker配置
└── README.md                 # 服务文档
```

---

## 💻 核心实现

### **1. 用户管理器**

```python
# app/users/manager.py
from typing import Optional, Dict, Any, List
import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_
import logging
from ..models.user import User, UserCreate, UserUpdate, UserStatus
from ..core.database import get_async_db
from ..utils.email import send_verification_email
from ..utils.validators import validate_email, validate_phone
from ..services.notification_service import notification_service

logger = logging.getLogger(__name__)

class UserManager:
    """用户管理器 - 核心用户管理逻辑"""
    
    def __init__(self):
        self.verification_expire_hours = 24
        self.inactive_threshold_days = 90
        
    async def create_user(
        self,
        user_data: UserCreate,
        tenant_id: str,
        created_by: str = None,
        auto_activate: bool = False
    ) -> Dict[str, Any]:
        """创建新用户"""
        async with get_async_db() as db:
            try:
                # 1. 数据验证
                await self._validate_user_data(user_data, db)
                
                # 2. 检查用户是否已存在
                existing_user = await self._get_user_by_email(user_data.email, db)
                if existing_user:
                    if existing_user.tenant_id == tenant_id:
                        raise ValueError("用户已存在于该租户中")
                    else:
                        # 用户存在于其他租户，创建租户关联
                        return await self._add_user_to_tenant(
                            existing_user.id, tenant_id, created_by
                        )
                
                # 3. 创建用户记录
                user_id = str(uuid.uuid4())
                new_user = User(
                    id=user_id,
                    email=user_data.email,
                    name=user_data.name,
                    phone=user_data.phone,
                    avatar_url=user_data.avatar_url,
                    tenant_id=tenant_id,
                    status=UserStatus.ACTIVE if auto_activate else UserStatus.PENDING,
                    email_verified=auto_activate,
                    created_by=created_by,
                    created_at=datetime.utcnow()
                )
                
                db.add(new_user)
                await db.flush()
                
                # 4. 创建用户画像
                await self._create_user_profile(user_id, user_data, db)
                
                # 5. 发送验证邮件（如果需要）
                if not auto_activate:
                    verification_token = await self._create_verification_token(user_id)
                    await send_verification_email(
                        user_data.email,
                        user_data.name,
                        verification_token
                    )
                
                # 6. 记录用户创建事件
                await self._log_user_event(
                    user_id, "user_created", 
                    {"created_by": created_by, "auto_activate": auto_activate}
                )
                
                await db.commit()
                
                logger.info(f"成功创建用户: {user_data.email} (ID: {user_id})")
                
                return {
                    "user_id": user_id,
                    "email": user_data.email,
                    "status": new_user.status.value,
                    "requires_verification": not auto_activate
                }
                
            except Exception as e:
                await db.rollback()
                logger.error(f"用户创建失败: {e}")
                raise
    
    async def activate_user(
        self,
        user_id: str,
        verification_token: str = None,
        activated_by: str = None
    ) -> bool:
        """激活用户"""
        async with get_async_db() as db:
            try:
                # 1. 获取用户信息
                user = await self._get_user_by_id(user_id, db)
                if not user:
                    raise ValueError("用户不存在")
                
                # 2. 检查用户状态
                if user.status == UserStatus.ACTIVE:
                    return True  # 已经激活
                
                if user.status == UserStatus.BANNED:
                    raise ValueError("用户已被禁用，无法激活")
                
                # 3. 验证令牌（如果提供）
                if verification_token:
                    token_valid = await self._verify_activation_token(
                        user_id, verification_token
                    )
                    if not token_valid:
                        raise ValueError("验证令牌无效或已过期")
                
                # 4. 激活用户
                user.status = UserStatus.ACTIVE
                user.email_verified = True
                user.activated_at = datetime.utcnow()
                user.activated_by = activated_by
                
                # 5. 发送欢迎通知
                await notification_service.send_welcome_notification(user_id)
                
                # 6. 记录激活事件
                await self._log_user_event(
                    user_id, "user_activated",
                    {"activated_by": activated_by, "method": "email" if verification_token else "admin"}
                )
                
                await db.commit()
                
                logger.info(f"用户激活成功: {user.email}")
                return True
                
            except Exception as e:
                await db.rollback()
                logger.error(f"用户激活失败: {e}")
                raise
    
    async def update_user(
        self,
        user_id: str,
        update_data: UserUpdate,
        updated_by: str = None,
        tenant_id: str = None
    ) -> Optional[User]:
        """更新用户信息"""
        async with get_async_db() as db:
            try:
                # 1. 获取用户
                user = await self._get_user_by_id_and_tenant(user_id, tenant_id, db)
                if not user:
                    raise ValueError("用户不存在")
                
                # 2. 权限检查
                if updated_by and updated_by != user_id:
                    # 管理员更新，需要权限验证
                    await self._check_update_permission(updated_by, user_id, tenant_id)
                
                # 3. 数据验证
                update_dict = update_data.dict(exclude_unset=True)
                if "email" in update_dict:
                    await self._validate_email_unique(update_dict["email"], user_id, db)
                
                # 4. 敏感字段处理
                sensitive_fields = ["email", "phone"]
                sensitive_changes = {}
                
                for field in sensitive_fields:
                    if field in update_dict and getattr(user, field) != update_dict[field]:
                        sensitive_changes[field] = {
                            "old": getattr(user, field),
                            "new": update_dict[field]
                        }
                
                # 5. 更新用户信息
                for field, value in update_dict.items():
                    if hasattr(user, field):
                        setattr(user, field, value)
                
                user.updated_at = datetime.utcnow()
                user.updated_by = updated_by
                
                # 6. 处理敏感字段变更
                if sensitive_changes:
                    await self._handle_sensitive_field_changes(
                        user, sensitive_changes, updated_by
                    )
                
                # 7. 记录更新事件
                await self._log_user_event(
                    user_id, "user_updated",
                    {
                        "updated_by": updated_by,
                        "fields": list(update_dict.keys()),
                        "sensitive_changes": bool(sensitive_changes)
                    }
                )
                
                await db.commit()
                
                logger.info(f"用户信息更新成功: {user.email}")
                return user
                
            except Exception as e:
                await db.rollback()
                logger.error(f"用户信息更新失败: {e}")
                raise
    
    async def deactivate_user(
        self,
        user_id: str,
        reason: str = None,
        deactivated_by: str = None,
        tenant_id: str = None
    ) -> bool:
        """停用用户"""
        async with get_async_db() as db:
            try:
                user = await self._get_user_by_id_and_tenant(user_id, tenant_id, db)
                if not user:
                    raise ValueError("用户不存在")
                
                if user.status == UserStatus.INACTIVE:
                    return True  # 已经停用
                
                # 更新用户状态
                user.status = UserStatus.INACTIVE
                user.deactivated_at = datetime.utcnow()
                user.deactivated_by = deactivated_by
                user.deactivation_reason = reason
                
                # 撤销用户会话
                await self._revoke_user_sessions(user_id)
                
                # 发送停用通知
                await notification_service.send_deactivation_notification(
                    user_id, reason
                )
                
                # 记录停用事件
                await self._log_user_event(
                    user_id, "user_deactivated",
                    {
                        "deactivated_by": deactivated_by,
                        "reason": reason
                    }
                )
                
                await db.commit()
                
                logger.info(f"用户停用成功: {user.email}")
                return True
                
            except Exception as e:
                await db.rollback()
                logger.error(f"用户停用失败: {e}")
                raise
    
    async def delete_user(
        self,
        user_id: str,
        delete_type: str = "soft",  # "soft", "hard", "anonymize"
        deleted_by: str = None,
        tenant_id: str = None
    ) -> bool:
        """删除用户"""
        async with get_async_db() as db:
            try:
                user = await self._get_user_by_id_and_tenant(user_id, tenant_id, db)
                if not user:
                    raise ValueError("用户不存在")
                
                if delete_type == "soft":
                    # 软删除 - 标记为已删除
                    user.status = UserStatus.DELETED
                    user.deleted_at = datetime.utcnow()
                    user.deleted_by = deleted_by
                    
                elif delete_type == "anonymize":
                    # 数据匿名化
                    await self._anonymize_user_data(user, db)
                    user.status = UserStatus.ANONYMIZED
                    user.deleted_at = datetime.utcnow()
                    user.deleted_by = deleted_by
                    
                elif delete_type == "hard":
                    # 硬删除 - 物理删除记录
                    await self._hard_delete_user_data(user_id, db)
                    await db.delete(user)
                    
                else:
                    raise ValueError(f"不支持的删除类型: {delete_type}")
                
                # 撤销所有会话
                await self._revoke_user_sessions(user_id)
                
                # 记录删除事件
                await self._log_user_event(
                    user_id, "user_deleted",
                    {
                        "deleted_by": deleted_by,
                        "delete_type": delete_type
                    }
                )
                
                await db.commit()
                
                logger.info(f"用户删除成功: {user.email} (类型: {delete_type})")
                return True
                
            except Exception as e:
                await db.rollback()
                logger.error(f"用户删除失败: {e}")
                raise
    
    async def get_user_by_id(
        self,
        user_id: str,
        tenant_id: str = None,
        include_profile: bool = False,
        include_activity: bool = False
    ) -> Optional[Dict[str, Any]]:
        """获取用户详细信息"""
        async with get_async_db() as db:
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
                    "status": user.status.value,
                    "email_verified": user.email_verified,
                    "last_login_at": user.last_login_at,
                    "created_at": user.created_at,
                    "updated_at": user.updated_at
                }
                
                # 包含用户画像
                if include_profile:
                    from ..services.profile_service import profile_service
                    profile_data = await profile_service.get_user_profile(user_id)
                    user_data["profile"] = profile_data
                
                # 包含活动统计
                if include_activity:
                    from ..services.activity_service import activity_service
                    activity_data = await activity_service.get_user_activity_summary(user_id)
                    user_data["activity"] = activity_data
                
                return user_data
                
            except Exception as e:
                logger.error(f"获取用户信息失败: {e}")
                return None
    
    async def search_users(
        self,
        tenant_id: str,
        query: str = None,
        status: str = None,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """搜索用户"""
        async with get_async_db() as db:
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
                    conditions.append(User.status == UserStatus(status))
                
                # 执行查询
                from sqlalchemy import select, func
                
                # 总数查询
                count_query = select(func.count(User.id)).where(and_(*conditions))
                total_result = await db.execute(count_query)
                total_count = total_result.scalar()
                
                # 数据查询
                query_obj = select(User).where(and_(*conditions))
                
                # 排序
                if sort_order.lower() == "desc":
                    query_obj = query_obj.order_by(getattr(User, sort_by).desc())
                else:
                    query_obj = query_obj.order_by(getattr(User, sort_by))
                
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
                        "last_login_at": user.last_login_at,
                        "created_at": user.created_at
                    })
                
                return {
                    "users": user_list,
                    "total": total_count,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + limit < total_count
                }
                
            except Exception as e:
                logger.error(f"用户搜索失败: {e}")
                raise
    
    async def _validate_user_data(self, user_data: UserCreate, db: AsyncSession):
        """验证用户数据"""
        # 邮箱格式验证
        if not validate_email(user_data.email):
            raise ValueError("邮箱格式不正确")
        
        # 手机号格式验证（如果提供）
        if user_data.phone and not validate_phone(user_data.phone):
            raise ValueError("手机号格式不正确")
        
        # 用户名长度验证
        if len(user_data.name.strip()) < 2:
            raise ValueError("用户名至少需要2个字符")
    
    async def _create_user_profile(self, user_id: str, user_data: UserCreate, db: AsyncSession):
        """创建用户画像"""
        from ..models.profile import UserProfile
        
        profile = UserProfile(
            user_id=user_id,
            display_name=user_data.name,
            bio=user_data.bio or "",
            preferences={
                "language": "zh-CN",
                "theme": "light",
                "timezone": "Asia/Shanghai",
                "notification_enabled": True
            },
            created_at=datetime.utcnow()
        )
        
        db.add(profile)
    
    async def _log_user_event(self, user_id: str, event_type: str, event_data: Dict[str, Any]):
        """记录用户事件"""
        from ..models.activity import UserEvent
        
        async with get_async_db() as db:
            event = UserEvent(
                user_id=user_id,
                event_type=event_type,
                event_data=event_data,
                created_at=datetime.utcnow()
            )
            
            db.add(event)
            await db.commit()

# 全局用户管理器实例
user_manager = UserManager()
```

### **2. 用户画像分析器**

```python
# app/profiles/analyzer.py
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
from sqlalchemy import select, func, and_
from ..models.activity import UserActivity, ConversationSession
from ..models.profile import UserProfile, UserPreferences
from ..core.database import get_async_db
from ..utils.analytics import calculate_user_segments, analyze_behavior_patterns

class UserProfileAnalyzer:
    """用户画像分析器"""
    
    def __init__(self):
        self.analysis_periods = {
            "daily": 1,
            "weekly": 7,
            "monthly": 30,
            "quarterly": 90
        }
    
    async def analyze_user_behavior(
        self,
        user_id: str,
        period: str = "monthly"
    ) -> Dict[str, Any]:
        """分析用户行为模式"""
        async with get_async_db() as db:
            try:
                days = self.analysis_periods.get(period, 30)
                start_date = datetime.utcnow() - timedelta(days=days)
                
                # 1. 基础活动统计
                activity_stats = await self._get_activity_statistics(
                    user_id, start_date, db
                )
                
                # 2. 模型使用分析
                model_usage = await self._analyze_model_usage(
                    user_id, start_date, db
                )
                
                # 3. 对话模式分析
                conversation_patterns = await self._analyze_conversation_patterns(
                    user_id, start_date, db
                )
                
                # 4. 活跃时段分析
                active_hours = await self._analyze_active_hours(
                    user_id, start_date, db
                )
                
                # 5. 功能偏好分析
                feature_preferences = await self._analyze_feature_usage(
                    user_id, start_date, db
                )
                
                # 6. 生成用户标签
                user_tags = await self._generate_user_tags(
                    activity_stats, model_usage, conversation_patterns
                )
                
                return {
                    "user_id": user_id,
                    "analysis_period": period,
                    "analyzed_at": datetime.utcnow().isoformat(),
                    "activity_stats": activity_stats,
                    "model_usage": model_usage,
                    "conversation_patterns": conversation_patterns,
                    "active_hours": active_hours,
                    "feature_preferences": feature_preferences,
                    "user_tags": user_tags,
                    "engagement_score": self._calculate_engagement_score(
                        activity_stats, conversation_patterns
                    )
                }
                
            except Exception as e:
                logger.error(f"用户行为分析失败: {e}")
                raise
    
    async def update_user_preferences(
        self,
        user_id: str,
        preference_updates: Dict[str, Any]
    ) -> bool:
        """更新用户偏好设置"""
        async with get_async_db() as db:
            try:
                # 获取用户画像
                profile_query = select(UserProfile).where(
                    UserProfile.user_id == user_id
                )
                result = await db.execute(profile_query)
                profile = result.scalar_one_or_none()
                
                if not profile:
                    raise ValueError("用户画像不存在")
                
                # 更新偏好设置
                current_prefs = profile.preferences or {}
                
                # 验证偏好设置
                validated_prefs = await self._validate_preferences(
                    preference_updates
                )
                
                # 合并偏好设置
                current_prefs.update(validated_prefs)
                profile.preferences = current_prefs
                profile.updated_at = datetime.utcnow()
                
                # 记录偏好变更
                await self._log_preference_change(
                    user_id, validated_prefs
                )
                
                await db.commit()
                
                logger.info(f"用户偏好更新成功: {user_id}")
                return True
                
            except Exception as e:
                await db.rollback()
                logger.error(f"用户偏好更新失败: {e}")
                raise
    
    async def get_personalized_recommendations(
        self,
        user_id: str,
        recommendation_type: str = "models"
    ) -> List[Dict[str, Any]]:
        """获取个性化推荐"""
        try:
            # 获取用户行为分析
            behavior_analysis = await self.analyze_user_behavior(user_id)
            
            if recommendation_type == "models":
                return await self._recommend_models(user_id, behavior_analysis)
            elif recommendation_type == "features":
                return await self._recommend_features(user_id, behavior_analysis)
            elif recommendation_type == "settings":
                return await self._recommend_settings(user_id, behavior_analysis)
            else:
                raise ValueError(f"不支持的推荐类型: {recommendation_type}")
                
        except Exception as e:
            logger.error(f"个性化推荐生成失败: {e}")
            return []
    
    async def generate_user_insights(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """生成用户洞察报告"""
        try:
            # 多周期行为分析
            weekly_analysis = await self.analyze_user_behavior(user_id, "weekly")
            monthly_analysis = await self.analyze_user_behavior(user_id, "monthly")
            quarterly_analysis = await self.analyze_user_behavior(user_id, "quarterly")
            
            # 趋势分析
            trends = await self._analyze_user_trends(
                user_id, [weekly_analysis, monthly_analysis, quarterly_analysis]
            )
            
            # 同类用户比较
            peer_comparison = await self._compare_with_peer_users(
                user_id, monthly_analysis
            )
            
            # 改进建议
            improvement_suggestions = await self._generate_improvement_suggestions(
                user_id, monthly_analysis, trends
            )
            
            return {
                "user_id": user_id,
                "generated_at": datetime.utcnow().isoformat(),
                "current_period": monthly_analysis,
                "trends": trends,
                "peer_comparison": peer_comparison,
                "improvement_suggestions": improvement_suggestions,
                "insights_summary": await self._generate_insights_summary(
                    monthly_analysis, trends, peer_comparison
                )
            }
            
        except Exception as e:
            logger.error(f"用户洞察生成失败: {e}")
            raise
    
    async def _get_activity_statistics(
        self,
        user_id: str,
        start_date: datetime,
        db
    ) -> Dict[str, Any]:
        """获取活动统计"""
        # 总会话数
        session_count_query = select(func.count(ConversationSession.id)).where(
            and_(
                ConversationSession.user_id == user_id,
                ConversationSession.created_at >= start_date
            )
        )
        session_result = await db.execute(session_count_query)
        total_sessions = session_result.scalar() or 0
        
        # 总消息数
        activity_count_query = select(func.count(UserActivity.id)).where(
            and_(
                UserActivity.user_id == user_id,
                UserActivity.activity_type == "chat_message",
                UserActivity.created_at >= start_date
            )
        )
        activity_result = await db.execute(activity_count_query)
        total_messages = activity_result.scalar() or 0
        
        # 平均会话时长
        avg_duration_query = select(
            func.avg(ConversationSession.duration_minutes)
        ).where(
            and_(
                ConversationSession.user_id == user_id,
                ConversationSession.created_at >= start_date,
                ConversationSession.duration_minutes.isnot(None)
            )
        )
        duration_result = await db.execute(avg_duration_query)
        avg_session_duration = duration_result.scalar() or 0
        
        # 活跃天数
        active_days_query = select(
            func.count(func.distinct(func.date(UserActivity.created_at)))
        ).where(
            and_(
                UserActivity.user_id == user_id,
                UserActivity.created_at >= start_date
            )
        )
        days_result = await db.execute(active_days_query)
        active_days = days_result.scalar() or 0
        
        return {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "avg_session_duration": float(avg_session_duration),
            "active_days": active_days,
            "avg_sessions_per_day": total_sessions / max(active_days, 1),
            "avg_messages_per_session": total_messages / max(total_sessions, 1)
        }
    
    async def _analyze_model_usage(
        self,
        user_id: str,
        start_date: datetime,
        db
    ) -> Dict[str, Any]:
        """分析模型使用情况"""
        # 模型使用统计
        model_usage_query = select(
            UserActivity.metadata['model'].astext.label('model_name'),
            func.count(UserActivity.id).label('usage_count'),
            func.sum(UserActivity.metadata['tokens_used'].astext.cast(db.Integer)).label('total_tokens')
        ).where(
            and_(
                UserActivity.user_id == user_id,
                UserActivity.activity_type == "model_usage",
                UserActivity.created_at >= start_date
            )
        ).group_by(UserActivity.metadata['model'].astext)
        
        result = await db.execute(model_usage_query)
        model_stats = result.fetchall()
        
        model_usage = {}
        total_usage = 0
        
        for stat in model_stats:
            model_name = stat.model_name
            usage_count = stat.usage_count
            total_tokens = stat.total_tokens or 0
            total_usage += usage_count
            
            model_usage[model_name] = {
                "usage_count": usage_count,
                "total_tokens": total_tokens,
                "percentage": 0  # 将在下面计算
            }
        
        # 计算使用比例
        for model_name in model_usage:
            model_usage[model_name]["percentage"] = (
                model_usage[model_name]["usage_count"] / max(total_usage, 1) * 100
            )
        
        # 找出最喜欢的模型
        favorite_model = max(
            model_usage.items(),
            key=lambda x: x[1]["usage_count"],
            default=(None, {"usage_count": 0})
        )
        
        return {
            "model_usage": model_usage,
            "favorite_model": favorite_model[0],
            "total_model_calls": total_usage,
            "unique_models_used": len(model_usage)
        }
    
    async def _analyze_conversation_patterns(
        self,
        user_id: str,
        start_date: datetime,
        db
    ) -> Dict[str, Any]:
        """分析对话模式"""
        # 对话主题分析
        topic_query = select(
            ConversationSession.metadata['topic'].astext.label('topic'),
            func.count(ConversationSession.id).label('count')
        ).where(
            and_(
                ConversationSession.user_id == user_id,
                ConversationSession.created_at >= start_date,
                ConversationSession.metadata['topic'].astext.isnot(None)
            )
        ).group_by(ConversationSession.metadata['topic'].astext)
        
        topic_result = await db.execute(topic_query)
        topic_stats = topic_result.fetchall()
        
        topics = {}
        for stat in topic_stats:
            topics[stat.topic] = stat.count
        
        # 对话长度分析
        length_query = select(
            ConversationSession.message_count,
            func.count(ConversationSession.id).label('session_count')
        ).where(
            and_(
                ConversationSession.user_id == user_id,
                ConversationSession.created_at >= start_date,
                ConversationSession.message_count.isnot(None)
            )
        ).group_by(ConversationSession.message_count)
        
        length_result = await db.execute(length_query)
        length_stats = length_result.fetchall()
        
        # 计算对话长度分布
        length_distribution = {
            "short": 0,    # 1-5 messages
            "medium": 0,   # 6-20 messages
            "long": 0      # 21+ messages
        }
        
        for stat in length_stats:
            message_count = stat.message_count
            session_count = stat.session_count
            
            if message_count <= 5:
                length_distribution["short"] += session_count
            elif message_count <= 20:
                length_distribution["medium"] += session_count
            else:
                length_distribution["long"] += session_count
        
        return {
            "popular_topics": dict(sorted(topics.items(), key=lambda x: x[1], reverse=True)[:10]),
            "conversation_length_distribution": length_distribution,
            "avg_messages_per_conversation": sum(
                stat.message_count * stat.session_count for stat in length_stats
            ) / max(sum(stat.session_count for stat in length_stats), 1)
        }
    
    def _calculate_engagement_score(
        self,
        activity_stats: Dict[str, Any],
        conversation_patterns: Dict[str, Any]
    ) -> float:
        """计算用户参与度评分 (0-100)"""
        try:
            # 基础活跃度权重
            activity_score = min(activity_stats["active_days"] * 3, 30)  # 最多30分
            
            # 会话质量权重
            avg_duration = activity_stats["avg_session_duration"]
            duration_score = min(avg_duration / 10 * 20, 20)  # 最多20分
            
            # 对话深度权重
            avg_messages = conversation_patterns["avg_messages_per_conversation"]
            depth_score = min(avg_messages / 5 * 25, 25)  # 最多25分
            
            # 一致性权重
            sessions_per_day = activity_stats["avg_sessions_per_day"]
            consistency_score = min(sessions_per_day * 10, 25)  # 最多25分
            
            total_score = activity_score + duration_score + depth_score + consistency_score
            return round(min(total_score, 100), 2)
            
        except Exception as e:
            logger.error(f"参与度评分计算失败: {e}")
            return 0.0

# 全局用户画像分析器实例
profile_analyzer = UserProfileAnalyzer()
```

### **3. 活动追踪器**

```python
# app/activities/tracker.py
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import asyncio
from sqlalchemy import select, func, and_, or_
from ..models.activity import UserActivity, ActivityType
from ..core.database import get_async_db
from ..core.cache import redis_client

class UserActivityTracker:
    """用户活动追踪器"""
    
    def __init__(self):
        self.batch_size = 100
        self.flush_interval = 30  # 秒
        self.activity_buffer = []
        self.buffer_lock = asyncio.Lock()
        
    async def track_activity(
        self,
        user_id: str,
        activity_type: str,
        metadata: Dict[str, Any] = None,
        tenant_id: str = None,
        ip_address: str = None,
        user_agent: str = None
    ):
        """记录用户活动"""
        try:
            activity_data = {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "activity_type": activity_type,
                "metadata": metadata or {},
                "ip_address": ip_address,
                "user_agent": user_agent,
                "created_at": datetime.utcnow()
            }
            
            # 添加到缓冲区
            async with self.buffer_lock:
                self.activity_buffer.append(activity_data)
                
                # 如果缓冲区满了，立即刷新
                if len(self.activity_buffer) >= self.batch_size:
                    await self._flush_activities()
            
            # 实时更新Redis缓存
            await self._update_activity_cache(user_id, activity_type, metadata)
            
        except Exception as e:
            logger.error(f"活动追踪失败: {e}")
    
    async def track_login(
        self,
        user_id: str,
        tenant_id: str,
        login_method: str = "local",
        ip_address: str = None,
        user_agent: str = None,
        success: bool = True
    ):
        """追踪登录活动"""
        await self.track_activity(
            user_id=user_id,
            activity_type="login",
            metadata={
                "method": login_method,
                "success": success,
                "timestamp": datetime.utcnow().isoformat()
            },
            tenant_id=tenant_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    async def track_chat_message(
        self,
        user_id: str,
        tenant_id: str,
        session_id: str,
        model: str,
        tokens_used: int = 0,
        response_time: float = 0.0
    ):
        """追踪聊天消息"""
        await self.track_activity(
            user_id=user_id,
            activity_type="chat_message",
            metadata={
                "session_id": session_id,
                "model": model,
                "tokens_used": tokens_used,
                "response_time": response_time
            },
            tenant_id=tenant_id
        )
    
    async def track_model_usage(
        self,
        user_id: str,
        tenant_id: str,
        model: str,
        provider: str,
        tokens_used: int,
        cost: float = 0.0
    ):
        """追踪模型使用"""
        await self.track_activity(
            user_id=user_id,
            activity_type="model_usage",
            metadata={
                "model": model,
                "provider": provider,
                "tokens_used": tokens_used,
                "cost": cost
            },
            tenant_id=tenant_id
        )
    
    async def track_feature_usage(
        self,
        user_id: str,
        tenant_id: str,
        feature: str,
        action: str,
        metadata: Dict[str, Any] = None
    ):
        """追踪功能使用"""
        await self.track_activity(
            user_id=user_id,
            activity_type="feature_usage",
            metadata={
                "feature": feature,
                "action": action,
                **(metadata or {})
            },
            tenant_id=tenant_id
        )
    
    async def get_user_activity_summary(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """获取用户活动摘要"""
        async with get_async_db() as db:
            try:
                start_date = datetime.utcnow() - timedelta(days=days)
                
                # 基础统计
                basic_stats = await self._get_basic_activity_stats(user_id, start_date, db)
                
                # 每日活动分布
                daily_distribution = await self._get_daily_activity_distribution(user_id, start_date, db)
                
                # 活动类型统计
                activity_types = await self._get_activity_type_stats(user_id, start_date, db)
                
                # 最近活动
                recent_activities = await self._get_recent_activities(user_id, limit=10, db=db)
                
                # 活跃时段分析
                hourly_pattern = await self._get_hourly_activity_pattern(user_id, start_date, db)
                
                return {
                    "user_id": user_id,
                    "period_days": days,
                    "summary_generated_at": datetime.utcnow().isoformat(),
                    "basic_stats": basic_stats,
                    "daily_distribution": daily_distribution,
                    "activity_types": activity_types,
                    "recent_activities": recent_activities,
                    "hourly_pattern": hourly_pattern
                }
                
            except Exception as e:
                logger.error(f"获取用户活动摘要失败: {e}")
                raise
    
    async def detect_unusual_activity(
        self,
        user_id: str,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """检测异常活动"""
        try:
            start_time = datetime.utcnow() - timedelta(hours=hours)
            
            anomalies = []
            
            # 检测异常登录
            login_anomalies = await self._detect_login_anomalies(user_id, start_time)
            anomalies.extend(login_anomalies)
            
            # 检测异常使用模式
            usage_anomalies = await self._detect_usage_anomalies(user_id, start_time)
            anomalies.extend(usage_anomalies)
            
            # 检测地理位置异常
            location_anomalies = await self._detect_location_anomalies(user_id, start_time)
            anomalies.extend(location_anomalies)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"异常活动检测失败: {e}")
            return []
    
    async def _flush_activities(self):
        """刷新活动缓冲区到数据库"""
        if not self.activity_buffer:
            return
        
        async with get_async_db() as db:
            try:
                activities_to_insert = self.activity_buffer.copy()
                self.activity_buffer.clear()
                
                # 批量插入活动记录
                for activity_data in activities_to_insert:
                    activity = UserActivity(**activity_data)
                    db.add(activity)
                
                await db.commit()
                
                logger.debug(f"成功写入 {len(activities_to_insert)} 条活动记录")
                
            except Exception as e:
                await db.rollback()
                logger.error(f"活动记录写入失败: {e}")
                
                # 将失败的记录重新加入缓冲区
                async with self.buffer_lock:
                    self.activity_buffer.extend(activities_to_insert)
    
    async def _update_activity_cache(
        self,
        user_id: str,
        activity_type: str,
        metadata: Dict[str, Any] = None
    ):
        """更新活动缓存"""
        try:
            today = datetime.utcnow().strftime("%Y-%m-%d")
            
            # 更新每日活动计数
            daily_key = f"user_activity:{user_id}:{today}"
            await redis_client.hincrby(daily_key, activity_type, 1)
            await redis_client.expire(daily_key, 86400 * 7)  # 7天过期
            
            # 更新实时活动状态
            status_key = f"user_status:{user_id}"
            status_data = {
                "last_activity": datetime.utcnow().isoformat(),
                "last_activity_type": activity_type
            }
            await redis_client.hmset(status_key, status_data)
            await redis_client.expire(status_key, 3600)  # 1小时过期
            
            # 如果是聊天消息，更新会话信息
            if activity_type == "chat_message" and metadata:
                session_key = f"chat_session:{metadata.get('session_id')}"
                session_data = {
                    "last_message_at": datetime.utcnow().isoformat(),
                    "message_count": await redis_client.hincrby(session_key, "message_count", 1)
                }
                await redis_client.hmset(session_key, session_data)
                await redis_client.expire(session_key, 86400)  # 24小时过期
                
        except Exception as e:
            logger.error(f"活动缓存更新失败: {e}")
    
    async def _get_basic_activity_stats(
        self,
        user_id: str,
        start_date: datetime,
        db
    ) -> Dict[str, Any]:
        """获取基础活动统计"""
        # 总活动数
        total_query = select(func.count(UserActivity.id)).where(
            and_(
                UserActivity.user_id == user_id,
                UserActivity.created_at >= start_date
            )
        )
        total_result = await db.execute(total_query)
        total_activities = total_result.scalar() or 0
        
        # 活跃天数
        active_days_query = select(
            func.count(func.distinct(func.date(UserActivity.created_at)))
        ).where(
            and_(
                UserActivity.user_id == user_id,
                UserActivity.created_at >= start_date
            )
        )
        days_result = await db.execute(active_days_query)
        active_days = days_result.scalar() or 0
        
        # 最后活动时间
        last_activity_query = select(
            func.max(UserActivity.created_at)
        ).where(UserActivity.user_id == user_id)
        last_result = await db.execute(last_activity_query)
        last_activity = last_result.scalar()
        
        return {
            "total_activities": total_activities,
            "active_days": active_days,
            "avg_activities_per_day": total_activities / max(active_days, 1),
            "last_activity": last_activity.isoformat() if last_activity else None
        }
    
    async def start_background_tasks(self):
        """启动后台任务"""
        # 定期刷新活动缓冲区
        asyncio.create_task(self._periodic_flush())
    
    async def _periodic_flush(self):
        """定期刷新任务"""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                async with self.buffer_lock:
                    if self.activity_buffer:
                        await self._flush_activities()
            except Exception as e:
                logger.error(f"定期刷新任务异常: {e}")

# 全局活动追踪器实例
activity_tracker = UserActivityTracker()
```

---

## 🌐 API接口设计

### **1. 用户管理API**

```python
# app/api/v1/users.py
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import HTTPBearer
from ...models.user import UserCreate, UserUpdate, UserResponse
from ...services.user_service import user_service
from ...core.auth import get_current_user, require_permission
from ...core.pagination import PaginatedResponse

router = APIRouter(prefix="/users", tags=["用户管理"])
security = HTTPBearer()

@router.post("/", response_model=UserResponse)
@require_permission("user:create")
async def create_user(
    user_data: UserCreate,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """创建新用户"""
    try:
        result = await user_service.create_user(
            user_data=user_data,
            tenant_id=current_user["tenant_id"],
            created_by=current_user["sub"],
            auto_activate=current_user.get("auto_activate_users", False)
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"用户创建失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")

@router.get("/", response_model=PaginatedResponse[UserResponse])
@require_permission("user:read")
async def list_users(
    query: Optional[str] = Query(None, description="搜索查询"),
    status: Optional[str] = Query(None, description="用户状态"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="排序方向"),
    current_user: dict = Depends(get_current_user)
):
    """获取用户列表"""
    try:
        result = await user_service.search_users(
            tenant_id=current_user["tenant_id"],
            query=query,
            status=status,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        return PaginatedResponse(
            items=result["users"],
            total=result["total"],
            limit=limit,
            offset=offset,
            has_more=result["has_more"]
        )
        
    except Exception as e:
        logger.error(f"用户列表获取失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")

@router.get("/{user_id}", response_model=UserResponse)
@require_permission("user:read")
async def get_user(
    user_id: str,
    include_profile: bool = Query(False, description="包含用户画像"),
    include_activity: bool = Query(False, description="包含活动统计"),
    current_user: dict = Depends(get_current_user)
):
    """获取用户详情"""
    try:
        # 权限检查：只能查看同租户用户或自己
        if user_id != current_user["sub"]:
            await user_service.check_user_access_permission(
                user_id=user_id,
                requester_id=current_user["sub"],
                tenant_id=current_user["tenant_id"]
            )
        
        user_data = await user_service.get_user_by_id(
            user_id=user_id,
            tenant_id=current_user["tenant_id"],
            include_profile=include_profile,
            include_activity=include_activity
        )
        
        if not user_data:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        return user_data
        
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"用户详情获取失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")

@router.put("/{user_id}", response_model=UserResponse)
@require_permission("user:update")
async def update_user(
    user_id: str,
    update_data: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """更新用户信息"""
    try:
        # 权限检查
        if user_id != current_user["sub"]:
            await user_service.check_user_update_permission(
                user_id=user_id,
                requester_id=current_user["sub"],
                tenant_id=current_user["tenant_id"]
            )
        
        updated_user = await user_service.update_user(
            user_id=user_id,
            update_data=update_data,
            updated_by=current_user["sub"],
            tenant_id=current_user["tenant_id"]
        )
        
        if not updated_user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        return updated_user
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"用户更新失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")

@router.post("/{user_id}/activate")
@require_permission("user:manage")
async def activate_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """激活用户"""
    try:
        success = await user_service.activate_user(
            user_id=user_id,
            activated_by=current_user["sub"]
        )
        
        if success:
            return {"message": "用户激活成功"}
        else:
            raise HTTPException(status_code=400, detail="用户激活失败")
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"用户激活失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")

@router.post("/{user_id}/deactivate")
@require_permission("user:manage")
async def deactivate_user(
    user_id: str,
    reason: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """停用用户"""
    try:
        success = await user_service.deactivate_user(
            user_id=user_id,
            reason=reason,
            deactivated_by=current_user["sub"],
            tenant_id=current_user["tenant_id"]
        )
        
        if success:
            return {"message": "用户停用成功"}
        else:
            raise HTTPException(status_code=400, detail="用户停用失败")
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"用户停用失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")

@router.delete("/{user_id}")
@require_permission("user:delete")
async def delete_user(
    user_id: str,
    delete_type: str = Query("soft", regex="^(soft|hard|anonymize)$"),
    current_user: dict = Depends(get_current_user)
):
    """删除用户"""
    try:
        success = await user_service.delete_user(
            user_id=user_id,
            delete_type=delete_type,
            deleted_by=current_user["sub"],
            tenant_id=current_user["tenant_id"]
        )
        
        if success:
            return {"message": f"用户{delete_type}删除成功"}
        else:
            raise HTTPException(status_code=400, detail="用户删除失败")
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"用户删除失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")

@router.get("/{user_id}/activity-summary")
@require_permission("user:read")
async def get_user_activity_summary(
    user_id: str,
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    current_user: dict = Depends(get_current_user)
):
    """获取用户活动摘要"""
    try:
        # 权限检查
        if user_id != current_user["sub"]:
            await user_service.check_user_access_permission(
                user_id=user_id,
                requester_id=current_user["sub"],
                tenant_id=current_user["tenant_id"]
            )
        
        from ...services.activity_service import activity_service
        summary = await activity_service.get_user_activity_summary(user_id, days)
        
        return summary
        
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"用户活动摘要获取失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")
```

---

## 🗄️ 数据模型

### **数据库表设计**

```sql
-- 用户基础信息表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    avatar_url TEXT,
    bio TEXT,
    tenant_id UUID NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'active', 'inactive', 'banned', 'deleted', 'anonymized'
    email_verified BOOLEAN DEFAULT FALSE,
    phone_verified BOOLEAN DEFAULT FALSE,
    last_login_at TIMESTAMP,
    created_by UUID,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    activated_at TIMESTAMP,
    activated_by UUID,
    deactivated_at TIMESTAMP,
    deactivated_by UUID,
    deactivation_reason TEXT,
    deleted_at TIMESTAMP,
    deleted_by UUID,
    
    UNIQUE INDEX idx_email_tenant (email, tenant_id),
    INDEX idx_status (status),
    INDEX idx_tenant_status (tenant_id, status),
    INDEX idx_created_at (created_at),
    INDEX idx_last_login (last_login_at)
);

-- 用户画像表
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    display_name VARCHAR(100),
    bio TEXT,
    location VARCHAR(100),
    timezone VARCHAR(50),
    language VARCHAR(10) DEFAULT 'zh-CN',
    preferences JSONB DEFAULT '{}',
    tags TEXT[],
    engagement_score DECIMAL(5,2) DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_engagement_score (engagement_score),
    INDEX idx_tags (tags)
);

-- 用户活动记录表
CREATE TABLE user_activities (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    tenant_id UUID,
    activity_type VARCHAR(50) NOT NULL,
    metadata JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_user_activity (user_id, activity_type, created_at),
    INDEX idx_tenant_activity (tenant_id, created_at),
    INDEX idx_activity_type (activity_type, created_at)
);

-- 对话会话表
CREATE TABLE conversation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    title VARCHAR(255),
    message_count INTEGER DEFAULT 0,
    duration_minutes INTEGER,
    model_used VARCHAR(100),
    total_tokens INTEGER DEFAULT 0,
    total_cost DECIMAL(10,4) DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_sessions (user_id, created_at),
    INDEX idx_tenant_sessions (tenant_id, created_at),
    INDEX idx_active_sessions (is_active, created_at)
);

-- 用户关系表
CREATE TABLE user_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_user_id UUID NOT NULL,
    to_user_id UUID NOT NULL,
    relationship_type VARCHAR(20) NOT NULL, -- 'follow', 'friend', 'block', 'invite'
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'accepted', 'rejected', 'cancelled'
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE INDEX idx_user_relationship (from_user_id, to_user_id, relationship_type),
    FOREIGN KEY (from_user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (to_user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_from_user (from_user_id, relationship_type),
    INDEX idx_to_user (to_user_id, relationship_type)
);

-- 用户邀请表
CREATE TABLE user_invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inviter_id UUID NOT NULL,
    invitee_email VARCHAR(255) NOT NULL,
    tenant_id UUID NOT NULL,
    invitation_code VARCHAR(32) UNIQUE NOT NULL,
    role_id UUID,
    metadata JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'accepted', 'expired', 'cancelled'
    expires_at TIMESTAMP NOT NULL,
    accepted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    
    FOREIGN KEY (inviter_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_invitation_code (invitation_code),
    INDEX idx_invitee_email (invitee_email),
    INDEX idx_inviter (inviter_id, status),
    INDEX idx_expires_at (expires_at)
);

-- 用户通知表
CREATE TABLE user_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    tenant_id UUID,
    notification_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    metadata JSONB DEFAULT '{}',
    is_read BOOLEAN DEFAULT FALSE,
    priority VARCHAR(10) DEFAULT 'normal', -- 'low', 'normal', 'high', 'urgent'
    channel VARCHAR(20) DEFAULT 'in_app', -- 'in_app', 'email', 'sms', 'push'
    scheduled_at TIMESTAMP,
    sent_at TIMESTAMP,
    read_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_notifications (user_id, is_read, created_at),
    INDEX idx_tenant_notifications (tenant_id, created_at),
    INDEX idx_scheduled_notifications (scheduled_at)
);

-- 用户事件日志表
CREATE TABLE user_events (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID,
    tenant_id UUID,
    event_type VARCHAR(50) NOT NULL,
    event_data JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_user_events (user_id, event_type, created_at),
    INDEX idx_tenant_events (tenant_id, created_at),
    INDEX idx_event_type (event_type, created_at)
);

-- 用户偏好设置表
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    category VARCHAR(50) NOT NULL, -- 'ui', 'notification', 'model', 'privacy'
    preference_key VARCHAR(100) NOT NULL,
    preference_value JSONB NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE INDEX idx_user_preference (user_id, category, preference_key),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 用户统计汇总表（用于快速查询）
CREATE TABLE user_statistics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    stat_date DATE NOT NULL,
    total_sessions INTEGER DEFAULT 0,
    total_messages INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_cost DECIMAL(10,4) DEFAULT 0,
    active_minutes INTEGER DEFAULT 0,
    unique_models_used INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE INDEX idx_user_stat_date (user_id, stat_date),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_tenant_stat_date (tenant_id, stat_date)
);
```

---

## 🚀 部署配置

### **Docker配置**

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建非root用户
RUN useradd -m -u 1002 userservice && chown -R userservice:userservice /app
USER userservice

# 暴露端口
EXPOSE 8002

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
```

---

## 📊 监控和日志

### **监控指标**

```python
# app/utils/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time

# 用户管理指标
user_operations_total = Counter(
    'user_operations_total',
    '用户操作总数',
    ['operation', 'status', 'tenant_id']
)

user_registrations_total = Counter(
    'user_registrations_total',
    '用户注册总数',
    ['method', 'tenant_id']
)

active_users_gauge = Gauge(
    'active_users',
    '活跃用户数',
    ['period', 'tenant_id']
)

# 用户活动指标
user_activities_total = Counter(
    'user_activities_total',
    '用户活动总数',
    ['activity_type', 'tenant_id']
)

user_engagement_score = Histogram(
    'user_engagement_score',
    '用户参与度评分',
    ['tenant_id']
)

# 用户生命周期指标
user_lifecycle_events = Counter(
    'user_lifecycle_events',
    '用户生命周期事件',
    ['event_type', 'tenant_id']
)

# 画像分析指标
profile_analysis_duration = Histogram(
    'profile_analysis_duration_seconds',
    '画像分析耗时',
    ['analysis_type']
)
```

---

## 🎯 总结

**lyss-user-service** 通过从tenant-service分离用户管理逻辑，建立了专业的用户管理服务：

### **核心价值**
1. **完整生命周期** - 从注册到删除的全生命周期管理
2. **智能画像分析** - 基于行为数据的用户画像和个性化推荐
3. **活动追踪** - 全面的用户行为追踪和异常检测
4. **关系管理** - 用户邀请、团队协作、社交功能
5. **多租户隔离** - 安全的跨租户用户管理

### **技术特性**
1. **高性能** - SQLAlchemy异步优化，批量处理，Redis缓存
2. **数据驱动** - 基于用户行为数据的智能分析和推荐
3. **可扩展** - 模块化设计，易于扩展新功能
4. **安全合规** - 数据匿名化，隐私保护，审计日志
5. **用户体验** - 个性化推荐，智能通知，偏好设置

### **开发优先级**
- ⚡ **重构分离**: 从tenant-service分离出独立的用户管理逻辑
- 👤 **用户中心**: 平台用户体验的核心基础服务
- 📊 **数据驱动**: 为AI个性化服务提供用户行为数据支持

该服务完成后，将为整个平台提供专业的用户管理和个性化服务能力！

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "\u8bc4\u4f30refactor\u6587\u6863\u5b8c\u5584\u7a0b\u5ea6\uff0c\u786e\u5b9a\u5f00\u53d1\u7b56\u7565", "status": "completed", "priority": "high", "id": "evaluate-docs-readiness"}, {"content": "\u8c03\u7814\u53c2\u8003\u9879\u76ee\uff1aDify\u3001One-API\u3001OpenWebUI\u67b6\u6784\u8bbe\u8ba1", "status": "completed", "priority": "high", "id": "research-reference-projects"}, {"content": "\u5efa\u7acb\u6280\u672f\u6587\u6863\u77e5\u8bc6\u5e93\uff0c\u56fa\u5316Context7\u8c03\u7814\u6210\u679c", "status": "completed", "priority": "medium", "id": "create-tech-knowledge-base"}, {"content": "\u5236\u5b9a\u5fae\u670d\u52a1\u5f00\u53d1\u987a\u5e8f\u548c\u7b56\u7565", "status": "completed", "priority": "high", "id": "plan-microservice-development"}, {"content": "\u8865\u5145lyss-provider-service\u67b6\u6784\u6587\u6863", "status": "completed", "priority": "high", "id": "create-provider-service-doc"}, {"content": "\u8865\u5145lyss-auth-service\u67b6\u6784\u6587\u6863", "status": "completed", "priority": "high", "id": "create-auth-service-doc"}, {"content": "\u8865\u5145lyss-user-service\u67b6\u6784\u6587\u6863", "status": "completed", "priority": "high", "id": "create-user-service-doc"}]