# -*- coding: utf-8 -*-
"""
基础Pydantic模型

定义通用的响应格式和基础验证模型
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

# 泛型类型变量
T = TypeVar('T')


class BaseSchema(BaseModel):
    """基础Schema类"""
    
    model_config = {
        "from_attributes": True,
        "arbitrary_types_allowed": True,
        "use_enum_values": True
    }


class IdSchema(BaseSchema):
    """包含ID的基础Schema"""
    
    id: uuid.UUID = Field(..., description="唯一标识符")


class TimestampSchema(BaseSchema):
    """包含时间戳的基础Schema"""
    
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class TenantAwareSchema(BaseSchema):
    """多租户感知Schema"""
    
    tenant_id: uuid.UUID = Field(..., description="租户ID")


class PaginationParams(BaseSchema):
    """分页参数"""
    
    page: int = Field(1, ge=1, description="页码，从1开始")
    page_size: int = Field(20, ge=1, le=100, description="每页数量，最大100")
    sort_by: Optional[str] = Field("created_at", description="排序字段")
    sort_order: Optional[str] = Field("desc", pattern="^(asc|desc)$", description="排序方向")


class PaginationInfo(BaseSchema):
    """分页信息"""
    
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    total_items: int = Field(..., description="总条目数")
    total_pages: int = Field(..., description="总页数")
    has_next: bool = Field(..., description="是否有下一页")
    has_prev: bool = Field(..., description="是否有上一页")


class PaginatedResponse(BaseSchema, Generic[T]):
    """分页响应"""
    
    items: List[T] = Field(..., description="数据列表")
    pagination: PaginationInfo = Field(..., description="分页信息")


class ApiResponse(BaseSchema, Generic[T]):
    """统一API响应格式"""
    
    success: bool = Field(True, description="操作是否成功")
    data: Optional[T] = Field(None, description="响应数据")
    message: Optional[str] = Field(None, description="响应消息")
    request_id: Optional[str] = Field(None, description="请求ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="响应时间")


class ErrorDetail(BaseSchema):
    """错误详情"""
    
    code: str = Field(..., description="错误代码")
    message: str = Field(..., description="错误消息")
    details: Optional[Dict[str, Any]] = Field(None, description="详细信息")


class ErrorResponse(BaseSchema):
    """错误响应格式"""
    
    success: bool = Field(False, description="操作是否成功")
    error: ErrorDetail = Field(..., description="错误信息")
    request_id: Optional[str] = Field(None, description="请求ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="响应时间")


class HealthCheckResponse(BaseSchema):
    """健康检查响应"""
    
    status: str = Field("healthy", description="服务状态")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="检查时间")
    version: str = Field("1.0.0", description="服务版本")
    dependencies: Dict[str, str] = Field(default_factory=dict, description="依赖服务状态")