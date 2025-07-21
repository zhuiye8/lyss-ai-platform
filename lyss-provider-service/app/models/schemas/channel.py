"""
Channel相关API模型

定义Channel管理相关的请求和响应模型。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
from .common import BaseResponse


class ChannelCreateRequest(BaseModel):
    """Channel创建请求模型"""
    name: str = Field(..., min_length=1, max_length=100, description="Channel名称")
    provider_id: str = Field(..., description="供应商ID")
    base_url: Optional[str] = Field(None, description="自定义API基础URL")
    credentials: Dict[str, Any] = Field(..., description="凭证信息")
    models: List[str] = Field(default_factory=list, description="支持的模型列表，为空则使用供应商默认模型")
    priority: int = Field(1, ge=0, le=100, description="优先级，数字越小优先级越高")
    weight: int = Field(100, ge=1, le=1000, description="负载均衡权重")
    max_requests_per_minute: int = Field(1000, ge=1, le=10000, description="每分钟最大请求数")
    config: Dict[str, Any] = Field(default_factory=dict, description="其他配置")
    
    @validator('name')
    def validate_name(cls, v):
        """验证Channel名称"""
        v = v.strip()
        if not v:
            raise ValueError('Channel名称不能为空')
        if len(v) < 2:
            raise ValueError('Channel名称至少需要2个字符')
        return v
    
    @validator('credentials')
    def validate_credentials(cls, v):
        """验证凭证"""
        if not v:
            raise ValueError('凭证信息不能为空')
        return v
    
    @validator('models')
    def validate_models(cls, v):
        """验证模型列表"""
        if v:
            # 去重并过滤空值
            v = list(set(model.strip() for model in v if model and model.strip()))
        return v


class ChannelUpdateRequest(BaseModel):
    """Channel更新请求模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Channel名称")
    base_url: Optional[str] = Field(None, description="自定义API基础URL")
    credentials: Optional[Dict[str, Any]] = Field(None, description="凭证信息")
    models: Optional[List[str]] = Field(None, description="支持的模型列表")
    priority: Optional[int] = Field(None, ge=0, le=100, description="优先级")
    weight: Optional[int] = Field(None, ge=1, le=1000, description="负载均衡权重")
    max_requests_per_minute: Optional[int] = Field(None, ge=1, le=10000, description="每分钟最大请求数")
    config: Optional[Dict[str, Any]] = Field(None, description="其他配置")
    status: Optional[str] = Field(None, regex="^(active|inactive|disabled)$", description="状态")


class ChannelResponse(BaseModel):
    """Channel响应模型"""
    id: int = Field(..., description="Channel ID")
    tenant_id: str = Field(..., description="租户ID")
    name: str = Field(..., description="Channel名称")
    provider_id: str = Field(..., description="供应商ID")
    provider_name: str = Field(..., description="供应商名称")
    base_url: str = Field(..., description="API基础URL")
    models: List[str] = Field(..., description="支持的模型列表")
    status: str = Field(..., description="状态")
    priority: int = Field(..., description="优先级")
    weight: int = Field(..., description="负载均衡权重")
    max_requests_per_minute: int = Field(..., description="每分钟最大请求数")
    health_status: str = Field("unknown", description="健康状态")
    masked_credentials: Dict[str, str] = Field(default_factory=dict, description="脱敏凭证")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    last_used_at: Optional[datetime] = Field(None, description="最后使用时间")
    
    class Config:
        orm_mode = True


class ChannelHealthStatus(BaseModel):
    """Channel健康状态"""
    channel_id: int = Field(..., description="Channel ID")
    is_healthy: bool = Field(..., description="是否健康")
    health_status: str = Field(..., description="健康状态")
    last_check_time: Optional[datetime] = Field(None, description="最后检查时间")
    response_time: float = Field(0.0, description="响应时间(ms)")
    error_message: Optional[str] = Field(None, description="错误信息")
    consecutive_failures: int = Field(0, description="连续失败次数")


class ChannelMetrics(BaseModel):
    """Channel性能指标"""
    channel_id: int = Field(..., description="Channel ID")
    total_requests: int = Field(0, description="总请求数")
    successful_requests: int = Field(0, description="成功请求数")
    failed_requests: int = Field(0, description="失败请求数")
    total_tokens: int = Field(0, description="总Token使用量")
    avg_response_time: float = Field(0.0, description="平均响应时间(ms)")
    success_rate: float = Field(0.0, description="成功率")
    requests_per_minute: float = Field(0.0, description="每分钟请求数")
    last_request_time: Optional[datetime] = Field(None, description="最后请求时间")
    last_success_time: Optional[datetime] = Field(None, description="最后成功时间")
    last_error_time: Optional[datetime] = Field(None, description="最后错误时间")


class ChannelDetailResponse(ChannelResponse):
    """Channel详情响应"""
    health: ChannelHealthStatus = Field(..., description="健康状态")
    metrics: ChannelMetrics = Field(..., description="性能指标")
    config: Dict[str, Any] = Field(default_factory=dict, description="其他配置")


class ChannelListResponse(BaseResponse):
    """Channel列表响应"""
    channels: List[ChannelResponse] = Field(..., description="Channel列表")
    total_count: int = Field(..., description="总数量")
    active_count: int = Field(..., description="活跃数量")
    healthy_count: int = Field(..., description="健康数量")


class ChannelTestRequest(BaseModel):
    """Channel连接测试请求"""
    test_model: Optional[str] = Field(None, description="测试模型")
    test_prompt: Optional[str] = Field("Hello", description="测试提示词")
    timeout: int = Field(30, ge=5, le=120, description="超时时间(秒)")


class ChannelTestResponse(BaseResponse):
    """Channel连接测试响应"""
    channel_id: int = Field(..., description="Channel ID")
    test_passed: bool = Field(..., description="测试是否通过")
    response_time: float = Field(..., description="响应时间(ms)")
    test_model: Optional[str] = Field(None, description="测试模型")
    test_response: Optional[str] = Field(None, description="测试响应")
    error_message: Optional[str] = Field(None, description="错误信息")
    test_timestamp: datetime = Field(default_factory=datetime.utcnow, description="测试时间")


class ChannelUsageRequest(BaseModel):
    """Channel使用统计请求"""
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")
    group_by: str = Field("day", regex="^(hour|day|week|month)$", description="分组方式")
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        """验证日期范围"""
        if v and 'start_date' in values and values['start_date']:
            if v <= values['start_date']:
                raise ValueError('结束日期必须大于开始日期')
        return v


class ChannelUsageStats(BaseModel):
    """Channel使用统计数据"""
    time_period: str = Field(..., description="时间段")
    requests: int = Field(0, description="请求数")
    successful_requests: int = Field(0, description="成功请求数") 
    failed_requests: int = Field(0, description="失败请求数")
    tokens: int = Field(0, description="Token使用量")
    avg_response_time: float = Field(0.0, description="平均响应时间")
    success_rate: float = Field(0.0, description="成功率")


class ChannelUsageResponse(BaseResponse):
    """Channel使用统计响应"""
    channel_id: int = Field(..., description="Channel ID")
    usage_stats: List[ChannelUsageStats] = Field(..., description="使用统计数据")
    summary: ChannelMetrics = Field(..., description="汇总指标")
    time_range: Dict[str, datetime] = Field(..., description="统计时间范围")


class ChannelBatchTestRequest(BaseModel):
    """Channel批量测试请求"""
    channel_ids: List[int] = Field(..., min_items=1, max_items=50, description="Channel ID列表")
    test_model: Optional[str] = Field(None, description="测试模型")
    timeout: int = Field(30, ge=5, le=120, description="超时时间(秒)")


class ChannelBatchTestResponse(BaseResponse):
    """Channel批量测试响应"""
    test_results: List[ChannelTestResponse] = Field(..., description="测试结果列表")
    success_count: int = Field(0, description="成功数量")
    failed_count: int = Field(0, description="失败数量")
    total_count: int = Field(0, description="总数量")