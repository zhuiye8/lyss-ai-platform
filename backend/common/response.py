"""
统一API响应格式工具
确保所有API响应都符合约定的格式规范
"""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from fastapi import Request
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """错误详情模型"""
    code: str
    message: str
    field: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ApiResponse(BaseModel):
    """API响应模型"""
    success: bool
    data: Optional[Any] = None
    message: str
    request_id: Optional[str] = None
    timestamp: str
    errors: List[ErrorDetail] = []


class ResponseHelper:
    """响应帮助类"""
    
    @staticmethod
    def success(
        data: Any = None,
        message: str = "操作成功",
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建成功响应"""
        return {
            "success": True,
            "data": data,
            "message": message,
            "request_id": request_id or str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "errors": []
        }
    
    @staticmethod
    def error(
        message: str = "操作失败",
        errors: Optional[List[ErrorDetail]] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建错误响应"""
        return {
            "success": False,
            "data": None,
            "message": message,
            "request_id": request_id or str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "errors": errors or []
        }
    
    @staticmethod
    def validation_error(
        message: str = "请求参数验证失败",
        validation_errors: Optional[List[Dict[str, Any]]] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建验证错误响应"""
        errors = []
        if validation_errors:
            for error in validation_errors:
                errors.append(ErrorDetail(
                    code="VALIDATION_ERROR",
                    message=error.get("message", "验证失败"),
                    field=error.get("field"),
                    details=error.get("details")
                ))
        
        return {
            "success": False,
            "data": None,
            "message": message,
            "request_id": request_id or str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "errors": errors
        }
    
    @staticmethod
    def unauthorized(
        message: str = "未授权访问",
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建未授权响应"""
        return {
            "success": False,
            "data": None,
            "message": message,
            "request_id": request_id or str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "errors": [
                ErrorDetail(
                    code="UNAUTHORIZED",
                    message=message
                )
            ]
        }
    
    @staticmethod
    def forbidden(
        message: str = "权限不足",
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建禁止访问响应"""
        return {
            "success": False,
            "data": None,
            "message": message,
            "request_id": request_id or str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "errors": [
                ErrorDetail(
                    code="FORBIDDEN",
                    message=message
                )
            ]
        }
    
    @staticmethod
    def not_found(
        message: str = "资源不存在",
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建资源不存在响应"""
        return {
            "success": False,
            "data": None,
            "message": message,
            "request_id": request_id or str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "errors": [
                ErrorDetail(
                    code="NOT_FOUND",
                    message=message
                )
            ]
        }
    
    @staticmethod
    def rate_limit_exceeded(
        message: str = "请求频率过高",
        limit: int = 60,
        remaining: int = 0,
        reset_time: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建速率限制响应"""
        return {
            "success": False,
            "data": None,
            "message": message,
            "request_id": request_id or str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "errors": [
                ErrorDetail(
                    code="RATE_LIMIT_EXCEEDED",
                    message=message,
                    details={
                        "limit": limit,
                        "remaining": remaining,
                        "reset_time": reset_time
                    }
                )
            ]
        }
    
    @staticmethod
    def internal_server_error(
        message: str = "内部服务器错误",
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建内部服务器错误响应"""
        return {
            "success": False,
            "data": None,
            "message": message,
            "request_id": request_id or str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "errors": [
                ErrorDetail(
                    code="INTERNAL_SERVER_ERROR",
                    message=message
                )
            ]
        }
    
    @staticmethod
    def from_request(
        request: Request,
        success: bool = True,
        data: Any = None,
        message: str = "操作成功",
        errors: Optional[List[ErrorDetail]] = None
    ) -> Dict[str, Any]:
        """从请求对象创建响应"""
        request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
        
        return {
            "success": success,
            "data": data,
            "message": message,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "errors": errors or []
        }


def format_response(
    success: bool = True,
    data: Any = None,
    message: str = "操作成功",
    errors: Optional[List[ErrorDetail]] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """格式化响应的便捷函数"""
    return {
        "success": success,
        "data": data,
        "message": message,
        "request_id": request_id or str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "errors": errors or []
    }


def success_response(
    data: Any = None,
    message: str = "操作成功",
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """成功响应的便捷函数"""
    return ResponseHelper.success(data, message, request_id)


def error_response(
    message: str = "操作失败",
    errors: Optional[List[ErrorDetail]] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """错误响应的便捷函数"""
    return ResponseHelper.error(message, errors, request_id)


# 常用的错误代码常量
class ErrorCode:
    """错误代码常量"""
    
    # 认证相关
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    TOKEN_REVOKED = "TOKEN_REVOKED"
    
    # 授权相关
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    ACCOUNT_DISABLED = "ACCOUNT_DISABLED"
    
    # 验证相关
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    
    # 资源相关
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    
    # 限制相关
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    
    # 系统相关
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    DATABASE_ERROR = "DATABASE_ERROR"
    
    # 租户相关
    TENANT_NOT_FOUND = "TENANT_NOT_FOUND"
    TENANT_SUSPENDED = "TENANT_SUSPENDED"
    TENANT_QUOTA_EXCEEDED = "TENANT_QUOTA_EXCEEDED"