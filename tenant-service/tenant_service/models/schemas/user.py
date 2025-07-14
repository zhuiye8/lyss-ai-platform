# -*- coding: utf-8 -*-
"""
用户相关的Pydantic模型

定义用户管理、验证等相关的数据传输对象
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr

from .base import BaseSchema, IdSchema, TimestampSchema, TenantAwareSchema


class UserVerifyRequest(BaseSchema):
    """用户验证请求模型"""
    
    username: str = Field(..., description="用户名（邮箱）", min_length=1, max_length=255)


class UserVerifyResponse(BaseSchema):
    """用户验证响应模型（向后兼容，包含密码哈希）"""
    
    user_id: uuid.UUID = Field(..., description="用户ID")
    email: str = Field(..., description="用户邮箱")
    hashed_password: str = Field(..., description="哈希密码")
    tenant_id: uuid.UUID = Field(..., description="租户ID")
    role: str = Field(..., description="用户角色")
    is_active: bool = Field(..., description="是否激活")


class UserPasswordVerifyResponse(BaseSchema):
    """用户密码验证响应模型（安全版，不包含密码哈希）"""
    
    user_id: uuid.UUID = Field(..., description="用户ID")
    email: str = Field(..., description="用户邮箱")
    tenant_id: uuid.UUID = Field(..., description="租户ID")
    role: str = Field(..., description="用户角色")
    is_active: bool = Field(..., description="是否激活")
    password_valid: bool = Field(..., description="密码是否正确")


class UserCreateRequest(BaseSchema):
    """用户创建请求模型"""
    
    email: EmailStr = Field(..., description="用户邮箱")
    username: Optional[str] = Field(None, description="用户名", max_length=100)
    password: str = Field(..., description="密码", min_length=8, max_length=255)
    first_name: Optional[str] = Field(None, description="名", max_length=100)
    last_name: Optional[str] = Field(None, description="姓", max_length=100)
    role: str = Field("end_user", description="用户角色")


class UserUpdateRequest(BaseSchema):
    """用户更新请求模型"""
    
    username: Optional[str] = Field(None, description="用户名", max_length=100)
    first_name: Optional[str] = Field(None, description="名", max_length=100)
    last_name: Optional[str] = Field(None, description="姓", max_length=100)
    role: Optional[str] = Field(None, description="用户角色")
    password: Optional[str] = Field(None, description="新密码", min_length=8, max_length=255)
    is_active: Optional[bool] = Field(None, description="是否激活")


class UserResponse(IdSchema, TenantAwareSchema, TimestampSchema):
    """用户响应模型"""
    
    email: str = Field(..., description="用户邮箱")
    username: Optional[str] = Field(None, description="用户名")
    first_name: Optional[str] = Field(None, description="名")
    last_name: Optional[str] = Field(None, description="姓")
    full_name: str = Field(..., description="全名")
    role: str = Field(..., description="用户角色")
    role_display_name: str = Field(..., description="角色显示名称")
    is_active: bool = Field(..., description="是否激活")
    email_verified: bool = Field(..., description="邮箱是否验证")
    last_login_at: Optional[datetime] = Field(None, description="最后登录时间")


class UserDetailResponse(UserResponse):
    """用户详情响应模型（包含更多信息）"""
    
    login_attempts: int = Field(..., description="登录尝试次数")
    locked_until: Optional[datetime] = Field(None, description="锁定截止时间")
    is_locked: bool = Field(..., description="是否被锁定")
    total_conversations: int = Field(..., description="总对话数")
    total_messages: int = Field(..., description="总消息数")
    last_activity_at: Optional[datetime] = Field(None, description="最后活动时间")


class UserListParams(BaseSchema):
    """用户列表查询参数"""
    
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    role: Optional[str] = Field(None, description="角色过滤")
    is_active: Optional[bool] = Field(None, description="状态过滤")
    search: Optional[str] = Field(None, description="搜索关键词（邮箱、用户名）")
    sort_by: str = Field("created_at", description="排序字段")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="排序方向")


class PasswordChangeRequest(BaseSchema):
    """密码修改请求模型"""
    
    current_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., description="新密码", min_length=8, max_length=255)


class PasswordResetRequest(BaseSchema):
    """密码重置请求模型（管理员操作）"""
    
    new_password: str = Field(..., description="新密码", min_length=8, max_length=255)