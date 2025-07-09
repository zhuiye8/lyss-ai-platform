"""
通用数据库模型和模式
更新以符合最新的数据库设计
"""
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from sqlalchemy import Column, String, DateTime, Boolean, JSON, Integer, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from pydantic import BaseModel, Field, validator

from .database import Base


# SQLAlchemy Models
class TimestampMixin:
    """时间戳混合类"""
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


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


class Tenant(Base, TimestampMixin):
    """租户模型"""
    __tablename__ = "tenants"
    
    tenant_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_name = Column(String(255), nullable=False, unique=True)
    tenant_slug = Column(String(100), unique=True, nullable=False)
    
    # 联系信息
    contact_email = Column(String(255), nullable=False)
    contact_name = Column(String(255), nullable=True)
    company_name = Column(String(255), nullable=True)
    
    # 状态和订阅
    status = Column(String(20), default=TenantStatus.ACTIVE, nullable=False)
    subscription_plan = Column(String(20), default=SubscriptionPlan.FREE, nullable=False)
    
    # 数据库连接配置（加密存储）
    db_connection_config = Column(Text, nullable=True)
    
    # 租户配置
    config = Column(JSON, nullable=False, default=dict)
    
    # 元数据
    tenant_metadata = Column(JSON, nullable=False, default=dict)
    
    # 软删除
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # 索引
    __table_args__ = (
        Index('idx_tenants_slug', 'tenant_slug'),
        Index('idx_tenants_status', 'status'),
        Index('idx_tenants_plan', 'subscription_plan'),
        Index('idx_tenants_created_at', 'created_at'),
    )


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class User(Base, TimestampMixin):
    """用户模型"""
    __tablename__ = "users"
    
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)  # 租户ID（冗余字段）
    
    # 身份认证信息
    email = Column(String(255), nullable=False, unique=True)  # 使用CITEXT类型
    username = Column(String(100), nullable=True)
    password_hash = Column(String(255), nullable=False)
    
    # 个人信息
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    
    # 状态和安全
    status = Column(String(20), default=UserStatus.ACTIVE, nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    login_count = Column(Integer, default=0, nullable=False)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    
    # 邮箱验证
    email_verified = Column(Boolean, default=False, nullable=False)
    email_verification_token = Column(String(255), nullable=True)
    email_verification_expires = Column(DateTime(timezone=True), nullable=True)
    
    # 密码重置
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)
    
    # 用户偏好设置
    preferences = Column(JSON, nullable=False, default=dict)
    
    # 软删除
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # 关联关系
    user_roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index('idx_users_email', 'email'),
        Index('idx_users_tenant_id', 'tenant_id'),
        Index('idx_users_status', 'status'),
        Index('idx_users_created_at', 'created_at'),
    )


class Role(Base, TimestampMixin):
    """角色模型"""
    __tablename__ = "roles"
    
    role_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_name = Column(String(100), nullable=False, unique=True)
    role_description = Column(Text, nullable=True)
    permissions = Column(JSON, nullable=False, default=list)  # 权限列表
    is_system_role = Column(Boolean, default=False, nullable=False)  # 是否为系统预定义角色
    
    # 关联关系
    user_roles = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index('idx_roles_name', 'role_name'),
    )


class UserRole(Base):
    """用户角色关联模型"""
    __tablename__ = "user_roles"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.role_id", ondelete="CASCADE"), primary_key=True)
    assigned_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # 关联关系
    user = relationship("User", back_populates="user_roles", foreign_keys=[user_id])
    role = relationship("Role", back_populates="user_roles")
    assigner = relationship("User", foreign_keys=[assigned_by])
    
    # 索引
    __table_args__ = (
        Index('idx_user_roles_user_id', 'user_id'),
        Index('idx_user_roles_role_id', 'role_id'),
    )


class AICredential(Base, TimestampMixin):
    """AI供应商凭证模型"""
    __tablename__ = "ai_credentials"
    
    credential_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    
    # 供应商信息
    provider_name = Column(String(100), nullable=False)
    provider_type = Column(String(50), nullable=False)
    display_name = Column(String(200), nullable=True)  # 用户友好的显示名称
    
    # 加密存储的敏感信息
    encrypted_api_key = Column(Text, nullable=True)  # 加密后的API密钥
    encrypted_config = Column(Text, nullable=True)  # 加密后的其他配置信息
    
    # 非敏感配置
    base_url = Column(String(500), nullable=True)
    model_mappings = Column(JSON, nullable=True)  # 模型映射配置
    rate_limits = Column(JSON, nullable=True)  # 速率限制设置
    retry_config = Column(JSON, nullable=True)  # 重试配置
    timeout_config = Column(JSON, nullable=True)  # 超时配置
    
    # 状态和元数据
    status = Column(String(20), default='active', nullable=False)  # 'active', 'inactive', 'testing', 'disabled'
    last_tested_at = Column(DateTime(timezone=True), nullable=True)
    test_result = Column(JSON, nullable=True)  # 最后测试结果
    usage_statistics = Column(JSON, nullable=True)  # 使用统计
    
    # 审计信息
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    
    # 关联关系
    ai_models = relationship("AIModel", back_populates="credential", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index('idx_ai_credentials_tenant_id', 'tenant_id'),
        Index('idx_ai_credentials_provider', 'provider_name'),
        Index('idx_ai_credentials_status', 'status'),
        # 唯一约束
        Index('idx_ai_credentials_unique', 'tenant_id', 'provider_name', 'display_name', unique=True),
    )


class AIModel(Base, TimestampMixin):
    """AI模型配置模型"""
    __tablename__ = "ai_models"
    
    model_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    credential_id = Column(UUID(as_uuid=True), ForeignKey("ai_credentials.credential_id", ondelete="CASCADE"), nullable=False)
    
    model_name = Column(String(200), nullable=False)  # 供应商的模型名称
    model_alias = Column(String(200), nullable=True)  # 内部别名
    model_type = Column(String(50), nullable=False)  # 'chat', 'completion', 'embedding', 'image'
    
    # 模型信息
    capabilities = Column(JSON, nullable=True)  # 模型能力描述
    pricing = Column(JSON, nullable=True)  # 定价信息
    context_window = Column(Integer, nullable=True)
    max_tokens = Column(Integer, nullable=True)
    supports_streaming = Column(Boolean, default=False, nullable=False)
    supports_function_calling = Column(Boolean, default=False, nullable=False)
    
    # 状态和优先级
    is_enabled = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=0, nullable=False)  # 优先级，用于模型选择
    
    # 关联关系
    credential = relationship("AICredential", back_populates="ai_models")
    
    # 索引
    __table_args__ = (
        Index('idx_ai_models_credential_id', 'credential_id'),
        Index('idx_ai_models_type', 'model_type'),
    )


class ConversationStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class Conversation(Base, TimestampMixin):
    """对话模型"""
    __tablename__ = "conversations"
    
    conversation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    
    # 内容
    title = Column(String(500), nullable=True)
    summary = Column(Text, nullable=True)
    
    # 对话配置
    model_config = Column(JSON, nullable=True)  # 使用的模型配置
    system_prompt = Column(Text, nullable=True)  # 系统提示词
    
    # 状态和统计
    status = Column(String(20), default=ConversationStatus.ACTIVE, nullable=False)
    message_count = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)
    estimated_cost = Column(Integer, default=0, nullable=False)  # 使用整数表示小数（分）
    
    # 元数据
    conversation_metadata = Column(JSON, nullable=False, default=dict)
    tags = Column(JSON, nullable=True)  # 标签
    
    # 时间戳
    last_message_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # 关联关系
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index('idx_conversations_user_id', 'user_id'),
        Index('idx_conversations_status', 'status'),
        Index('idx_conversations_updated_at', 'updated_at'),
        Index('idx_conversations_user_status', 'user_id', 'status'),
    )


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class Message(Base, TimestampMixin):
    """消息模型"""
    __tablename__ = "messages"
    
    message_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.conversation_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    parent_message_id = Column(UUID(as_uuid=True), ForeignKey("messages.message_id"), nullable=True)  # 支持消息树结构
    
    # 消息内容
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system', 'tool'
    content = Column(Text, nullable=False)
    content_type = Column(String(50), default="text", nullable=False)  # 'text', 'markdown', 'json'
    
    # AI生成相关信息
    model_used = Column(String(200), nullable=True)  # 使用的模型
    prompt_tokens = Column(Integer, default=0, nullable=False)
    completion_tokens = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)
    estimated_cost = Column(Integer, default=0, nullable=False)  # 使用整数表示小数（分）
    processing_time_ms = Column(Integer, nullable=True)
    
    # 元数据和附件
    message_metadata = Column(JSON, nullable=False, default=dict)
    attachments = Column(JSON, nullable=True)  # 附件信息
    
    # 软删除
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # 关联关系
    conversation = relationship("Conversation", back_populates="messages")
    parent_message = relationship("Message", remote_side=[message_id])
    
    # 索引
    __table_args__ = (
        Index('idx_messages_conversation_id', 'conversation_id'),
        Index('idx_messages_user_id', 'user_id'),
        Index('idx_messages_created_at', 'created_at'),
        Index('idx_messages_conversation_created', 'conversation_id', 'created_at'),
    )


class APIKey(Base, TimestampMixin):
    """API密钥模型"""
    __tablename__ = "api_keys"
    
    api_key_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    key_name = Column(String(200), nullable=False)
    encrypted_key_value = Column(Text, nullable=False)  # 加密后的API密钥值
    key_prefix = Column(String(20), nullable=False)  # 密钥前缀，用于显示
    
    # 权限和限制
    permissions = Column(JSON, nullable=False, default=list)
    rate_limit_per_minute = Column(Integer, default=60, nullable=False)
    rate_limit_per_hour = Column(Integer, default=1000, nullable=False)
    rate_limit_per_day = Column(Integer, default=10000, nullable=False)
    
    # 状态和统计
    status = Column(String(20), default='active', nullable=False)  # 'active', 'inactive', 'revoked'
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    usage_count = Column(Integer, default=0, nullable=False)
    
    # 过期和安全
    expires_at = Column(DateTime(timezone=True), nullable=True)
    # allowed_ips = Column(ARRAY(String), nullable=True)  # 允许的IP地址
    
    # 关联关系
    user = relationship("User", back_populates="api_keys")
    
    # 索引
    __table_args__ = (
        Index('idx_api_keys_user_id', 'user_id'),
        Index('idx_api_keys_status', 'status'),
        Index('idx_api_keys_prefix', 'key_prefix'),
        # 唯一约束
        Index('idx_api_keys_unique', 'user_id', 'key_name', unique=True),
    )


class AuditLog(Base):
    """审计日志模型"""
    __tablename__ = "audit_logs"
    
    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    
    # 事件详情
    event_type = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(255), nullable=True)
    
    # 结果
    result = Column(String(20), nullable=False)  # success, failure, error
    
    # 详情
    details = Column(JSON, nullable=False, default=dict)
    
    # 上下文
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # 时间戳
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # 索引
    __table_args__ = (
        Index('idx_audit_tenant', 'tenant_id'),
        Index('idx_audit_user', 'user_id'),
        Index('idx_audit_event', 'event_type'),
        Index('idx_audit_timestamp', 'timestamp'),
    )


# Pydantic Schemas
class TenantConfigSchema(BaseModel):
    """租户配置模式"""
    max_users: int = Field(default=10, ge=1, le=10000)
    max_conversations_per_user: int = Field(default=100, ge=1)
    max_api_calls_per_month: int = Field(default=10000, ge=0)
    max_storage_gb: float = Field(default=1.0, ge=0)
    max_memory_entries: int = Field(default=1000, ge=0)
    
    # AI模型配置
    enabled_models: List[str] = Field(default_factory=list)
    model_rate_limits: Dict[str, int] = Field(default_factory=dict)
    
    # 功能标志
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
    webhook_endpoints: List[str] = Field(default_factory=list)
    ip_whitelist: List[str] = Field(default_factory=list)


class TenantSchema(BaseModel):
    """租户模式"""
    tenant_id: str
    tenant_name: str
    tenant_slug: str
    contact_email: str
    contact_name: Optional[str] = None
    company_name: Optional[str] = None
    status: TenantStatus
    subscription_plan: SubscriptionPlan
    config: TenantConfigSchema
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class UserPreferencesSchema(BaseModel):
    """用户偏好设置模式"""
    theme: str = Field(default="light")
    language: str = Field(default="zh-CN")
    timezone: str = Field(default="Asia/Shanghai")
    notifications: Dict[str, bool] = Field(default_factory=lambda: {
        "email": True,
        "push": True,
        "browser": True
    })
    ai_settings: Dict[str, Any] = Field(default_factory=lambda: {
        "default_model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 2000,
        "use_memory": True
    })


class UserSchema(BaseModel):
    """用户模型响应数据"""
    user_id: str
    tenant_id: str
    email: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar_url: Optional[str] = None
    status: UserStatus
    email_verified: bool
    last_login_at: Optional[datetime] = None
    login_count: int
    preferences: UserPreferencesSchema
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class ConversationSchema(BaseModel):
    """对话模型响应数据"""
    conversation_id: str
    user_id: str
    title: Optional[str] = None
    summary: Optional[str] = None
    status: ConversationStatus
    ai_model_config: Optional[Dict[str, Any]] = None
    conversation_metadata: Dict[str, Any]
    message_count: int
    total_tokens: int
    estimated_cost: int
    last_message_at: datetime
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class MessageSchema(BaseModel):
    """消息模型响应数据"""
    message_id: str
    conversation_id: str
    user_id: str
    parent_message_id: Optional[str] = None
    role: MessageRole
    content: str
    content_type: str
    model_used: Optional[str] = None
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: int
    processing_time_ms: Optional[int] = None
    message_metadata: Dict[str, Any]
    attachments: Optional[List[Dict[str, Any]]] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class AuditLogSchema(BaseModel):
    """审计日志模式"""
    log_id: str
    tenant_id: str
    user_id: Optional[str] = None
    event_type: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    result: str
    details: Dict[str, Any]
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime
    
    model_config = {"from_attributes": True}