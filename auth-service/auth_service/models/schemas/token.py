"""
Auth Service 令牌相关的Pydantic模式定义
定义令牌刷新和验证的数据结构
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求模型"""

    refresh_token: str = Field(
        ..., 
        description="刷新令牌",
        example="refresh_token_string"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "refresh_token_string"
            }
        }


class RefreshTokenResponse(BaseModel):
    """刷新令牌响应模型"""

    access_token: str = Field(..., description="新的访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="令牌过期时间（秒）")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800
            }
        }


class TokenVerifyRequest(BaseModel):
    """令牌验证请求模型（内部接口）"""

    token: str = Field(
        ..., 
        description="要验证的JWT令牌",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class TokenVerifyResponse(BaseModel):
    """令牌验证响应模型"""

    valid: bool = Field(..., description="令牌是否有效")
    payload: Optional[Dict[str, Any]] = Field(None, description="令牌载荷数据")

    class Config:
        json_schema_extra = {
            "example": {
                "valid": True,
                "payload": {
                    "user_id": "550e8400-e29b-41d4-a716-446655440000",
                    "tenant_id": "550e8400-e29b-41d4-a716-446655440001",
                    "role": "end_user",
                    "email": "user@example.com",
                    "exp": 1234567890
                }
            }
        }


class LogoutRequest(BaseModel):
    """登出请求模型"""

    token: Optional[str] = Field(
        None, 
        description="要废止的令牌（可选）",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }