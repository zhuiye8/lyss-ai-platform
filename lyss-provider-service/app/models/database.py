"""
数据库模型定义

定义供应商服务的所有数据库表结构，包括：
- 供应商配置表
- Channel配置表  
- 请求日志表
- 指标统计表

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, Float, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from pydantic import BaseModel

Base = declarative_base()


class ProviderConfigTable(Base):
    """供应商配置表"""
    __tablename__ = "provider_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(String(50), unique=True, nullable=False, index=True, comment="供应商标识符")
    name = Column(String(100), nullable=False, comment="供应商名称")
    description = Column(Text, nullable=True, comment="供应商描述")
    base_url = Column(String(500), nullable=False, comment="API基础URL")
    auth_type = Column(String(20), nullable=False, comment="认证类型")
    supported_models = Column(JSON, nullable=False, comment="支持的模型列表")
    default_config = Column(JSON, nullable=True, comment="默认配置")
    status = Column(String(20), default="active", comment="状态：active/disabled")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    __table_args__ = (
        Index('idx_provider_status', 'status'),
        {'comment': '供应商配置表'}
    )


class ChannelTable(Base):
    """Channel配置表"""
    __tablename__ = "channels"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(36), nullable=False, index=True, comment="租户ID")
    name = Column(String(100), nullable=False, comment="Channel名称")
    provider_id = Column(String(50), nullable=False, comment="供应商ID")
    base_url = Column(String(500), nullable=False, comment="API基础URL")
    credentials = Column(Text, nullable=False, comment="加密后的凭证信息")
    models = Column(JSON, nullable=False, comment="支持的模型列表")
    status = Column(String(20), default="active", comment="状态：active/disabled")
    priority = Column(Integer, default=1, comment="优先级（数字越小优先级越高）")
    weight = Column(Integer, default=100, comment="负载均衡权重")
    max_requests_per_minute = Column(Integer, default=1000, comment="每分钟最大请求数")
    config = Column(JSON, nullable=True, comment="其他配置信息")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    __table_args__ = (
        Index('idx_channel_tenant', 'tenant_id'),
        Index('idx_channel_provider', 'provider_id'),
        Index('idx_channel_status', 'status'),
        Index('idx_channel_priority', 'priority'),
        {'comment': 'Channel配置表'}
    )


class RequestLogTable(Base):
    """请求日志表"""
    __tablename__ = "request_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(36), nullable=False, index=True, comment="租户ID")
    channel_id = Column(Integer, nullable=False, comment="使用的Channel ID")
    provider_id = Column(String(50), nullable=False, comment="供应商ID")
    model = Column(String(100), nullable=False, comment="使用的模型")
    request_id = Column(String(100), nullable=True, comment="请求追踪ID")
    method = Column(String(10), default="POST", comment="HTTP方法")
    endpoint = Column(String(200), nullable=False, comment="请求端点")
    status_code = Column(Integer, nullable=False, comment="响应状态码")
    response_time = Column(Float, nullable=False, comment="响应时间（毫秒）")
    prompt_tokens = Column(Integer, default=0, comment="输入token数")
    completion_tokens = Column(Integer, default=0, comment="输出token数")
    total_tokens = Column(Integer, default=0, comment="总token数")
    is_stream = Column(Boolean, default=False, comment="是否流式请求")
    error_message = Column(Text, nullable=True, comment="错误信息")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    
    __table_args__ = (
        Index('idx_request_tenant', 'tenant_id'),
        Index('idx_request_channel', 'channel_id'),
        Index('idx_request_provider', 'provider_id'),
        Index('idx_request_model', 'model'),
        Index('idx_request_created', 'created_at'),
        Index('idx_request_status', 'status_code'),
        {'comment': '请求日志表'}
    )


class ChannelMetricsTable(Base):
    """Channel指标统计表"""
    __tablename__ = "channel_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, unique=True, nullable=False, index=True, comment="Channel ID")
    total_requests = Column(Integer, default=0, comment="总请求数")
    successful_requests = Column(Integer, default=0, comment="成功请求数")
    failed_requests = Column(Integer, default=0, comment="失败请求数")
    total_tokens = Column(Integer, default=0, comment="总token使用量")
    avg_response_time = Column(Float, default=0.0, comment="平均响应时间")
    success_rate = Column(Float, default=0.0, comment="成功率")
    last_request_time = Column(DateTime, nullable=True, comment="最后请求时间")
    last_success_time = Column(DateTime, nullable=True, comment="最后成功时间")
    last_error_time = Column(DateTime, nullable=True, comment="最后错误时间")
    health_status = Column(String(20), default="unknown", comment="健康状态")
    health_check_time = Column(DateTime, nullable=True, comment="最后健康检查时间")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    __table_args__ = (
        Index('idx_metrics_channel', 'channel_id'),
        Index('idx_metrics_health', 'health_status'),
        Index('idx_metrics_updated', 'updated_at'),
        {'comment': 'Channel指标统计表'}
    )


class TenantQuotaTable(Base):
    """租户配额管理表"""
    __tablename__ = "tenant_quotas"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(36), unique=True, nullable=False, index=True, comment="租户ID")
    daily_request_limit = Column(Integer, default=10000, comment="每日请求限制")
    daily_token_limit = Column(Integer, default=1000000, comment="每日token限制")
    daily_requests_used = Column(Integer, default=0, comment="每日已使用请求数")
    daily_tokens_used = Column(Integer, default=0, comment="每日已使用token数")
    reset_date = Column(DateTime, default=func.now(), comment="配额重置日期")
    status = Column(String(20), default="active", comment="状态：active/suspended/disabled")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    __table_args__ = (
        Index('idx_quota_tenant', 'tenant_id'),
        Index('idx_quota_status', 'status'),
        Index('idx_quota_reset', 'reset_date'),
        {'comment': '租户配额管理表'}
    )


# Pydantic模型用于API响应
class ProviderConfigResponse(BaseModel):
    """供应商配置响应模型"""
    id: int
    provider_id: str
    name: str
    description: Optional[str]
    base_url: str
    auth_type: str
    supported_models: List[str]
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True


class ChannelDBResponse(BaseModel):
    """Channel数据库响应模型"""
    id: int
    tenant_id: str
    name: str
    provider_id: str
    base_url: str
    models: List[str]
    status: str
    priority: int
    weight: int
    max_requests_per_minute: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True


class RequestLogResponse(BaseModel):
    """请求日志响应模型"""
    id: int
    tenant_id: str
    channel_id: int
    provider_id: str
    model: str
    request_id: Optional[str]
    method: str
    endpoint: str
    status_code: int
    response_time: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    is_stream: bool
    error_message: Optional[str]
    created_at: datetime
    
    class Config:
        orm_mode = True


class ChannelMetricsResponse(BaseModel):
    """Channel指标响应模型"""
    id: int
    channel_id: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_tokens: int
    avg_response_time: float
    success_rate: float
    last_request_time: Optional[datetime]
    last_success_time: Optional[datetime]
    last_error_time: Optional[datetime]
    health_status: str
    health_check_time: Optional[datetime]
    updated_at: datetime
    
    class Config:
        orm_mode = True


class TenantQuotaResponse(BaseModel):
    """租户配额响应模型"""
    id: int
    tenant_id: str
    daily_request_limit: int
    daily_token_limit: int
    daily_requests_used: int
    daily_tokens_used: int
    reset_date: datetime
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True