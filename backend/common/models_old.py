"""
Common database models and schemas
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
    """Mixin for timestamp fields"""
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
    """Tenant model"""
    __tablename__ = "tenants"
    
    tenant_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_name = Column(String(255), nullable=False)
    tenant_slug = Column(String(100), unique=True, nullable=False)
    
    # Contact information
    contact_email = Column(String(255), nullable=False)
    contact_name = Column(String(255), nullable=True)
    company_name = Column(String(255), nullable=True)
    
    # Status and plan
    status = Column(String(20), default=TenantStatus.ACTIVE, nullable=False)
    subscription_plan = Column(String(20), default=SubscriptionPlan.FREE, nullable=False)
    
    # Configuration
    config = Column(JSON, nullable=False, default=dict)
    
    # Database configuration
    database_config = Column(JSON, nullable=False, default=dict)
    
    # Metadata
    metadata = Column(JSON, nullable=False, default=dict)
    
    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    ai_credentials = relationship("AICredential", back_populates="tenant", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_tenant_slug', 'tenant_slug'),
        Index('idx_tenant_status', 'status'),
        Index('idx_tenant_plan', 'subscription_plan'),
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
    avatar_url = Column(String(500), nullable=True)  # 修正字段名
    
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


class AICredential(Base, TimestampMixin):
    """AI provider credentials"""
    __tablename__ = "ai_credentials"
    
    credential_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.tenant_id"), nullable=False)
    
    # Provider info
    provider_name = Column(String(100), nullable=False)
    provider_type = Column(String(50), nullable=False)
    display_name = Column(String(255), nullable=False)
    
    # Credentials (encrypted)
    api_key = Column(Text, nullable=False)
    base_url = Column(String(500), nullable=True)
    
    # Configuration
    model_mappings = Column(JSON, nullable=False, default=dict)
    rate_limits = Column(JSON, nullable=False, default=dict)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="ai_credentials")
    
    # Indexes
    __table_args__ = (
        Index('idx_ai_credential_tenant', 'tenant_id'),
        Index('idx_ai_credential_provider', 'provider_type'),
        Index('idx_ai_credential_active', 'is_active'),
    )


class ConversationStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class Conversation(Base, TimestampMixin):
    """Conversation model"""
    __tablename__ = "conversations"
    
    conversation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.tenant_id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    
    # Content
    title = Column(String(500), nullable=False)
    summary = Column(Text, nullable=True)
    
    # Status
    status = Column(String(20), default=ConversationStatus.ACTIVE, nullable=False)
    
    # Metadata
    metadata = Column(JSON, nullable=False, default=dict)
    
    # Statistics
    message_count = Column(Integer, default=0, nullable=False)
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_conversation_user', 'user_id'),
        Index('idx_conversation_tenant', 'tenant_id'),
        Index('idx_conversation_status', 'status'),
        Index('idx_conversation_updated', 'updated_at'),
    )


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(Base, TimestampMixin):
    """Message model"""
    __tablename__ = "messages"
    
    message_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.conversation_id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Content
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(String(50), default="text", nullable=False)
    
    # Metadata
    metadata = Column(JSON, nullable=False, default=dict)
    
    # Attachments
    attachments = Column(JSON, nullable=False, default=list)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    
    # Indexes
    __table_args__ = (
        Index('idx_message_conversation', 'conversation_id'),
        Index('idx_message_tenant', 'tenant_id'),
        Index('idx_message_created', 'created_at'),
    )


class AuditLog(Base):
    """Audit log model"""
    __tablename__ = "audit_logs"
    
    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Event details
    event_type = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(255), nullable=True)
    
    # Result
    result = Column(String(20), nullable=False)  # success, failure, error
    
    # Details
    details = Column(JSON, nullable=False, default=dict)
    
    # Context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Timestamp
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_audit_tenant', 'tenant_id'),
        Index('idx_audit_user', 'user_id'),
        Index('idx_audit_event', 'event_type'),
        Index('idx_audit_timestamp', 'timestamp'),
    )


# Pydantic Schemas
class TenantConfigSchema(BaseModel):
    """Tenant configuration schema"""
    max_users: int = Field(default=10, ge=1, le=10000)
    max_conversations_per_user: int = Field(default=100, ge=1)
    max_api_calls_per_month: int = Field(default=10000, ge=0)
    max_storage_gb: float = Field(default=1.0, ge=0)
    max_memory_entries: int = Field(default=1000, ge=0)
    
    # AI model configuration
    enabled_models: List[str] = Field(default_factory=list)
    model_rate_limits: Dict[str, int] = Field(default_factory=dict)
    
    # Feature flags
    features: Dict[str, bool] = Field(default_factory=lambda: {
        "conversation_memory": True,
        "file_upload": True,
        "api_access": True,
        "webhook_integration": False,
        "sso_integration": False,
        "audit_logs": True,
        "advanced_analytics": False,
    })
    
    # Custom settings
    custom_branding: Dict[str, Any] = Field(default_factory=dict)
    webhook_endpoints: List[str] = Field(default_factory=list)
    ip_whitelist: List[str] = Field(default_factory=list)


class TenantSchema(BaseModel):
    """Tenant schema"""
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
    
    class Config:
        from_attributes = True


class UserPreferencesSchema(BaseModel):
    """User preferences schema"""
    theme: str = Field(default="light")
    language: str = Field(default="en")
    timezone: str = Field(default="UTC")
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
    """User schema"""
    user_id: str
    tenant_id: str
    email: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    profile_picture: Optional[str] = None
    status: UserStatus
    roles: List[str]
    last_login_at: Optional[datetime] = None
    preferences: UserPreferencesSchema
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ConversationSchema(BaseModel):
    """Conversation schema"""
    conversation_id: str
    tenant_id: str
    user_id: str
    title: str
    summary: Optional[str] = None
    status: ConversationStatus
    metadata: Dict[str, Any]
    message_count: int
    last_message_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MessageSchema(BaseModel):
    """Message schema"""
    message_id: str
    conversation_id: str
    tenant_id: str
    role: MessageRole
    content: str
    content_type: str
    metadata: Dict[str, Any]
    attachments: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AuditLogSchema(BaseModel):
    """Audit log schema"""
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
    
    class Config:
        from_attributes = True