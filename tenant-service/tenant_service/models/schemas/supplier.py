# -*- coding: utf-8 -*-
"""
供应商凭证相关的Pydantic模型

定义供应商凭证管理相关的数据传输对象
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, HttpUrl

from .base import BaseSchema, IdSchema, TimestampSchema, TenantAwareSchema


class SupplierCredentialCreateRequest(BaseSchema):
    """供应商凭证创建请求模型"""
    
    provider_name: str = Field(
        ..., 
        description="供应商名称",
        min_length=1,
        max_length=50,
        pattern=r"^[a-z][a-z0-9_]*$"
    )
    display_name: str = Field(
        ..., 
        description="显示名称",
        min_length=1,
        max_length=100
    )
    api_key: str = Field(
        ..., 
        description="API密钥",
        min_length=1,
        max_length=500
    )
    base_url: Optional[str] = Field(
        None, 
        description="基础URL",
        max_length=255
    )
    model_configs: Optional[Dict[str, Any]] = Field(
        None, 
        description="模型配置"
    )


class SupplierCredentialUpdateRequest(BaseSchema):
    """供应商凭证更新请求模型"""
    
    display_name: Optional[str] = Field(
        None, 
        description="显示名称",
        min_length=1,
        max_length=100
    )
    api_key: Optional[str] = Field(
        None, 
        description="新API密钥",
        min_length=1,
        max_length=500
    )
    base_url: Optional[str] = Field(
        None, 
        description="基础URL",
        max_length=255
    )
    model_configs: Optional[Dict[str, Any]] = Field(
        None, 
        description="模型配置"
    )
    is_active: Optional[bool] = Field(
        None, 
        description="是否激活"
    )


class SupplierCredentialResponse(IdSchema, TenantAwareSchema, TimestampSchema):
    """供应商凭证响应模型（不包含API密钥）"""
    
    provider_name: str = Field(..., description="供应商名称")
    display_name: str = Field(..., description="显示名称")
    base_url: Optional[str] = Field(None, description="基础URL")
    model_configs: Dict[str, Any] = Field(..., description="模型配置")
    is_active: bool = Field(..., description="是否激活")
    # 注意：不包含 api_key 字段，确保安全


class SupplierCredentialDetailResponse(SupplierCredentialResponse):
    """供应商凭证详情响应模型（包含更多统计信息）"""
    
    last_used_at: Optional[datetime] = Field(None, description="最后使用时间")
    usage_count: int = Field(0, description="使用次数")
    error_count: int = Field(0, description="错误次数")
    last_error_at: Optional[datetime] = Field(None, description="最后错误时间")
    last_error_message: Optional[str] = Field(None, description="最后错误信息")


class SupplierCredentialListParams(BaseSchema):
    """供应商凭证列表查询参数"""
    
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    provider_name: Optional[str] = Field(None, description="供应商过滤")
    is_active: Optional[bool] = Field(None, description="状态过滤")
    sort_by: str = Field("created_at", description="排序字段")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="排序方向")


class SupplierTestRequest(BaseSchema):
    """供应商连接测试请求模型"""
    
    test_type: str = Field(
        "connection", 
        description="测试类型",
        pattern="^(connection|model_list|simple_chat)$"
    )
    model_name: Optional[str] = Field(
        None, 
        description="要测试的模型名称"
    )
    test_message: Optional[str] = Field(
        "Hello, this is a test message.", 
        description="测试消息内容",
        max_length=1000
    )


class SupplierTestResponse(BaseSchema):
    """供应商连接测试响应模型"""
    
    success: bool = Field(..., description="测试是否成功")
    test_type: str = Field(..., description="测试类型")
    response_time_ms: int = Field(..., description="响应时间（毫秒）")
    provider_name: str = Field(..., description="供应商名称")
    model_name: Optional[str] = Field(None, description="测试的模型名称")
    
    # 测试结果详情
    result_data: Optional[Dict[str, Any]] = Field(None, description="测试结果数据")
    error_message: Optional[str] = Field(None, description="错误信息")
    error_code: Optional[str] = Field(None, description="错误代码")
    
    # 额外信息
    available_models: Optional[list[str]] = Field(None, description="可用模型列表")
    api_version: Optional[str] = Field(None, description="API版本")
    rate_limit_info: Optional[Dict[str, Any]] = Field(None, description="速率限制信息")


class SupplierCredentialSecureResponse(BaseSchema):
    """供应商凭证安全响应模型（仅内部服务使用，包含解密的API密钥）"""
    
    id: uuid.UUID = Field(..., description="凭证ID")
    tenant_id: uuid.UUID = Field(..., description="租户ID")
    provider_name: str = Field(..., description="供应商名称")
    display_name: str = Field(..., description="显示名称")
    api_key: str = Field(..., description="解密的API密钥")
    base_url: Optional[str] = Field(None, description="基础URL")
    model_configs: Dict[str, Any] = Field(..., description="模型配置")
    is_active: bool = Field(..., description="是否激活")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class ModelInfo(BaseSchema):
    """模型信息模型"""
    
    model_id: str = Field(..., description="模型ID")
    display_name: str = Field(..., description="显示名称")
    description: str = Field(..., description="模型描述")
    type: str = Field(..., description="模型类型")
    context_window: int = Field(..., description="上下文窗口大小")
    max_tokens: int = Field(..., description="最大输出tokens")
    price_per_1k_tokens: Dict[str, float] = Field(..., description="每千tokens价格")
    features: List[str] = Field(..., description="特性列表")
    is_available: bool = Field(True, description="是否可用")


class ProviderInfo(BaseSchema):
    """供应商信息模型"""
    
    provider_name: str = Field(..., description="供应商名称")
    display_name: str = Field(..., description="显示名称")
    description: str = Field(..., description="供应商描述")
    logo_url: str = Field(..., description="Logo URL")
    base_url: Optional[str] = Field(None, description="基础URL")
    models: List[ModelInfo] = Field(..., description="模型列表")


class AvailableProvidersResponse(BaseSchema):
    """可用供应商响应模型"""
    
    providers: List[ProviderInfo] = Field(..., description="供应商列表")


class ProviderModelsResponse(BaseSchema):
    """供应商模型响应模型"""
    
    provider_name: str = Field(..., description="供应商名称")
    display_name: str = Field(..., description="显示名称")
    models: List[ModelInfo] = Field(..., description="模型列表")


# 供应商和模型树形结构配置
SUPPORTED_PROVIDERS = {
    "openai": {
        "display_name": "OpenAI",
        "description": "OpenAI是人工智能研究公司，提供GPT系列模型",
        "logo_url": "/images/providers/openai.png",
        "base_url": "https://api.openai.com/v1",
        "api_key_pattern": r"^sk-[A-Za-z0-9]{48}$",
        "test_endpoint": "/models",
        "test_method": "model_list",
        "models": {
            "gpt-4": {
                "display_name": "GPT-4",
                "description": "最强大的GPT-4模型，适用于复杂任务",
                "type": "chat",
                "context_window": 8192,
                "max_tokens": 4096,
                "price_per_1k_tokens": {"input": 0.03, "output": 0.06},
                "features": ["复杂推理", "创意写作", "多语言", "代码生成"]
            },
            "gpt-4-turbo": {
                "display_name": "GPT-4 Turbo",
                "description": "更快的GPT-4版本，性价比更高",
                "type": "chat",
                "context_window": 32768,
                "max_tokens": 4096,
                "price_per_1k_tokens": {"input": 0.01, "output": 0.03},
                "features": ["快速响应", "长上下文", "多语言", "代码生成"]
            },
            "gpt-3.5-turbo": {
                "display_name": "GPT-3.5 Turbo",
                "description": "快速且经济的对话模型",
                "type": "chat",
                "context_window": 4096,
                "max_tokens": 2048,
                "price_per_1k_tokens": {"input": 0.001, "output": 0.002},
                "features": ["高性价比", "快速响应", "多语言"]
            }
        }
    },
    "anthropic": {
        "display_name": "Anthropic",
        "description": "Anthropic专注于AI安全研究，提供Claude系列模型",
        "logo_url": "/images/providers/anthropic.png",
        "base_url": "https://api.anthropic.com",
        "api_key_pattern": r"^sk-ant-[A-Za-z0-9\-_]{95}$",
        "test_endpoint": "/v1/messages",
        "test_method": "simple_message",
        "models": {
            "claude-3-opus-20240229": {
                "display_name": "Claude 3 Opus",
                "description": "Anthropic最强大的模型，适用于复杂推理",
                "type": "chat",
                "context_window": 200000,
                "max_tokens": 4096,
                "price_per_1k_tokens": {"input": 0.015, "output": 0.075},
                "features": ["超长上下文", "复杂推理", "创意写作", "多语言"]
            },
            "claude-3-sonnet-20240229": {
                "display_name": "Claude 3 Sonnet",
                "description": "平衡性能和成本的模型",
                "type": "chat",
                "context_window": 200000,
                "max_tokens": 4096,
                "price_per_1k_tokens": {"input": 0.003, "output": 0.015},
                "features": ["长上下文", "平衡性能", "多语言"]
            },
            "claude-3-haiku-20240307": {
                "display_name": "Claude 3 Haiku",
                "description": "快速且经济的对话模型",
                "type": "chat",
                "context_window": 200000,
                "max_tokens": 4096,
                "price_per_1k_tokens": {"input": 0.0008, "output": 0.004},
                "features": ["快速响应", "高性价比", "多语言"]
            }
        }
    },
    "deepseek": {
        "display_name": "DeepSeek",
        "description": "DeepSeek是一家专注于AI大模型技术的公司，提供对话和代码模型",
        "logo_url": "/images/providers/deepseek.png",
        "base_url": "https://api.deepseek.com",
        "api_key_pattern": r"^sk-[A-Za-z0-9]{32}$",
        "test_endpoint": "/v1/models",
        "test_method": "model_list",
        "models": {
            "deepseek-chat": {
                "display_name": "DeepSeek Chat",
                "description": "DeepSeek通用对话模型，适用于日常对话和问答",
                "type": "chat",
                "context_window": 32768,
                "max_tokens": 4096,
                "price_per_1k_tokens": {"input": 0.0014, "output": 0.0028},
                "features": ["对话", "推理", "多语言", "问答"]
            },
            "deepseek-coder": {
                "display_name": "DeepSeek Coder",
                "description": "专门用于代码生成、调试和编程任务的模型",
                "type": "chat",
                "context_window": 32768,
                "max_tokens": 4096,
                "price_per_1k_tokens": {"input": 0.0014, "output": 0.0028},
                "features": ["代码生成", "代码解释", "编程问答", "调试"]
            }
        }
    },
    "google": {
        "display_name": "Google AI",
        "description": "Google AI提供Gemini系列多模态模型",
        "logo_url": "/images/providers/google.png",
        "base_url": "https://generativelanguage.googleapis.com",
        "api_key_pattern": r"^[A-Za-z0-9\-_]{39}$",
        "test_endpoint": "/v1/models",
        "test_method": "model_list",
        "models": {
            "gemini-pro": {
                "display_name": "Gemini Pro",
                "description": "Google的先进多模态模型",
                "type": "chat",
                "context_window": 30720,
                "max_tokens": 2048,
                "price_per_1k_tokens": {"input": 0.0005, "output": 0.0015},
                "features": ["多模态", "推理", "多语言"]
            },
            "gemini-pro-vision": {
                "display_name": "Gemini Pro Vision",
                "description": "支持图像理解的多模态模型",
                "type": "multimodal",
                "context_window": 30720,
                "max_tokens": 2048,
                "price_per_1k_tokens": {"input": 0.0005, "output": 0.0015},
                "features": ["图像理解", "多模态", "推理"]
            }
        }
    },
    "azure": {
        "display_name": "Azure OpenAI",
        "description": "Azure托管的OpenAI模型服务",
        "logo_url": "/images/providers/azure.png",
        "base_url": None,  # 需要自定义
        "api_key_pattern": r"^[A-Za-z0-9]{32}$",
        "test_endpoint": "/openai/deployments",
        "test_method": "deployment_list",
        "models": {
            "gpt-4": {
                "display_name": "GPT-4 (Azure)",
                "description": "Azure托管的GPT-4模型",
                "type": "chat",
                "context_window": 8192,
                "max_tokens": 4096,
                "price_per_1k_tokens": {"input": 0.03, "output": 0.06},
                "features": ["企业级", "数据隐私", "复杂推理"]
            },
            "gpt-35-turbo": {
                "display_name": "GPT-3.5 Turbo (Azure)",
                "description": "Azure托管的GPT-3.5模型",
                "type": "chat",
                "context_window": 4096,
                "max_tokens": 2048,
                "price_per_1k_tokens": {"input": 0.001, "output": 0.002},
                "features": ["企业级", "数据隐私", "高性价比"]
            }
        }
    },
    "custom": {
        "display_name": "自定义供应商",
        "description": "用户自定义的AI模型供应商",
        "logo_url": "/images/providers/custom.png",
        "base_url": None,  # 需要自定义
        "api_key_pattern": None,  # 不验证格式
        "test_endpoint": "/v1/models",
        "test_method": "model_list",
        "models": {}  # 动态获取
    }
}


# ===== EINO服务专用模型 =====

class CredentialSelectorRequest(BaseSchema):
    """凭证选择器请求模型"""
    
    strategy: str = Field(
        default="first_available",
        description="选择策略: first_available, round_robin, least_used"
    )
    only_active: bool = Field(
        default=True,
        description="仅返回活跃凭证"
    )
    providers: Optional[List[str]] = Field(
        default=None,
        description="供应商过滤列表"
    )


class SupplierCredentialInternalResponse(BaseSchema):
    """供应商凭证内部响应模型（包含解密的API密钥）"""
    
    id: uuid.UUID = Field(..., description="凭证ID")
    tenant_id: uuid.UUID = Field(..., description="租户ID")
    provider_name: str = Field(..., description="供应商名称")
    display_name: str = Field(..., description="显示名称")
    api_key: str = Field(..., description="解密的API密钥")
    base_url: Optional[str] = Field(None, description="基础URL")
    model_configs: Dict[str, Any] = Field(default_factory=dict, description="模型配置")
    is_active: bool = Field(..., description="是否激活")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class CredentialTestRequest(BaseSchema):
    """凭证测试请求模型"""
    
    tenant_id: str = Field(..., description="租户ID")
    test_type: str = Field(
        default="connection",
        description="测试类型: connection, model_list, simple_chat"
    )
    model_name: Optional[str] = Field(
        default=None,
        description="测试模型名称"
    )


class CredentialTestResponse(BaseSchema):
    """凭证测试响应模型"""
    
    success: bool = Field(..., description="测试是否成功")
    test_type: str = Field(..., description="测试类型")
    response_time_ms: int = Field(..., description="响应时间（毫秒）")
    error_message: Optional[str] = Field(None, description="错误信息")
    result_data: Optional[Dict[str, Any]] = Field(None, description="测试结果数据")


class ActiveTenantsResponse(BaseSchema):
    """活跃租户响应模型"""
    
    tenant_ids: List[str] = Field(..., description="活跃租户ID列表")


class ToolConfigResponse(BaseSchema):
    """工具配置响应模型"""
    
    tenant_id: str = Field(..., description="租户ID")
    workflow_name: str = Field(..., description="工作流名称")
    tool_name: str = Field(..., description="工具名称")
    is_enabled: bool = Field(..., description="是否启用")
    config_params: Dict[str, Any] = Field(default_factory=dict, description="配置参数")