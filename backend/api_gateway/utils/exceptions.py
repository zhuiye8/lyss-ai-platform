"""
异常定义模块

定义API Gateway使用的自定义异常类
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException, status


class LyssAPIException(HTTPException):
    """Lyss平台API异常基类"""
    
    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        self.error_code = error_code
        self.error_message = message
        self.error_details = details or {}
        
        detail = {
            "error": {
                "code": error_code,
                "message": message,
                "details": self.error_details
            }
        }
        
        super().__init__(
            status_code=status_code,
            detail=detail,
            headers=headers
        )


class AuthenticationError(LyssAPIException):
    """认证错误"""
    
    def __init__(self, message: str = "认证失败", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="2001",
            message=message,
            details=details,
            headers={"WWW-Authenticate": "Bearer"}
        )


class TokenExpiredError(LyssAPIException):
    """令牌过期错误"""
    
    def __init__(self, message: str = "令牌已过期", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="2002",
            message=message,
            details=details,
            headers={"WWW-Authenticate": "Bearer"}
        )


class TokenInvalidError(LyssAPIException):
    """令牌无效错误"""
    
    def __init__(self, message: str = "令牌无效", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="2003",
            message=message,
            details=details,
            headers={"WWW-Authenticate": "Bearer"}
        )


class InsufficientPermissionsError(LyssAPIException):
    """权限不足错误"""
    
    def __init__(self, message: str = "权限不足", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="2004",
            message=message,
            details=details
        )


class ServiceUnavailableError(LyssAPIException):
    """服务不可用错误"""
    
    def __init__(self, service_name: str, message: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if not message:
            message = f"服务 {service_name} 不可用"
        
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="5004",
            message=message,
            details=details or {"service": service_name}
        )


class RequestTimeoutError(LyssAPIException):
    """请求超时错误"""
    
    def __init__(self, message: str = "请求超时", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            error_code="4003",
            message=message,
            details=details
        )


class InvalidInputError(LyssAPIException):
    """输入参数无效错误"""
    
    def __init__(self, message: str = "输入参数无效", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="1001",
            message=message,
            details=details
        )


class RateLimitExceededError(LyssAPIException):
    """请求频率超限错误"""
    
    def __init__(self, message: str = "请求频率超限", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="1005",
            message=message,
            details=details
        )


class InternalServerError(LyssAPIException):
    """内部服务器错误"""
    
    def __init__(self, message: str = "内部服务器错误", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="5003",
            message=message,
            details=details
        )