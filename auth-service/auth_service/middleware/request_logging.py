"""
Auth Service 请求日志中间件
记录所有HTTP请求和响应的详细信息
"""

import time
import uuid
from contextvars import ContextVar
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..utils.logging import logger

# 请求上下文变量
request_id_var: ContextVar[str] = ContextVar("request_id")
tenant_id_var: ContextVar[str] = ContextVar("tenant_id")
user_id_var: ContextVar[str] = ContextVar("user_id")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志记录中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 生成或获取请求ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            timestamp = str(int(time.time() * 1000))
            short_uuid = str(uuid.uuid4())[:8]
            request_id = f"req-{timestamp}-{short_uuid}"

        # 设置请求上下文
        request_id_var.set(request_id)

        # 记录请求开始时间
        start_time = time.time()

        # 提取客户端信息
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")
        method = request.method
        url = str(request.url)
        path = request.url.path

        # 记录请求开始
        logger.info(
            f"请求开始: {method} {path}",
            operation="request_start",
            data={
                "method": method,
                "url": url,
                "path": path,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "headers": dict(request.headers) if logger.logger.isEnabledFor(10) else None,  # DEBUG级别才记录headers
            }
        )

        try:
            # 处理请求
            response = await call_next(request)

            # 计算处理时间
            duration_ms = int((time.time() - start_time) * 1000)

            # 记录请求完成
            logger.info(
                f"请求完成: {method} {path} - {response.status_code}",
                operation="request_end",
                data={
                    "method": method,
                    "path": path,
                    "status_code": response.status_code,
                    "client_ip": client_ip,
                },
                duration_ms=duration_ms,
                success=200 <= response.status_code < 400,
            )

            # 添加响应头
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            # 计算处理时间
            duration_ms = int((time.time() - start_time) * 1000)

            # 记录请求异常
            logger.error(
                f"请求异常: {method} {path}",
                operation="request_error",
                data={
                    "method": method,
                    "path": path,
                    "client_ip": client_ip,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                duration_ms=duration_ms,
            )

            # 重新抛出异常
            raise

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端真实IP地址"""
        # 检查反向代理头部
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # X-Forwarded-For可能包含多个IP，取第一个
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # 使用客户端直连IP
        if request.client:
            return request.client.host

        return "unknown"