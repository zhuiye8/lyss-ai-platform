"""
供应商数据模型

定义供应商相关的数据结构，包括供应商配置、凭证管理等模型。
支持Pydantic数据验证和SQLAlchemy ORM映射。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from dataclasses import dataclass
from enum import Enum


class ProviderStatus(str, Enum):
    """供应商状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class ModelType(str, Enum):
    """模型类型枚举"""
    LLM = "llm"
    EMBEDDING = "embedding"
    IMAGE = "image"
    AUDIO = "audio"


@dataclass
class CredentialField:
    """凭证字段配置"""
    name: str
    type: str
    required: bool
    sensitive: bool = False
    label: str = ""
    placeholder: str = ""
    default: Optional[str] = None
    validation: Optional[Dict[str, Any]] = None


@dataclass
class ModelInfo:
    """模型信息"""
    model_id: str
    name: str
    type: str
    max_tokens: int
    pricing: Dict[str, float]


@dataclass
class ProviderConfig:
    """供应商配置"""
    provider_id: str
    name: str
    description: str
    icon: str
    supported_model_types: List[str]
    credential_schema: Dict[str, Any]
    supported_models: List[ModelInfo]
    error_mapping: Dict[str, List[str]]
    defaults: Dict[str, Any]


class ProviderCredentialCreate(BaseModel):
    """创建供应商凭证请求模型"""
    provider_id: str = Field(..., description="供应商ID")
    credentials: Dict[str, Any] = Field(..., description="凭证数据")
    
    class Config:
        schema_extra = {
            "example": {
                "provider_id": "openai",
                "credentials": {
                    "api_key": "sk-...",
                    "base_url": "https://api.openai.com/v1",
                    "organization": "org-..."
                }
            }
        }


class ProviderCredentialResponse(BaseModel):
    """供应商凭证响应模型"""
    id: str = Field(..., description="凭证ID")
    provider_id: str = Field(..., description="供应商ID")
    tenant_id: str = Field(..., description="租户ID")
    status: ProviderStatus = Field(..., description="状态")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "cred_123",
                "provider_id": "openai",
                "tenant_id": "tenant_456",
                "status": "active",
                "created_at": "2025-01-21T10:00:00Z",
                "updated_at": "2025-01-21T10:00:00Z"
            }
        }


class ProviderResponse(BaseModel):
    """供应商响应模型"""
    provider_id: str = Field(..., description="供应商ID")
    name: str = Field(..., description="供应商名称")
    description: str = Field(..., description="供应商描述")
    icon: str = Field(..., description="图标")
    supported_models: List[str] = Field(..., description="支持的模型列表")
    credential_schema: Dict[str, Any] = Field(..., description="凭证配置Schema")
    is_configured: bool = Field(..., description="是否已配置凭证")
    
    class Config:
        schema_extra = {
            "example": {
                "provider_id": "openai",
                "name": "OpenAI",
                "description": "OpenAI GPT系列模型",
                "icon": "openai.png",
                "supported_models": ["gpt-3.5-turbo", "gpt-4", "gpt-4o"],
                "credential_schema": {
                    "fields": [
                        {
                            "name": "api_key",
                            "type": "string",
                            "required": True,
                            "sensitive": True,
                            "label": "API Key"
                        }
                    ]
                },
                "is_configured": True
            }
        }


class ProviderTestRequest(BaseModel):
    """供应商连接测试请求"""
    provider_id: str = Field(..., description="供应商ID")
    credentials: Dict[str, Any] = Field(..., description="测试凭证")
    
    class Config:
        schema_extra = {
            "example": {
                "provider_id": "openai",
                "credentials": {
                    "api_key": "sk-..."
                }
            }
        }


class ProviderTestResponse(BaseModel):
    """供应商连接测试响应"""
    success: bool = Field(..., description="测试是否成功")
    message: str = Field(..., description="测试结果消息")
    response_time: float = Field(0, description="响应时间（毫秒）")
    models: Optional[List[str]] = Field(None, description="可用模型列表")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "连接测试成功",
                "response_time": 234.5,
                "models": ["gpt-3.5-turbo", "gpt-4"]
            }
        }