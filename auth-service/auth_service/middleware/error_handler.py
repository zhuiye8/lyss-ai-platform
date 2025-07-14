"""
Auth Service 全局错误处理中间件
处理所有异常并返回统一格式的错误响应
"""

import traceback
from typing import Union

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..core.exceptions import AuthServiceException
from ..models.schemas.response import ErrorResponse, ErrorDetail
from ..middleware.request_logging import request_id_var
from ..utils.logging import logger


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """全局错误处理中间件"""

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            return await self._handle_exception(request, e)

    async def _handle_exception(self, request: Request, exc: Exception) -> JSONResponse:
        """
        处理异常并返回统一格式的错误响应

        Args:
            request: FastAPI请求对象
            exc: 捕获的异常

        Returns:
            JSONResponse: 标准化的错误响应
        """
        # 获取请求ID
        try:
            request_id = request_id_var.get()
        except LookupError:
            request_id = "unknown"

        # 处理Auth Service自定义异常
        if isinstance(exc, AuthServiceException):
            error_detail = ErrorDetail(
                code=exc.error_code,
                message=exc.message,
                details=exc.details,
            )

            # 记录错误日志
            logger.error(
                f"业务异常: {exc.message}",
                operation="business_exception",
                error_code=exc.error_code,
                data={
                    "exception_type": type(exc).__name__,
                    "details": exc.details,
                    "path": request.url.path,
                    "method": request.method,
                },
            )

            return JSONResponse(
                status_code=exc.status_code,
                content=ErrorResponse(
                    error=error_detail,
                    request_id=request_id,
                ).dict(),
            )

        # 处理FastAPI HTTPException
        elif isinstance(exc, HTTPException):
            error_detail = ErrorDetail(
                code=str(exc.status_code),
                message=exc.detail if isinstance(exc.detail, str) else "HTTP错误",
                details={"status_code": exc.status_code} if not isinstance(exc.detail, str) else None,
            )

            # 记录错误日志
            logger.error(
                f"HTTP异常: {exc.detail}",
                operation="http_exception",
                error_code=str(exc.status_code),
                data={
                    "status_code": exc.status_code,
                    "detail": exc.detail,
                    "path": request.url.path,
                    "method": request.method,
                },
            )

            return JSONResponse(
                status_code=exc.status_code,
                content=ErrorResponse(
                    error=error_detail,
                    request_id=request_id,
                ).dict(),
            )

        # 处理其他未捕获的异常
        else:
            # 生成错误详情
            error_detail = ErrorDetail(
                code="5003",  # INTERNAL_SERVER_ERROR
                message="服务器内部错误",
                details={
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                } if request.app.debug else None,  # 只在DEBUG模式下暴露详细错误
            )

            # 记录详细错误日志
            logger.error(
                f"未捕获异常: {str(exc)}",
                operation="unhandled_exception",
                error_code="5003",
                data={
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                    "traceback": traceback.format_exc(),
                    "path": request.url.path,
                    "method": request.method,
                },
            )

            return JSONResponse(
                status_code=500,
                content=ErrorResponse(
                    error=error_detail,
                    request_id=request_id,
                ).dict(),
            )