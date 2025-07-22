# -*- coding: utf-8 -*-
"""
租户相关的Pydantic模型

定义租户管理相关的数据传输对象
"""

import uuid
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

from .base import BaseSchema, IdSchema, TimestampSchema


class TenantCreateRequest(BaseSchema):
    """租户创建请求模型"""
    
    name: str = Field(..., description="租户名称", min_length=1, max_length=255)
    slug: str = Field(..., description="租户标识符", min_length=1, max_length=100)
    subscription_plan: str = Field("basic", description="订阅计划")
    max_users: int = Field(10, description="最大用户数", ge=1, le=10000)
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="租户设置")
    
    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v):
        """验证slug格式"""
        import re
        if not re.match(r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?$', v):
            raise ValueError('slug只能包含小写字母、数字和连字符，不能以连字符开头或结尾')
        return v
    
    @field_validator('subscription_plan')
    @classmethod
    def validate_subscription_plan(cls, v):
        """验证订阅计划"""
        valid_plans = ['basic', 'standard', 'premium', 'enterprise']
        if v not in valid_plans:
            raise ValueError(f'订阅计划必须是以下之一: {", ".join(valid_plans)}')
        return v


class TenantUpdateRequest(BaseSchema):
    """租户更新请求模型"""
    
    name: Optional[str] = Field(None, description="租户名称", min_length=1, max_length=255)
    status: Optional[str] = Field(None, description="租户状态")
    subscription_plan: Optional[str] = Field(None, description="订阅计划")
    max_users: Optional[int] = Field(None, description="最大用户数", ge=1, le=10000)
    settings: Optional[Dict[str, Any]] = Field(None, description="租户设置")
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """验证状态"""
        if v is not None:
            valid_statuses = ['active', 'suspended', 'inactive']
            if v not in valid_statuses:
                raise ValueError(f'状态必须是以下之一: {", ".join(valid_statuses)}')
        return v
    
    @field_validator('subscription_plan')
    @classmethod
    def validate_subscription_plan(cls, v):
        """验证订阅计划"""
        if v is not None:
            valid_plans = ['basic', 'standard', 'premium', 'enterprise']
            if v not in valid_plans:
                raise ValueError(f'订阅计划必须是以下之一: {", ".join(valid_plans)}')
        return v


class TenantResponse(IdSchema, TimestampSchema):
    """租户响应模型"""
    
    name: str = Field(..., description="租户名称")
    slug: str = Field(..., description="租户标识符")
    status: str = Field(..., description="租户状态")
    subscription_plan: str = Field(..., description="订阅计划")
    max_users: int = Field(..., description="最大用户数")
    settings: Dict[str, Any] = Field(..., description="租户设置")
    
    # 统计信息（可选，用于详情接口）
    current_users_count: Optional[int] = Field(None, description="当前用户数")
    total_conversations: Optional[int] = Field(None, description="总对话数")
    last_activity_at: Optional[str] = Field(None, description="最后活动时间")


class TenantDetailResponse(TenantResponse):
    """租户详情响应模型（包含更多统计信息）"""
    
    # 详细统计信息
    active_users_count: int = Field(0, description="活跃用户数")
    inactive_users_count: int = Field(0, description="非活跃用户数")
    total_api_calls: int = Field(0, description="总API调用次数")
    total_tokens_used: int = Field(0, description="总token使用量")
    
    # 最近活动信息
    recent_users: Optional[list] = Field(None, description="最近活跃用户列表")
    popular_models: Optional[list] = Field(None, description="热门AI模型")


class TenantListParams(BaseSchema):
    """租户列表查询参数"""
    
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    status: Optional[str] = Field(None, description="状态过滤")
    subscription_plan: Optional[str] = Field(None, description="订阅计划过滤")
    search: Optional[str] = Field(None, description="搜索关键词（名称、slug）")
    sort_by: str = Field("created_at", description="排序字段")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="排序方向")
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """验证状态过滤"""
        if v is not None:
            valid_statuses = ['active', 'suspended', 'inactive']
            if v not in valid_statuses:
                raise ValueError(f'状态必须是以下之一: {", ".join(valid_statuses)}')
        return v
    
    @field_validator('subscription_plan')
    @classmethod
    def validate_subscription_plan(cls, v):
        """验证订阅计划过滤"""
        if v is not None:
            valid_plans = ['basic', 'standard', 'premium', 'enterprise']
            if v not in valid_plans:
                raise ValueError(f'订阅计划必须是以下之一: {", ".join(valid_plans)}')
        return v


class TenantStatsResponse(BaseSchema):
    """租户统计信息响应模型"""
    
    tenant_id: uuid.UUID = Field(..., description="租户ID")
    total_users: int = Field(0, description="总用户数")
    active_users: int = Field(0, description="活跃用户数")
    total_conversations: int = Field(0, description="总对话数")
    total_messages: int = Field(0, description="总消息数")
    api_calls_today: int = Field(0, description="今日API调用数")
    api_calls_this_month: int = Field(0, description="本月API调用数")
    storage_used_mb: int = Field(0, description="存储使用量(MB)")
    last_activity_at: Optional[str] = Field(None, description="最后活动时间")