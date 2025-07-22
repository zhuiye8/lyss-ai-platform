"""
通用API模型

定义通用的请求和响应模型，包括分页、状态等基础模型。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

from typing import Optional, Any, List, Dict, Generic, TypeVar
from datetime import datetime
from pydantic import BaseModel, Field

T = TypeVar('T')


class BaseResponse(BaseModel):
    """基础响应模型"""
    success: bool = Field(True, description="操作是否成功")
    message: str = Field("操作成功", description="响应消息")
    request_id: Optional[str] = Field(None, description="请求追踪ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="响应时间")


class ErrorResponse(BaseResponse):
    """错误响应模型"""
    success: bool = Field(False, description="操作失败")
    error_code: Optional[str] = Field(None, description="错误代码")
    error_details: Optional[Dict[str, Any]] = Field(None, description="错误详情")


class DataResponse(BaseResponse, Generic[T]):
    """数据响应模型"""
    data: T = Field(..., description="响应数据")


class PaginatedResponse(BaseResponse, Generic[T]):
    """分页响应模型"""
    data: List[T] = Field(..., description="数据列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")
    pages: int = Field(..., description="总页数")
    
    @property
    def has_next(self) -> bool:
        """是否有下一页"""
        return self.page < self.pages
    
    @property
    def has_prev(self) -> bool:
        """是否有上一页"""
        return self.page > 1


class PaginationRequest(BaseModel):
    """分页请求模型"""
    page: int = Field(1, ge=1, le=1000, description="页码，从1开始")
    size: int = Field(20, ge=1, le=100, description="每页大小，最大100")
    sort_by: Optional[str] = Field(None, description="排序字段")
    sort_order: Optional[str] = Field("desc", regex="^(asc|desc)$", description="排序方向")


class StatusRequest(BaseModel):
    """状态变更请求模型"""
    status: str = Field(..., regex="^(active|inactive|disabled)$", description="状态值")


class HealthCheckResponse(BaseModel):
    """健康检查响应模型"""
    status: str = Field("healthy", description="服务状态")
    service: str = Field("lyss-provider-service", description="服务名称")
    version: str = Field("1.0.0", description="服务版本")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="检查时间")
    database: bool = Field(True, description="数据库连接状态")
    redis: bool = Field(True, description="Redis连接状态")
    provider_count: int = Field(0, description="已注册供应商数量")
    channel_count: int = Field(0, description="活跃Channel数量")


class MetricsResponse(BaseModel):
    """指标统计响应模型"""
    total_requests: int = Field(0, description="总请求数")
    successful_requests: int = Field(0, description="成功请求数")
    failed_requests: int = Field(0, description="失败请求数")
    avg_response_time: float = Field(0.0, description="平均响应时间(ms)")
    success_rate: float = Field(0.0, description="成功率")
    active_channels: int = Field(0, description="活跃Channel数")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="统计时间")


class BatchOperationRequest(BaseModel):
    """批量操作请求模型"""
    ids: List[int] = Field(..., min_items=1, max_items=100, description="操作的ID列表")
    operation: str = Field(..., regex="^(enable|disable|delete)$", description="操作类型")


class BatchOperationResponse(BaseModel):
    """批量操作响应模型"""
    success_count: int = Field(0, description="成功操作数量")
    failed_count: int = Field(0, description="失败操作数量")
    failed_items: List[Dict[str, Any]] = Field([], description="失败项详情")
    total_count: int = Field(0, description="总操作数量")
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_count == 0:
            return 0.0
        return self.success_count / self.total_count