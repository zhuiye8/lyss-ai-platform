"""
Auth Service 异常定义模块
定义认证服务专用的异常类型，遵循统一错误代码规范
"""

from typing import Any, Dict, Optional


class AuthServiceException(Exception):
    """认证服务基础异常类"""

    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}


class AuthenticationError(AuthServiceException):
    """认证失败异常"""

    def __init__(
        self,
        message: str = "认证失败",
        error_code: str = "2001",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=401,
            details=details,
        )


class TokenExpiredError(AuthServiceException):
    """令牌过期异常"""

    def __init__(
        self,
        message: str = "令牌已过期",
        error_code: str = "2002",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=401,
            details=details,
        )


class TokenInvalidError(AuthServiceException):
    """令牌无效异常"""

    def __init__(
        self,
        message: str = "令牌无效",
        error_code: str = "2003",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=401,
            details=details,
        )


class InvalidCredentialsError(AuthServiceException):
    """凭证无效异常"""

    def __init__(
        self,
        message: str = "用户名或密码错误",
        error_code: str = "3004",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=401,
            details=details,
        )


class UserNotFoundError(AuthServiceException):
    """用户不存在异常"""

    def __init__(
        self,
        message: str = "用户不存在",
        error_code: str = "3003",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=404,
            details=details,
        )


class RateLimitExceededError(AuthServiceException):
    """速率限制超限异常"""

    def __init__(
        self,
        message: str = "登录尝试次数过多，请稍后再试",
        error_code: str = "1005",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=429,
            details=details,
        )


class TenantServiceError(AuthServiceException):
    """租户服务调用异常"""

    def __init__(
        self,
        message: str = "租户服务调用失败",
        error_code: str = "4001",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=503,
            details=details,
        )


class RedisConnectionError(AuthServiceException):
    """Redis连接异常"""

    def __init__(
        self,
        message: str = "缓存服务连接失败",
        error_code: str = "5002",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=503,
            details=details,
        )