# 多租户架构详细设计文档

## 1. 多租户架构概述

### 1.1 多租户定义
多租户架构是一种软件架构模式，其中单个应用程序实例可以为多个租户(客户)提供服务。每个租户的数据被逻辑隔离，但可能共享相同的应用程序实例和基础设施资源。

### 1.2 租户隔离级别
```
┌─────────────────────────────────────────────────┐
│                隔离级别金字塔                    │
├─────────────────────────────────────────────────┤
│  完全隔离    │ 每个租户独立部署和基础设施        │
├─────────────────────────────────────────────────┤
│  数据库隔离  │ 共享应用，独立数据库              │
├─────────────────────────────────────────────────┤
│  Schema隔离  │ 共享数据库，独立Schema           │
├─────────────────────────────────────────────────┤
│  表级隔离    │ 共享Schema，通过字段区分         │
└─────────────────────────────────────────────────┘
```

### 1.3 Lyss平台的多租户策略
采用**混合多租户模型**，结合不同隔离级别的优势：
- **核心敏感数据**: 数据库级隔离（每个租户独立数据库）
- **大容量数据**: 表级隔离（通过tenant_id字段区分）
- **缓存数据**: 键前缀隔离（Redis namespace隔离）
- **应用层**: 共享微服务实例，运行时隔离

## 2. 租户数据模型

### 2.1 租户实体设计
```python
# models/tenant.py
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class TenantStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"
    TRIAL = "trial"

class SubscriptionPlan(str, Enum):
    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"

class TenantConfig(BaseModel):
    """租户配置模型"""
    max_users: int = Field(default=10, ge=1, le=10000)
    max_conversations_per_user: int = Field(default=100, ge=1)
    max_api_calls_per_month: int = Field(default=10000, ge=0)
    max_storage_gb: float = Field(default=1.0, ge=0)
    max_memory_entries: int = Field(default=1000, ge=0)
    
    # AI模型配置
    enabled_models: list[str] = Field(default_factory=list)
    model_rate_limits: Dict[str, int] = Field(default_factory=dict)
    
    # 功能开关
    features: Dict[str, bool] = Field(default_factory=lambda: {
        "conversation_memory": True,
        "file_upload": True,
        "api_access": True,
        "webhook_integration": False,
        "sso_integration": False,
        "audit_logs": True,
        "advanced_analytics": False,
    })
    
    # 自定义设置
    custom_branding: Dict[str, Any] = Field(default_factory=dict)
    webhook_endpoints: list[str] = Field(default_factory=list)
    ip_whitelist: list[str] = Field(default_factory=list)

class Tenant(BaseModel):
    """租户主模型"""
    tenant_id: str = Field(..., description="租户唯一标识")
    tenant_name: str = Field(..., min_length=1, max_length=255)
    tenant_slug: str = Field(..., regex="^[a-z0-9-]+$", description="URL友好的租户标识")
    
    # 联系信息
    contact_email: str = Field(..., description="主要联系邮箱")
    contact_name: Optional[str] = Field(None, description="联系人姓名")
    company_name: Optional[str] = Field(None, description="公司名称")
    
    # 状态和配置
    status: TenantStatus = Field(default=TenantStatus.ACTIVE)
    subscription_plan: SubscriptionPlan = Field(default=SubscriptionPlan.FREE)
    config: TenantConfig = Field(default_factory=TenantConfig)
    
    # 数据库连接信息
    database_config: Dict[str, str] = Field(..., description="租户数据库配置")
    
    # 元数据
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    trial_ends_at: Optional[datetime] = Field(None)
    billing_cycle_start: Optional[datetime] = Field(None)
    
    # 使用统计
    current_users: int = Field(default=0, ge=0)
    current_storage_gb: float = Field(default=0, ge=0)
    monthly_api_calls: int = Field(default=0, ge=0)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class TenantUser(BaseModel):
    """租户用户关联模型"""
    user_id: str
    tenant_id: str
    role: str = Field(..., description="用户在租户中的角色")
    permissions: list[str] = Field(default_factory=list)
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    last_active_at: Optional[datetime] = None
    is_owner: bool = Field(default=False)
    
class TenantInvitation(BaseModel):
    """租户邀请模型"""
    invitation_id: str
    tenant_id: str
    email: str
    role: str
    invited_by: str
    invitation_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    accepted_at: Optional[datetime] = None
    status: str = Field(default="pending")  # pending, accepted, expired, revoked
```

### 2.2 租户路由策略
```python
# tenant/routing.py
from typing import Optional
from fastapi import Request, HTTPException, status
import re

class TenantRouter:
    """租户路由管理器"""
    
    def __init__(self, tenant_service):
        self.tenant_service = tenant_service
        self.routing_strategies = {
            "subdomain": self._route_by_subdomain,
            "header": self._route_by_header,
            "jwt": self._route_by_jwt,
            "path": self._route_by_path,
        }
    
    async def resolve_tenant(self, request: Request, strategy: str = "auto") -> Optional[str]:
        """解析当前请求的租户ID"""
        if strategy == "auto":
            # 自动检测策略优先级
            strategies = ["jwt", "header", "subdomain", "path"]
        else:
            strategies = [strategy]
        
        for strategy_name in strategies:
            if strategy_name in self.routing_strategies:
                tenant_id = await self.routing_strategies[strategy_name](request)
                if tenant_id:
                    # 验证租户是否存在且状态正常
                    tenant = await self.tenant_service.get_tenant(tenant_id)
                    if tenant and tenant.status == "active":
                        return tenant_id
        
        return None
    
    async def _route_by_subdomain(self, request: Request) -> Optional[str]:
        """通过子域名路由"""
        host = request.headers.get("host", "")
        
        # 匹配子域名模式: {tenant}.lyss.ai
        match = re.match(r"^([a-z0-9-]+)\.lyss\.ai$", host)
        if match:
            tenant_slug = match.group(1)
            # 跳过系统保留的子域名
            if tenant_slug not in ["www", "api", "admin", "app"]:
                tenant = await self.tenant_service.get_tenant_by_slug(tenant_slug)
                return tenant.tenant_id if tenant else None
        
        return None
    
    async def _route_by_header(self, request: Request) -> Optional[str]:
        """通过HTTP头路由"""
        tenant_id = request.headers.get("X-Tenant-ID")
        return tenant_id if tenant_id else None
    
    async def _route_by_jwt(self, request: Request) -> Optional[str]:
        """通过JWT令牌路由"""
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                # 解析JWT获取租户ID
                payload = self.jwt_manager.verify_token(token)
                return payload.get("tenant_id")
            except:
                return None
        return None
    
    async def _route_by_path(self, request: Request) -> Optional[str]:
        """通过URL路径路由"""
        path = request.url.path
        
        # 匹配路径模式: /tenant/{tenant_id}/...
        match = re.match(r"^/tenant/([a-f0-9-]+)/", path)
        if match:
            return match.group(1)
        
        return None

class TenantContext:
    """租户上下文管理器"""
    
    def __init__(self):
        self._context: Dict[str, Any] = {}
    
    def set_current_tenant(self, tenant_id: str, tenant_data: Dict[str, Any] = None):
        """设置当前租户上下文"""
        self._context["tenant_id"] = tenant_id
        self._context["tenant_data"] = tenant_data or {}
    
    def get_current_tenant_id(self) -> Optional[str]:
        """获取当前租户ID"""
        return self._context.get("tenant_id")
    
    def get_current_tenant_data(self) -> Dict[str, Any]:
        """获取当前租户数据"""
        return self._context.get("tenant_data", {})
    
    def clear(self):
        """清除租户上下文"""
        self._context.clear()

# 全局租户上下文实例
tenant_context = TenantContext()
```

## 3. 数据隔离实现

### 3.1 数据库级隔离
```python
# tenant/database.py
from typing import Dict, Optional
import asyncio
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

class TenantDatabaseManager:
    """租户数据库管理器"""
    
    def __init__(self, master_db_url: str):
        self.master_db_url = master_db_url
        self.tenant_engines: Dict[str, Any] = {}
        self.tenant_sessions: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
    
    async def create_tenant_database(self, tenant_id: str) -> Dict[str, str]:
        """为租户创建独立数据库"""
        db_name = f"tenant_{tenant_id.replace('-', '_')}"
        db_user = f"user_{tenant_id.replace('-', '_')}"
        db_password = self._generate_password()
        
        # 连接到主数据库创建租户数据库
        master_conn = await asyncpg.connect(self.master_db_url)
        
        try:
            # 创建数据库
            await master_conn.execute(f'CREATE DATABASE "{db_name}"')
            
            # 创建用户
            await master_conn.execute(
                f'CREATE USER "{db_user}" WITH PASSWORD \'{db_password}\''
            )
            
            # 授权
            await master_conn.execute(
                f'GRANT ALL PRIVILEGES ON DATABASE "{db_name}" TO "{db_user}"'
            )
            
            # 构建连接字符串
            db_config = {
                "host": "localhost",  # 或从配置获取
                "port": "5432",
                "database": db_name,
                "username": db_user,
                "password": db_password,
                "connection_string": f"postgresql+asyncpg://{db_user}:{db_password}@localhost:5432/{db_name}"
            }
            
            # 初始化数据库Schema
            await self._initialize_tenant_schema(db_config["connection_string"])
            
            return db_config
            
        finally:
            await master_conn.close()
    
    async def get_tenant_session(self, tenant_id: str) -> AsyncSession:
        """获取租户数据库会话"""
        async with self._lock:
            if tenant_id not in self.tenant_sessions:
                # 从主数据库获取租户连接信息
                tenant = await self.tenant_service.get_tenant(tenant_id)
                if not tenant:
                    raise ValueError(f"Tenant {tenant_id} not found")
                
                connection_string = tenant.database_config["connection_string"]
                
                # 创建引擎和会话
                engine = create_async_engine(
                    connection_string,
                    echo=False,
                    pool_size=10,
                    max_overflow=20,
                    pool_pre_ping=True,
                    pool_recycle=3600,
                )
                
                session_factory = sessionmaker(
                    engine, class_=AsyncSession, expire_on_commit=False
                )
                
                self.tenant_engines[tenant_id] = engine
                self.tenant_sessions[tenant_id] = session_factory
            
            return self.tenant_sessions[tenant_id]()
    
    async def _initialize_tenant_schema(self, connection_string: str):
        """初始化租户数据库Schema"""
        engine = create_async_engine(connection_string)
        
        # 执行Schema创建脚本
        schema_sql = """
        -- 用户表
        CREATE TABLE users (
            user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            username VARCHAR(100),
            hashed_password VARCHAR(255) NOT NULL,
            -- ... 其他用户字段
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 角色表
        CREATE TABLE roles (
            role_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            role_name VARCHAR(100) NOT NULL UNIQUE,
            permissions JSONB NOT NULL DEFAULT '[]',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 对话表
        CREATE TABLE conversations (
            conversation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(user_id),
            title VARCHAR(500),
            status VARCHAR(20) DEFAULT 'active',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 消息表
        CREATE TABLE messages (
            message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            conversation_id UUID NOT NULL REFERENCES conversations(conversation_id),
            user_id UUID NOT NULL REFERENCES users(user_id),
            role VARCHAR(20) NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 供应商凭证表
        CREATE TABLE ai_provider_credentials (
            credential_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            provider_name VARCHAR(100) NOT NULL,
            encrypted_api_key BYTEA,
            encrypted_config BYTEA,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 创建索引
        CREATE INDEX idx_users_tenant_id ON users(tenant_id);
        CREATE INDEX idx_conversations_user_id ON conversations(user_id);
        CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
        """
        
        async with engine.begin() as conn:
            await conn.execute(text(schema_sql))
        
        await engine.dispose()
    
    def _generate_password(self) -> str:
        """生成安全密码"""
        import secrets
        import string
        
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(32))

# 租户数据库中间件
class TenantDatabaseMiddleware:
    """租户数据库中间件"""
    
    def __init__(self, app, db_manager: TenantDatabaseManager):
        self.app = app
        self.db_manager = db_manager
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # 获取租户ID
            tenant_id = tenant_context.get_current_tenant_id()
            
            if tenant_id:
                # 设置数据库连接到租户数据库
                scope["tenant_session"] = await self.db_manager.get_tenant_session(tenant_id)
        
        await self.app(scope, receive, send)
```

### 3.2 缓存隔离
```python
# tenant/cache.py
import redis.asyncio as redis
from typing import Any, Optional, Union
import json
import pickle

class TenantCacheManager:
    """租户缓存管理器"""
    
    def __init__(self, redis_url: str):
        self.redis_pool = redis.ConnectionPool.from_url(redis_url)
        self.redis_client = redis.Redis(connection_pool=self.redis_pool)
    
    def _get_tenant_key(self, tenant_id: str, key: str) -> str:
        """生成租户特定的缓存键"""
        return f"tenant:{tenant_id}:{key}"
    
    async def set(self, tenant_id: str, key: str, value: Any, 
                  expire: Optional[int] = None, serializer: str = "json") -> bool:
        """设置租户缓存"""
        tenant_key = self._get_tenant_key(tenant_id, key)
        
        # 序列化值
        if serializer == "json":
            serialized_value = json.dumps(value, default=str)
        elif serializer == "pickle":
            serialized_value = pickle.dumps(value)
        else:
            serialized_value = str(value)
        
        # 设置缓存
        if expire:
            return await self.redis_client.setex(tenant_key, expire, serialized_value)
        else:
            return await self.redis_client.set(tenant_key, serialized_value)
    
    async def get(self, tenant_id: str, key: str, 
                  default: Any = None, serializer: str = "json") -> Any:
        """获取租户缓存"""
        tenant_key = self._get_tenant_key(tenant_id, key)
        
        value = await self.redis_client.get(tenant_key)
        if value is None:
            return default
        
        # 反序列化值
        try:
            if serializer == "json":
                return json.loads(value)
            elif serializer == "pickle":
                return pickle.loads(value)
            else:
                return value.decode('utf-8')
        except:
            return default
    
    async def delete(self, tenant_id: str, key: str) -> bool:
        """删除租户缓存"""
        tenant_key = self._get_tenant_key(tenant_id, key)
        return await self.redis_client.delete(tenant_key) > 0
    
    async def exists(self, tenant_id: str, key: str) -> bool:
        """检查租户缓存是否存在"""
        tenant_key = self._get_tenant_key(tenant_id, key)
        return await self.redis_client.exists(tenant_key) > 0
    
    async def incr(self, tenant_id: str, key: str, amount: int = 1) -> int:
        """递增租户缓存值"""
        tenant_key = self._get_tenant_key(tenant_id, key)
        return await self.redis_client.incr(tenant_key, amount)
    
    async def expire(self, tenant_id: str, key: str, seconds: int) -> bool:
        """设置租户缓存过期时间"""
        tenant_key = self._get_tenant_key(tenant_id, key)
        return await self.redis_client.expire(tenant_key, seconds)
    
    async def clear_tenant_cache(self, tenant_id: str) -> int:
        """清除租户所有缓存"""
        pattern = self._get_tenant_key(tenant_id, "*")
        keys = await self.redis_client.keys(pattern)
        if keys:
            return await self.redis_client.delete(*keys)
        return 0
    
    async def get_tenant_cache_stats(self, tenant_id: str) -> dict:
        """获取租户缓存统计"""
        pattern = self._get_tenant_key(tenant_id, "*")
        keys = await self.redis_client.keys(pattern)
        
        total_keys = len(keys)
        total_memory = 0
        
        if keys:
            # 计算内存使用（近似值）
            for key in keys[:100]:  # 采样前100个键
                memory = await self.redis_client.memory_usage(key)
                if memory:
                    total_memory += memory
            
            # 估算总内存使用
            if total_keys > 100:
                total_memory = total_memory * (total_keys / 100)
        
        return {
            "total_keys": total_keys,
            "estimated_memory_bytes": total_memory,
            "estimated_memory_mb": round(total_memory / 1024 / 1024, 2)
        }

# Redis ACL管理
class TenantRedisACL:
    """租户Redis访问控制列表管理"""
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
    
    async def create_tenant_user(self, tenant_id: str, password: str) -> bool:
        """为租户创建Redis用户"""
        username = f"tenant_{tenant_id.replace('-', '_')}"
        
        # 创建用户并设置权限
        acl_command = [
            "ACL", "SETUSER", username,
            "on",  # 启用用户
            f">password",  # 设置密码
            f"~tenant:{tenant_id}:*",  # 只能访问该租户的键
            "+@all",  # 允许所有命令
            "-flushall",  # 禁止清空所有数据
            "-flushdb",   # 禁止清空数据库
            "-shutdown",  # 禁止关闭服务器
            "-debug",     # 禁止调试命令
            "-config",    # 禁止配置命令
        ]
        
        try:
            await self.redis_client.execute_command(*acl_command)
            return True
        except Exception as e:
            print(f"Error creating Redis user for tenant {tenant_id}: {e}")
            return False
    
    async def delete_tenant_user(self, tenant_id: str) -> bool:
        """删除租户Redis用户"""
        username = f"tenant_{tenant_id.replace('-', '_')}"
        
        try:
            await self.redis_client.acl_deluser(username)
            return True
        except Exception as e:
            print(f"Error deleting Redis user for tenant {tenant_id}: {e}")
            return False
    
    async def list_tenant_users(self) -> list:
        """列出所有租户用户"""
        try:
            users = await self.redis_client.acl_list()
            tenant_users = []
            
            for user_info in users:
                if "tenant_" in user_info:
                    tenant_users.append(user_info)
            
            return tenant_users
        except Exception as e:
            print(f"Error listing tenant users: {e}")
            return []
```

## 4. 租户管理服务

### 4.1 租户服务
```python
# services/tenant_service.py
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import asyncio

class TenantService:
    """租户管理服务"""
    
    def __init__(self, db_manager, cache_manager, billing_service):
        self.db_manager = db_manager
        self.cache_manager = cache_manager
        self.billing_service = billing_service
    
    async def create_tenant(self, tenant_data: dict) -> Tenant:
        """创建新租户"""
        # 生成租户ID
        tenant_id = str(uuid.uuid4())
        
        # 验证租户slug唯一性
        await self._validate_tenant_slug(tenant_data["tenant_slug"])
        
        # 创建租户数据库
        db_config = await self.db_manager.create_tenant_database(tenant_id)
        
        # 创建租户记录
        tenant = Tenant(
            tenant_id=tenant_id,
            database_config=db_config,
            **tenant_data
        )
        
        # 保存到主数据库
        async with self.db_manager.get_master_session() as session:
            session.add(tenant)
            await session.commit()
        
        # 初始化租户资源
        await self._initialize_tenant_resources(tenant)
        
        # 发送欢迎邮件
        await self._send_welcome_email(tenant)
        
        return tenant
    
    async def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """获取租户信息"""
        # 先从缓存获取
        cached_tenant = await self.cache_manager.get(
            "system", f"tenant:{tenant_id}", serializer="pickle"
        )
        if cached_tenant:
            return cached_tenant
        
        # 从数据库获取
        async with self.db_manager.get_master_session() as session:
            result = await session.execute(
                select(Tenant).where(Tenant.tenant_id == tenant_id)
            )
            tenant = result.scalar_one_or_none()
        
        # 缓存结果
        if tenant:
            await self.cache_manager.set(
                "system", f"tenant:{tenant_id}", tenant, 
                expire=300, serializer="pickle"
            )
        
        return tenant
    
    async def get_tenant_by_slug(self, slug: str) -> Optional[Tenant]:
        """通过slug获取租户"""
        async with self.db_manager.get_master_session() as session:
            result = await session.execute(
                select(Tenant).where(Tenant.tenant_slug == slug)
            )
            return result.scalar_one_or_none()
    
    async def update_tenant(self, tenant_id: str, updates: dict) -> Tenant:
        """更新租户信息"""
        async with self.db_manager.get_master_session() as session:
            result = await session.execute(
                select(Tenant).where(Tenant.tenant_id == tenant_id)
            )
            tenant = result.scalar_one_or_none()
            
            if not tenant:
                raise ValueError(f"Tenant {tenant_id} not found")
            
            # 更新字段
            for field, value in updates.items():
                if hasattr(tenant, field):
                    setattr(tenant, field, value)
            
            tenant.updated_at = datetime.utcnow()
            await session.commit()
        
        # 清除缓存
        await self.cache_manager.delete("system", f"tenant:{tenant_id}")
        
        return tenant
    
    async def suspend_tenant(self, tenant_id: str, reason: str) -> bool:
        """暂停租户"""
        await self.update_tenant(tenant_id, {
            "status": TenantStatus.SUSPENDED,
            "suspension_reason": reason,
            "suspended_at": datetime.utcnow()
        })
        
        # 清除租户所有活动会话
        await self._revoke_tenant_sessions(tenant_id)
        
        # 发送暂停通知
        await self._send_suspension_notification(tenant_id, reason)
        
        return True
    
    async def delete_tenant(self, tenant_id: str) -> bool:
        """删除租户（软删除）"""
        # 更新租户状态
        await self.update_tenant(tenant_id, {
            "status": TenantStatus.DELETED,
            "deleted_at": datetime.utcnow()
        })
        
        # 清除租户缓存
        await self.cache_manager.clear_tenant_cache(tenant_id)
        
        # 备份租户数据
        await self._backup_tenant_data(tenant_id)
        
        # 调度数据清理任务（延迟执行）
        await self._schedule_tenant_cleanup(tenant_id)
        
        return True
    
    async def get_tenant_usage_stats(self, tenant_id: str) -> dict:
        """获取租户使用统计"""
        async with self.db_manager.get_tenant_session(tenant_id) as session:
            # 用户数统计
            user_count = await session.scalar(
                select(func.count(User.user_id))
                .where(User.tenant_id == tenant_id)
            )
            
            # 对话数统计
            conversation_count = await session.scalar(
                select(func.count(Conversation.conversation_id))
            )
            
            # 消息数统计
            message_count = await session.scalar(
                select(func.count(Message.message_id))
            )
            
            # 本月API调用统计
            current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
            api_calls = await session.scalar(
                select(func.count(APIUsageLog.log_id))
                .where(APIUsageLog.created_at >= current_month)
            )
        
        # 存储使用统计
        storage_stats = await self._calculate_storage_usage(tenant_id)
        
        return {
            "user_count": user_count,
            "conversation_count": conversation_count,
            "message_count": message_count,
            "monthly_api_calls": api_calls,
            "storage_usage_gb": storage_stats["total_gb"],
            "cache_usage": await self.cache_manager.get_tenant_cache_stats(tenant_id)
        }
    
    async def check_tenant_limits(self, tenant_id: str) -> dict:
        """检查租户是否超出限制"""
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        usage_stats = await self.get_tenant_usage_stats(tenant_id)
        config = tenant.config
        
        limits_check = {
            "users": {
                "current": usage_stats["user_count"],
                "limit": config.max_users,
                "exceeded": usage_stats["user_count"] >= config.max_users
            },
            "api_calls": {
                "current": usage_stats["monthly_api_calls"],
                "limit": config.max_api_calls_per_month,
                "exceeded": usage_stats["monthly_api_calls"] >= config.max_api_calls_per_month
            },
            "storage": {
                "current": usage_stats["storage_usage_gb"],
                "limit": config.max_storage_gb,
                "exceeded": usage_stats["storage_usage_gb"] >= config.max_storage_gb
            }
        }
        
        # 检查是否有任何超限
        any_exceeded = any(limit["exceeded"] for limit in limits_check.values())
        
        return {
            "limits": limits_check,
            "any_exceeded": any_exceeded,
            "actions_required": self._get_limit_actions(limits_check)
        }
    
    async def _validate_tenant_slug(self, slug: str):
        """验证租户slug唯一性"""
        existing = await self.get_tenant_by_slug(slug)
        if existing:
            raise ValueError(f"Tenant slug '{slug}' already exists")
        
        # 检查保留slug
        reserved_slugs = ["www", "api", "admin", "app", "mail", "ftp", "support"]
        if slug in reserved_slugs:
            raise ValueError(f"Slug '{slug}' is reserved")
    
    async def _initialize_tenant_resources(self, tenant: Tenant):
        """初始化租户资源"""
        tasks = [
            self._create_default_roles(tenant.tenant_id),
            self._setup_tenant_cache(tenant.tenant_id),
            self._initialize_billing(tenant),
            self._setup_monitoring(tenant.tenant_id),
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _create_default_roles(self, tenant_id: str):
        """创建默认角色"""
        default_roles = [
            {
                "role_name": "owner",
                "description": "租户所有者",
                "permissions": ["*"],  # 所有权限
            },
            {
                "role_name": "admin",
                "description": "管理员",
                "permissions": [
                    "user:create", "user:read", "user:update", "user:delete",
                    "conversation:read", "model:manage"
                ],
            },
            {
                "role_name": "user",
                "description": "普通用户",
                "permissions": [
                    "conversation:create", "conversation:read", 
                    "conversation:update", "conversation:delete",
                    "model:use"
                ],
            }
        ]
        
        async with self.db_manager.get_tenant_session(tenant_id) as session:
            for role_data in default_roles:
                role = Role(**role_data)
                session.add(role)
            await session.commit()

class TenantInvitationService:
    """租户邀请服务"""
    
    def __init__(self, tenant_service, email_service):
        self.tenant_service = tenant_service
        self.email_service = email_service
    
    async def create_invitation(self, tenant_id: str, email: str, 
                              role: str, invited_by: str) -> TenantInvitation:
        """创建租户邀请"""
        # 验证邀请者权限
        await self._validate_inviter_permissions(tenant_id, invited_by)
        
        # 检查用户是否已存在
        existing_user = await self._check_existing_user(email)
        if existing_user:
            # 检查是否已经是该租户成员
            if await self._is_tenant_member(tenant_id, existing_user.user_id):
                raise ValueError("User is already a member of this tenant")
        
        # 生成邀请
        invitation = TenantInvitation(
            invitation_id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            email=email,
            role=role,
            invited_by=invited_by,
            invitation_token=self._generate_invitation_token(),
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        
        # 保存邀请
        async with self.tenant_service.db_manager.get_master_session() as session:
            session.add(invitation)
            await session.commit()
        
        # 发送邀请邮件
        await self._send_invitation_email(invitation)
        
        return invitation
    
    async def accept_invitation(self, invitation_token: str, 
                               user_id: str) -> TenantUser:
        """接受租户邀请"""
        # 获取邀请信息
        invitation = await self._get_invitation_by_token(invitation_token)
        if not invitation:
            raise ValueError("Invalid invitation token")
        
        if invitation.status != "pending":
            raise ValueError("Invitation has already been processed")
        
        if invitation.expires_at < datetime.utcnow():
            raise ValueError("Invitation has expired")
        
        # 创建租户用户关联
        tenant_user = TenantUser(
            user_id=user_id,
            tenant_id=invitation.tenant_id,
            role=invitation.role,
            joined_at=datetime.utcnow()
        )
        
        # 更新邀请状态
        invitation.status = "accepted"
        invitation.accepted_at = datetime.utcnow()
        
        # 保存到数据库
        async with self.tenant_service.db_manager.get_tenant_session(invitation.tenant_id) as session:
            session.add(tenant_user)
            await session.commit()
        
        return tenant_user
```

## 5. 租户中间件

### 5.1 租户解析中间件
```python
# middleware/tenant_middleware.py
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import time

class TenantMiddleware(BaseHTTPMiddleware):
    """租户中间件"""
    
    def __init__(self, app, tenant_router: TenantRouter, tenant_service):
        super().__init__(app)
        self.tenant_router = tenant_router
        self.tenant_service = tenant_service
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # 跳过系统路径
        if self._should_skip_tenant_resolution(request):
            return await call_next(request)
        
        try:
            # 解析租户
            tenant_id = await self.tenant_router.resolve_tenant(request)
            
            if not tenant_id:
                # 如果是API请求，返回错误
                if request.url.path.startswith("/api/"):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Unable to resolve tenant"
                    )
                # 如果是前端请求，重定向到首页
                else:
                    return RedirectResponse(url="/", status_code=302)
            
            # 验证租户状态
            tenant = await self.tenant_service.get_tenant(tenant_id)
            if not tenant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Tenant not found"
                )
            
            if tenant.status != "active":
                if tenant.status == "suspended":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Tenant is suspended"
                    )
                elif tenant.status == "deleted":
                    raise HTTPException(
                        status_code=status.HTTP_410_GONE,
                        detail="Tenant has been deleted"
                    )
            
            # 设置租户上下文
            tenant_context.set_current_tenant(tenant_id, tenant.dict())
            
            # 在请求对象中添加租户信息
            request.state.tenant_id = tenant_id
            request.state.tenant = tenant
            
            # 处理请求
            response = await call_next(request)
            
            # 添加租户相关响应头
            response.headers["X-Tenant-ID"] = tenant_id
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Tenant resolution error: {str(e)}"
            )
        finally:
            # 清理租户上下文
            tenant_context.clear()
            
            # 记录请求时间
            process_time = time.time() - start_time
            if hasattr(request.state, 'tenant_id'):
                await self._log_tenant_request(
                    request.state.tenant_id, 
                    request, 
                    process_time
                )
    
    def _should_skip_tenant_resolution(self, request: Request) -> bool:
        """检查是否应该跳过租户解析"""
        skip_paths = [
            "/health",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/static/",
            "/favicon.ico",
            "/robots.txt",
            "/api/auth/register",  # 新用户注册
            "/api/tenants/create",  # 创建租户
        ]
        
        return any(request.url.path.startswith(path) for path in skip_paths)
    
    async def _log_tenant_request(self, tenant_id: str, request: Request, process_time: float):
        """记录租户请求日志"""
        log_data = {
            "tenant_id": tenant_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "user_agent": request.headers.get("user-agent"),
            "ip_address": request.client.host if request.client else None,
            "process_time": process_time,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 异步记录日志（避免影响响应时间）
        asyncio.create_task(self._write_request_log(log_data))
```

### 5.2 租户资源限制中间件
```python
# middleware/tenant_limits_middleware.py
class TenantLimitsMiddleware(BaseHTTPMiddleware):
    """租户资源限制中间件"""
    
    def __init__(self, app, tenant_service, cache_manager):
        super().__init__(app)
        self.tenant_service = tenant_service
        self.cache_manager = cache_manager
    
    async def dispatch(self, request: Request, call_next):
        # 跳过非API请求
        if not request.url.path.startswith("/api/"):
            return await call_next(request)
        
        tenant_id = getattr(request.state, 'tenant_id', None)
        if not tenant_id:
            return await call_next(request)
        
        # 检查API调用限制
        if await self._check_api_rate_limit(tenant_id, request):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="API rate limit exceeded"
            )
        
        # 检查存储限制（对于上传请求）
        if request.method in ["POST", "PUT", "PATCH"]:
            if await self._check_storage_limit(tenant_id, request):
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Storage limit exceeded"
                )
        
        # 记录API调用
        await self._record_api_call(tenant_id, request)
        
        return await call_next(request)
    
    async def _check_api_rate_limit(self, tenant_id: str, request: Request) -> bool:
        """检查API调用速率限制"""
        # 获取租户配置
        tenant = await self.tenant_service.get_tenant(tenant_id)
        if not tenant:
            return False
        
        # 检查每分钟限制
        minute_key = f"api_calls:minute:{tenant_id}:{int(time.time() // 60)}"
        minute_calls = await self.cache_manager.incr("system", minute_key)
        await self.cache_manager.expire("system", minute_key, 60)
        
        if minute_calls > 100:  # 每分钟100次调用限制
            return True
        
        # 检查每月限制
        month_calls = await self._get_monthly_api_calls(tenant_id)
        if month_calls >= tenant.config.max_api_calls_per_month:
            return True
        
        return False
    
    async def _record_api_call(self, tenant_id: str, request: Request):
        """记录API调用"""
        call_data = {
            "tenant_id": tenant_id,
            "endpoint": request.url.path,
            "method": request.method,
            "timestamp": datetime.utcnow(),
            "user_agent": request.headers.get("user-agent"),
            "ip_address": request.client.host if request.client else None,
        }
        
        # 异步写入使用日志
        asyncio.create_task(self._write_usage_log(call_data))
```

## 6. 租户配置管理

### 6.1 动态配置
```python
# tenant/config.py
class TenantConfigManager:
    """租户配置管理器"""
    
    def __init__(self, cache_manager, tenant_service):
        self.cache_manager = cache_manager
        self.tenant_service = tenant_service
        self.config_validators = self._setup_validators()
    
    async def get_config(self, tenant_id: str, config_key: str = None) -> Any:
        """获取租户配置"""
        # 从缓存获取
        cache_key = f"config:{config_key}" if config_key else "config"
        config = await self.cache_manager.get(tenant_id, cache_key)
        
        if config is None:
            # 从数据库获取
            tenant = await self.tenant_service.get_tenant(tenant_id)
            if not tenant:
                raise ValueError(f"Tenant {tenant_id} not found")
            
            config = tenant.config.dict()
            
            # 缓存配置
            await self.cache_manager.set(tenant_id, "config", config, expire=300)
        
        if config_key:
            return config.get(config_key)
        
        return config
    
    async def update_config(self, tenant_id: str, config_updates: dict) -> bool:
        """更新租户配置"""
        # 验证配置
        for key, value in config_updates.items():
            if not await self._validate_config_value(key, value):
                raise ValueError(f"Invalid value for config key '{key}': {value}")
        
        # 获取当前配置
        current_config = await self.get_config(tenant_id)
        
        # 合并更新
        updated_config = {**current_config, **config_updates}
        
        # 更新数据库
        await self.tenant_service.update_tenant(tenant_id, {
            "config": TenantConfig(**updated_config)
        })
        
        # 清除缓存
        await self.cache_manager.delete(tenant_id, "config")
        
        # 触发配置变更事件
        await self._trigger_config_change_event(tenant_id, config_updates)
        
        return True
    
    async def reset_config(self, tenant_id: str, config_keys: List[str] = None) -> bool:
        """重置租户配置到默认值"""
        default_config = TenantConfig()
        
        if config_keys:
            # 只重置指定的配置项
            reset_values = {
                key: getattr(default_config, key) 
                for key in config_keys 
                if hasattr(default_config, key)
            }
        else:
            # 重置所有配置
            reset_values = default_config.dict()
        
        return await self.update_config(tenant_id, reset_values)
    
    def _setup_validators(self) -> dict:
        """设置配置验证器"""
        return {
            "max_users": lambda v: isinstance(v, int) and 1 <= v <= 10000,
            "max_conversations_per_user": lambda v: isinstance(v, int) and v >= 1,
            "max_api_calls_per_month": lambda v: isinstance(v, int) and v >= 0,
            "max_storage_gb": lambda v: isinstance(v, (int, float)) and v >= 0,
            "enabled_models": lambda v: isinstance(v, list) and all(isinstance(m, str) for m in v),
            "features": lambda v: isinstance(v, dict) and all(isinstance(k, str) and isinstance(v, bool) for k, v in v.items()),
        }
    
    async def _validate_config_value(self, key: str, value: Any) -> bool:
        """验证配置值"""
        validator = self.config_validators.get(key)
        if validator:
            return validator(value)
        return True  # 未知配置项默认通过
    
    async def _trigger_config_change_event(self, tenant_id: str, changes: dict):
        """触发配置变更事件"""
        event_data = {
            "tenant_id": tenant_id,
            "changes": changes,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 发布配置变更事件
        await self.cache_manager.redis_client.publish(
            f"tenant_config_change:{tenant_id}", 
            json.dumps(event_data)
        )

# 配置变更监听器
class TenantConfigListener:
    """租户配置变更监听器"""
    
    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
        self.handlers = {}
    
    def register_handler(self, config_key: str, handler):
        """注册配置变更处理器"""
        if config_key not in self.handlers:
            self.handlers[config_key] = []
        self.handlers[config_key].append(handler)
    
    async def start_listening(self):
        """开始监听配置变更"""
        pubsub = self.cache_manager.redis_client.pubsub()
        await pubsub.psubscribe("tenant_config_change:*")
        
        async for message in pubsub.listen():
            if message["type"] == "pmessage":
                await self._handle_config_change(message["data"])
    
    async def _handle_config_change(self, data: bytes):
        """处理配置变更"""
        try:
            event_data = json.loads(data.decode())
            tenant_id = event_data["tenant_id"]
            changes = event_data["changes"]
            
            for config_key, new_value in changes.items():
                if config_key in self.handlers:
                    for handler in self.handlers[config_key]:
                        await handler(tenant_id, config_key, new_value)
        
        except Exception as e:
            print(f"Error handling config change: {e}")
```

这个多租户架构详细设计文档提供了完整的多租户实现方案，包括数据隔离、租户管理、中间件、配置管理等核心功能的详细设计和实现。