"""
Channel数据模型

定义Channel相关的数据结构，包括Channel配置、状态管理等模型。
借鉴One-API的Channel概念设计。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from dataclasses import dataclass
from enum import Enum


class ChannelStatus(str, Enum):
    """Channel状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class ChannelHealth(str, Enum):
    """Channel健康状态枚举"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class Channel:
    """Channel数据类"""
    id: int
    name: str
    provider_id: str
    base_url: str
    credentials: Dict[str, Any]
    models: List[str]
    status: ChannelStatus
    priority: int
    weight: int
    tenant_id: str
    max_requests_per_minute: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class ChannelMetrics:
    """Channel性能指标"""
    channel_id: int
    response_time: float
    success_rate: float
    request_count: int
    error_count: int
    last_success: Optional[float]
    last_error: Optional[float]
    health_status: ChannelHealth


class ChannelCreateRequest(BaseModel):
    """创建Channel请求模型"""
    name: str = Field(..., min_length=1, max_length=100, description="Channel名称")
    provider_id: str = Field(..., description="供应商ID")
    base_url: Optional[str] = Field("", description="基础URL")
    credentials: Dict[str, Any] = Field(..., description="凭证配置")
    models: List[str] = Field(default_factory=list, description="支持的模型列表")
    priority: int = Field(0, ge=0, le=100, description="优先级（0-100）")
    weight: int = Field(100, ge=1, le=1000, description="权重（1-1000）")
    max_requests_per_minute: int = Field(0, ge=0, description="每分钟最大请求数（0表示无限制）")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "OpenAI主要Channel",
                "provider_id": "openai",
                "base_url": "https://api.openai.com/v1",
                "credentials": {
                    "api_key": "sk-..."
                },
                "models": ["gpt-3.5-turbo", "gpt-4"],
                "priority": 10,
                "weight": 100,
                "max_requests_per_minute": 1000
            }
        }


class ChannelResponse(BaseModel):
    """Channel响应模型"""
    id: int = Field(..., description="Channel ID")
    name: str = Field(..., description="Channel名称")
    provider_id: str = Field(..., description="供应商ID")
    provider_name: str = Field(..., description="供应商名称")
    base_url: str = Field(..., description="基础URL")
    models: List[str] = Field(..., description="支持的模型列表")
    status: ChannelStatus = Field(..., description="状态")
    health: ChannelHealth = Field(..., description="健康状态")
    priority: int = Field(..., description="优先级")
    weight: int = Field(..., description="权重")
    max_requests_per_minute: int = Field(..., description="每分钟最大请求数")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")
    
    class Config:
        schema_extra = {
            "example": {
                "id": 1,
                "name": "OpenAI主要Channel",
                "provider_id": "openai",
                "provider_name": "OpenAI",
                "base_url": "https://api.openai.com/v1",
                "models": ["gpt-3.5-turbo", "gpt-4"],
                "status": "active",
                "health": "healthy",
                "priority": 10,
                "weight": 100,
                "max_requests_per_minute": 1000,
                "created_at": "2025-01-21T10:00:00Z",
                "updated_at": "2025-01-21T10:00:00Z"
            }
        }


class ChannelStatusResponse(BaseModel):
    """Channel状态响应模型"""
    id: int = Field(..., description="Channel ID")
    name: str = Field(..., description="Channel名称")
    provider: str = Field(..., description="供应商")
    status: ChannelStatus = Field(..., description="状态")
    health: ChannelHealth = Field(..., description="健康状态")
    response_time: float = Field(..., description="平均响应时间（毫秒）")
    success_rate: float = Field(..., description="成功率（0-1）")
    request_count: int = Field(..., description="总请求数")
    error_count: int = Field(..., description="错误数")
    last_check: Optional[str] = Field(None, description="最后健康检查时间")
    
    class Config:
        schema_extra = {
            "example": {
                "id": 1,
                "name": "OpenAI主要Channel",
                "provider": "openai",
                "status": "active",
                "health": "healthy",
                "response_time": 234.5,
                "success_rate": 0.98,
                "request_count": 1000,
                "error_count": 20,
                "last_check": "2025-01-21T15:30:00Z"
            }
        }


class ChannelUpdateRequest(BaseModel):
    """更新Channel请求模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Channel名称")
    base_url: Optional[str] = Field(None, description="基础URL")
    credentials: Optional[Dict[str, Any]] = Field(None, description="凭证配置")
    models: Optional[List[str]] = Field(None, description="支持的模型列表")
    status: Optional[ChannelStatus] = Field(None, description="状态")
    priority: Optional[int] = Field(None, ge=0, le=100, description="优先级")
    weight: Optional[int] = Field(None, ge=1, le=1000, description="权重")
    max_requests_per_minute: Optional[int] = Field(None, ge=0, description="每分钟最大请求数")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "OpenAI备用Channel",
                "status": "active",
                "priority": 5,
                "weight": 50
            }
        }