"""
错误处理中间件

统一处理API Gateway的异常和错误响应
"""

import traceback
from typing import Dict, Any, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from pydantic import ValidationError

from ..core.logging import get_logger
from ..utils.exceptions import LyssAPIException
from ..utils.helpers import build_error_response, mask_sensitive_data
from ..utils.constants import ERROR_CODES, DEFAULT_MESSAGES


logger = get_logger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """错误处理中间件"""
    
    async def dispatch(self, request: Request, call_next):
        """
        处理请求和异常
        
        Args:
            request: 请求对象
            call_next: 下一个中间件或路由处理器
            
        Returns:
            响应对象
        """
        try:
            response = await call_next(request)
            return response
            
        except LyssAPIException as e:
            # 处理自定义API异常
            return await self._handle_lyss_api_exception(request, e)
            
        except HTTPException as e:
            # 处理FastAPI HTTP异常
            return await self._handle_http_exception(request, e)
            
        except RequestValidationError as e:
            # 处理请求验证错误
            return await self._handle_validation_error(request, e)
            
        except ValidationError as e:
            # 处理Pydantic验证错误
            return await self._handle_pydantic_validation_error(request, e)
            
        except Exception as e:
            # 处理其他未知异常
            return await self._handle_unknown_exception(request, e)
    
    async def _handle_lyss_api_exception(
        self,
        request: Request,
        exc: LyssAPIException
    ) -> JSONResponse:
        """
        处理自定义API异常
        
        Args:
            request: 请求对象
            exc: 异常对象
            
        Returns:
            JSON错误响应
        """
        request_id = getattr(request.state, "request_id", "")
        
        # 记录异常日志
        logger.error(
            f"API异常: {exc.error_message}",
            extra={
                "request_id": request_id,
                "error_code": exc.error_code,
                "path": request.url.path,
                "method": request.method,
                "status_code": exc.status_code,
                "error_details": mask_sensitive_data(exc.error_details)
            }
        )
        
        # 构建错误响应
        error_response = build_error_response(
            error_code=exc.error_code,
            message=exc.error_message,
            details=exc.error_details,
            request_id=request_id
        )
        
        return JSONResponse(
            content=error_response,
            status_code=exc.status_code,
            headers=exc.headers
        )
    
    async def _handle_http_exception(
        self,
        request: Request,
        exc: HTTPException
    ) -> JSONResponse:
        """
        处理FastAPI HTTP异常
        
        Args:
            request: 请求对象
            exc: 异常对象
            
        Returns:
            JSON错误响应
        """
        request_id = getattr(request.state, "request_id", "")
        
        # 映射HTTP状态码到错误代码
        error_code = self._map_status_code_to_error_code(exc.status_code)
        
        # 记录异常日志
        logger.error(
            f"HTTP异常: {exc.detail}",
            extra={
                "request_id": request_id,
                "error_code": error_code,
                "path": request.url.path,
                "method": request.method,
                "status_code": exc.status_code
            }
        )
        
        # 构建错误响应
        error_response = build_error_response(
            error_code=error_code,
            message=str(exc.detail),
            details={"status_code": exc.status_code},
            request_id=request_id
        )
        
        return JSONResponse(
            content=error_response,
            status_code=exc.status_code,
            headers=exc.headers
        )
    
    async def _handle_validation_error(
        self,
        request: Request,
        exc: RequestValidationError
    ) -> JSONResponse:
        """
        处理请求验证错误
        
        Args:
            request: 请求对象
            exc: 异常对象
            
        Returns:
            JSON错误响应
        """
        request_id = getattr(request.state, "request_id", "")
        
        # 提取验证错误详情
        error_details = []
        for error in exc.errors():
            error_details.append({
                "field": ".".join(str(loc) for loc in error.get("loc", [])),
                "message": error.get("msg", ""),
                "type": error.get("type", ""),
                "input": error.get("input")
            })
        
        # 记录异常日志
        logger.warning(
            f"请求验证失败: {len(error_details)}个错误",
            extra={
                "request_id": request_id,
                "error_code": ERROR_CODES["INVALID_INPUT"],
                "path": request.url.path,
                "method": request.method,
                "validation_errors": error_details
            }
        )
        
        # 构建错误响应
        error_response = build_error_response(
            error_code=ERROR_CODES["INVALID_INPUT"],
            message=DEFAULT_MESSAGES["INVALID_INPUT"],
            details={"validation_errors": error_details},
            request_id=request_id
        )
        
        return JSONResponse(
            content=error_response,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )
    
    async def _handle_pydantic_validation_error(
        self,
        request: Request,
        exc: ValidationError
    ) -> JSONResponse:
        """
        处理Pydantic验证错误
        
        Args:
            request: 请求对象
            exc: 异常对象
            
        Returns:
            JSON错误响应
        """
        request_id = getattr(request.state, "request_id", "")
        
        # 提取验证错误详情
        error_details = []
        for error in exc.errors():
            error_details.append({
                "field": ".".join(str(loc) for loc in error.get("loc", [])),
                "message": error.get("msg", ""),
                "type": error.get("type", "")
            })
        
        # 记录异常日志
        logger.warning(
            f"数据验证失败: {len(error_details)}个错误",
            extra={
                "request_id": request_id,
                "error_code": ERROR_CODES["INVALID_FORMAT"],
                "path": request.url.path,
                "method": request.method,
                "validation_errors": error_details
            }
        )
        
        # 构建错误响应
        error_response = build_error_response(
            error_code=ERROR_CODES["INVALID_FORMAT"],
            message="数据格式验证失败",
            details={"validation_errors": error_details},
            request_id=request_id
        )
        
        return JSONResponse(
            content=error_response,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )
    
    async def _handle_unknown_exception(
        self,
        request: Request,
        exc: Exception
    ) -> JSONResponse:
        """
        处理未知异常
        
        Args:
            request: 请求对象
            exc: 异常对象
            
        Returns:
            JSON错误响应
        """
        request_id = getattr(request.state, "request_id", "")
        
        # 记录异常日志
        logger.error(
            f"未知异常: {str(exc)}",
            extra={
                "request_id": request_id,
                "error_code": ERROR_CODES["INTERNAL_SERVER_ERROR"],
                "path": request.url.path,
                "method": request.method,
                "exception_type": type(exc).__name__,
                "traceback": traceback.format_exc()
            }
        )
        
        # 构建错误响应
        error_response = build_error_response(
            error_code=ERROR_CODES["INTERNAL_SERVER_ERROR"],
            message=DEFAULT_MESSAGES["INTERNAL_ERROR"],
            details={
                "exception_type": type(exc).__name__,
                "error": str(exc)
            },
            request_id=request_id
        )
        
        return JSONResponse(
            content=error_response,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    def _map_status_code_to_error_code(self, status_code: int) -> str:
        """
        映射HTTP状态码到错误代码
        
        Args:
            status_code: HTTP状态码
            
        Returns:
            错误代码
        """
        mapping = {
            400: ERROR_CODES["INVALID_INPUT"],
            401: ERROR_CODES["UNAUTHORIZED"],
            403: ERROR_CODES["INSUFFICIENT_PERMISSIONS"],
            404: "3001",  # NOT_FOUND
            405: "1002",  # METHOD_NOT_ALLOWED
            409: "3005",  # CONFLICT
            413: ERROR_CODES["REQUEST_TOO_LARGE"],
            422: ERROR_CODES["INVALID_FORMAT"],
            429: ERROR_CODES["RATE_LIMIT_EXCEEDED"],
            500: ERROR_CODES["INTERNAL_SERVER_ERROR"],
            503: ERROR_CODES["SERVICE_UNAVAILABLE"],
            504: ERROR_CODES["REQUEST_TIMEOUT"]
        }
        
        return mapping.get(status_code, ERROR_CODES["INTERNAL_SERVER_ERROR"])


async def custom_http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    自定义HTTP异常处理器
    
    Args:
        request: 请求对象
        exc: 异常对象
        
    Returns:
        JSON错误响应
    """
    request_id = getattr(request.state, "request_id", "")
    
    # 构建错误响应
    error_response = build_error_response(
        error_code=str(exc.status_code),
        message=str(exc.detail),
        details={"status_code": exc.status_code},
        request_id=request_id
    )
    
    return JSONResponse(
        content=error_response,
        status_code=exc.status_code,
        headers=exc.headers
    )


async def custom_validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """
    自定义验证异常处理器
    
    Args:
        request: 请求对象
        exc: 异常对象
        
    Returns:
        JSON错误响应
    """
    request_id = getattr(request.state, "request_id", "")
    
    # 提取验证错误详情
    error_details = []
    for error in exc.errors():
        error_details.append({
            "field": ".".join(str(loc) for loc in error.get("loc", [])),
            "message": error.get("msg", ""),
            "type": error.get("type", "")
        })
    
    # 构建错误响应
    error_response = build_error_response(
        error_code=ERROR_CODES["INVALID_INPUT"],
        message="请求参数验证失败",
        details={"validation_errors": error_details},
        request_id=request_id
    )
    
    return JSONResponse(
        content=error_response,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
    )