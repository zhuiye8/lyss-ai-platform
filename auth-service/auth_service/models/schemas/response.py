"""
Auth Service 统一响应模式定义
严格遵循 docs/STANDARDS.md 中的API响应规范
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field
from datetime import datetime

# 泛型类型变量
T = TypeVar("T")


class ErrorDetail(BaseModel):
    """错误详情模型"""

    code: str = Field(..., description="错误代码")
    message: str = Field(..., description="错误描述")
    details: Optional[Dict[str, Any]] = Field(None, description="详细错误信息")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "2001",
                "message": "用户未认证，请先登录",
                "details": {
                    "field": "authorization",
                    "reason": "JWT令牌已过期"
                }
            }
        }


class ApiResponse(BaseModel, Generic[T]):
    """统一API响应模型"""

    success: bool = Field(..., description="操作是否成功")
    data: Optional[T] = Field(None, description="响应数据")
    message: Optional[str] = Field(None, description="响应消息")
    request_id: str = Field(..., description="请求追踪ID")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="响应时间戳",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {"user_id": "uuid", "name": "用户名"},
                "message": "操作成功",
                "request_id": "req-20250710143025-a1b2c3d4",
                "timestamp": "2025-07-10T10:30:00Z"
            }
        }


class ErrorResponse(BaseModel):
    """错误响应模型"""

    success: bool = Field(default=False, description="操作是否成功")
    error: ErrorDetail = Field(..., description="错误信息")
    request_id: str = Field(..., description="请求追踪ID")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="响应时间戳",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": {
                    "code": "2001",
                    "message": "用户未认证，请先登录",
                    "details": {
                        "field": "authorization",
                        "reason": "JWT令牌已过期"
                    }
                },
                "request_id": "req-20250710143025-a1b2c3d4",
                "timestamp": "2025-07-10T10:30:00Z"
            }
        }


class SuccessResponse(BaseModel):
    """成功响应模型（无数据）"""

    success: bool = Field(default=True, description="操作是否成功")
    message: str = Field(..., description="成功消息")
    request_id: str = Field(..., description="请求追踪ID")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="响应时间戳",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "登出成功",
                "request_id": "req-20250710143025-a1b2c3d4",
                "timestamp": "2025-07-10T10:30:00Z"
            }
        }


class HealthResponse(BaseModel):
    """健康检查响应模型"""

    status: str = Field(..., description="服务状态")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="检查时间戳",
    )
    version: str = Field(default="1.0.0", description="服务版本")
    dependencies: Dict[str, str] = Field(
        default_factory=dict, description="依赖服务状态"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-07-10T10:30:00Z",
                "version": "1.0.0",
                "dependencies": {
                    "tenant_service": "healthy",
                    "redis": "healthy"
                }
            }
        }