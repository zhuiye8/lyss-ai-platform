"""
供应商相关API模型

定义供应商管理相关的请求和响应模型。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
from .common import BaseResponse


class ProviderCredentialField(BaseModel):
    """供应商凭证字段定义"""
    name: str = Field(..., description="字段名称")
    type: str = Field(..., description="字段类型")
    required: bool = Field(True, description="是否必填")
    sensitive: bool = Field(False, description="是否敏感信息")
    label: str = Field(..., description="字段标签")
    placeholder: Optional[str] = Field(None, description="占位符")
    description: Optional[str] = Field(None, description="字段描述")
    default: Optional[str] = Field(None, description="默认值")
    validation: Optional[Dict[str, Any]] = Field(None, description="验证规则")


class ProviderModel(BaseModel):
    """供应商模型定义"""
    model_id: str = Field(..., description="模型标识符")
    name: str = Field(..., description="模型名称") 
    type: str = Field(..., description="模型类型")
    max_tokens: int = Field(..., description="最大Token数")
    supports_stream: bool = Field(True, description="是否支持流式响应")
    pricing: Dict[str, float] = Field({}, description="定价信息")
    capabilities: List[str] = Field([], description="模型能力")


class ProviderConfigSchema(BaseModel):
    """供应商配置Schema"""
    provider_id: str = Field(..., description="供应商ID")
    name: str = Field(..., description="供应商名称")
    description: Optional[str] = Field(None, description="供应商描述")
    icon: Optional[str] = Field(None, description="图标")
    base_url: str = Field(..., description="API基础URL")
    auth_type: str = Field(..., description="认证类型")
    credential_fields: List[ProviderCredentialField] = Field(..., description="凭证字段定义")
    supported_models: List[ProviderModel] = Field(..., description="支持的模型")
    default_config: Dict[str, Any] = Field({}, description="默认配置")
    error_mapping: Dict[str, List[str]] = Field({}, description="错误映射")


class ProviderResponse(BaseModel):
    """供应商基础响应模型"""
    provider_id: str = Field(..., description="供应商ID")
    name: str = Field(..., description="供应商名称")
    description: Optional[str] = Field(None, description="供应商描述")
    base_url: str = Field(..., description="API基础URL")
    auth_type: str = Field(..., description="认证类型")
    supported_models: List[str] = Field(..., description="支持的模型列表")
    status: str = Field(..., description="状态")
    has_credentials: bool = Field(False, description="是否已配置凭证")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class ProviderCredentialsRequest(BaseModel):
    """供应商凭证配置请求"""
    credentials: Dict[str, Any] = Field(..., description="凭证信息")
    
    @validator('credentials')
    def validate_credentials(cls, v):
        """验证凭证格式"""
        if not v:
            raise ValueError('凭证信息不能为空')
        
        # 检查是否包含敏感信息标识
        sensitive_keys = ['api_key', 'secret', 'password', 'token']
        has_sensitive = any(key in str(v).lower() for key in sensitive_keys)
        if not has_sensitive:
            raise ValueError('凭证信息格式不正确')
        
        return v


class ProviderCredentialsResponse(BaseResponse):
    """供应商凭证配置响应"""
    provider_id: str = Field(..., description="供应商ID")
    masked_credentials: Dict[str, str] = Field(..., description="脱敏后的凭证信息")
    test_result: Dict[str, Any] = Field(..., description="连接测试结果")


class ProviderTestRequest(BaseModel):
    """供应商连接测试请求"""
    provider_id: str = Field(..., description="供应商ID")
    credentials: Dict[str, Any] = Field(..., description="测试凭证")
    model: Optional[str] = Field(None, description="测试模型")


class ProviderTestResponse(BaseResponse):
    """供应商连接测试响应"""
    provider_id: str = Field(..., description="供应商ID") 
    test_passed: bool = Field(..., description="测试是否通过")
    response_time: float = Field(..., description="响应时间(ms)")
    test_model: Optional[str] = Field(None, description="测试使用的模型")
    error_message: Optional[str] = Field(None, description="错误信息")
    test_details: Dict[str, Any] = Field({}, description="测试详情")


class ProviderModelsResponse(BaseResponse):
    """供应商模型列表响应"""
    provider_id: str = Field(..., description="供应商ID")
    models: List[ProviderModel] = Field(..., description="模型列表")
    total_count: int = Field(..., description="模型总数")


class ProviderUsageStats(BaseModel):
    """供应商使用统计"""
    provider_id: str = Field(..., description="供应商ID")
    total_requests: int = Field(0, description="总请求数")
    successful_requests: int = Field(0, description="成功请求数")
    failed_requests: int = Field(0, description="失败请求数")
    total_tokens: int = Field(0, description="总Token使用量")
    avg_response_time: float = Field(0.0, description="平均响应时间")
    success_rate: float = Field(0.0, description="成功率")
    active_channels: int = Field(0, description="活跃Channel数")
    last_request_time: Optional[datetime] = Field(None, description="最后请求时间")


class ProviderUsageResponse(BaseResponse):
    """供应商使用统计响应"""
    usage_stats: List[ProviderUsageStats] = Field(..., description="使用统计")
    time_range: Dict[str, datetime] = Field(..., description="统计时间范围")


class ProviderListResponse(BaseResponse):
    """供应商列表响应"""
    providers: List[ProviderResponse] = Field(..., description="供应商列表")
    total_count: int = Field(..., description="总数量")
    available_count: int = Field(..., description="可用数量")
    configured_count: int = Field(..., description="已配置数量")