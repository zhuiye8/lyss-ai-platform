"""
Auth Service 登录相关的Pydantic模式定义
定义登录请求和响应的数据结构
"""

from typing import Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """登录请求模型"""

    username: str = Field(
        ..., 
        min_length=1, 
        max_length=255,
        description="用户名或邮箱",
        example="user@example.com"
    )
    password: str = Field(
        ..., 
        min_length=1, 
        max_length=255,
        description="密码",
        example="password123"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "username": "user@example.com",
                "password": "password123"
            }
        }


class UserInfo(BaseModel):
    """用户信息模型（从Tenant Service获取）"""

    user_id: str = Field(..., description="用户ID")
    email: str = Field(..., description="用户邮箱")
    tenant_id: str = Field(..., description="租户ID")
    role: str = Field(default="end_user", description="用户角色")
    is_active: bool = Field(default=True, description="账户是否激活")
    last_login_at: Optional[str] = Field(None, description="上次登录时间")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "tenant_id": "550e8400-e29b-41d4-a716-446655440001",
                "role": "end_user",
                "is_active": True,
                "last_login_at": "2025-07-10T10:30:00Z"
            }
        }


class TokenResponse(BaseModel):
    """令牌响应模型"""

    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="令牌过期时间（秒）")
    refresh_token: str = Field(..., description="刷新令牌")
    user_info: UserInfo = Field(..., description="用户信息")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800,
                "refresh_token": "refresh_token_string",
                "user_info": {
                    "user_id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "user@example.com",
                    "tenant_id": "550e8400-e29b-41d4-a716-446655440001",
                    "role": "end_user",
                    "is_active": True
                }
            }
        }