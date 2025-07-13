"""
基础HTTP客户端模块

提供与下游微服务通信的基础功能
"""

import asyncio
import time
from typing import Dict, Any, Optional, Union, List
from urllib.parse import urljoin
import httpx
from fastapi import Request, Response
from starlette.responses import StreamingResponse

from ..core.logging import get_logger, log_service_call
from ..utils.exceptions import ServiceUnavailableError, RequestTimeoutError, InternalServerError, DownstreamServiceError
from ..utils.helpers import build_service_url, mask_sensitive_data
from ..utils.constants import CUSTOM_HEADERS, HTTP_METHODS
from ..config import settings


logger = get_logger(__name__)


class BaseServiceClient:
    """基础服务客户端"""
    
    def __init__(self, service_name: str, base_url: str, timeout: int = 30):
        """
        初始化基础服务客户端
        
        Args:
            service_name: 服务名称
            base_url: 服务基础URL
            timeout: 请求超时时间
        """
        self.service_name = service_name
        self.base_url = base_url
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.client.aclose()
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()
    
    async def proxy_request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        json: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        request_id: Optional[str] = None
    ) -> Union[httpx.Response, StreamingResponse]:
        """
        代理请求到下游服务
        
        Args:
            method: HTTP方法
            path: 请求路径
            headers: 请求头
            params: 查询参数
            data: 请求体数据
            json: JSON数据
            files: 文件数据
            stream: 是否流式响应
            request_id: 请求ID
            
        Returns:
            HTTP响应或流式响应
            
        Raises:
            ServiceUnavailableError: 服务不可用
            RequestTimeoutError: 请求超时
            InternalServerError: 内部错误
        """
        start_time = time.time()
        
        # 构建完整URL
        full_url = build_service_url(self.base_url, path)
        
        # 准备请求头
        request_headers = self._prepare_headers(headers or {})
        
        # 记录请求开始
        logger.info(
            f"开始代理请求到 {self.service_name}",
            extra={
                "request_id": request_id,
                "target_service": self.service_name,
                "method": method,
                "path": path,
                "url": full_url,
                "operation": "proxy_request"
            }
        )
        
        try:
            # 发送HTTP请求
            response = await self.client.request(
                method=method,
                url=full_url,
                headers=request_headers,
                params=params,
                data=data,
                json=json,
                files=files,
                follow_redirects=True
            )
            
            # 计算耗时
            duration_ms = int((time.time() - start_time) * 1000)
            
            # 记录日志
            is_success = 200 <= response.status_code < 400
            log_service_call(
                logger,
                self.service_name,
                method,
                path,
                response.status_code,
                duration_ms,
                request_id,
                success=is_success,
                data={
                    "url": full_url,
                    "response_size": len(response.content) if response.content else 0
                }
            )
            
            # 对于错误响应，透传下游服务的错误信息
            if not is_success:
                await self._handle_downstream_error(response, full_url, request_id)
            
            # 如果是流式响应，返回StreamingResponse
            if stream or self._is_streaming_response(response):
                return await self._create_streaming_response(response)
            
            return response
            
        except httpx.TimeoutException:
            duration_ms = int((time.time() - start_time) * 1000)
            
            # 记录超时日志
            log_service_call(
                logger,
                self.service_name,
                method,
                path,
                504,
                duration_ms,
                request_id,
                success=False,
                error_message="请求超时"
            )
            
            raise RequestTimeoutError(
                f"请求 {self.service_name} 超时",
                details={"url": full_url, "timeout": self.timeout}
            )
            
        except httpx.ConnectError:
            duration_ms = int((time.time() - start_time) * 1000)
            
            # 记录连接错误日志
            log_service_call(
                logger,
                self.service_name,
                method,
                path,
                503,
                duration_ms,
                request_id,
                success=False,
                error_message="连接失败"
            )
            
            raise ServiceUnavailableError(
                self.service_name,
                f"无法连接到 {self.service_name}",
                details={"url": full_url}
            )
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            
            # 记录其他错误日志
            log_service_call(
                logger,
                self.service_name,
                method,
                path,
                500,
                duration_ms,
                request_id,
                success=False,
                error_message=str(e)
            )
            
            raise InternalServerError(
                f"请求 {self.service_name} 时发生错误: {str(e)}",
                details={"url": full_url, "error": str(e)}
            )
    
    async def _handle_downstream_error(
        self, 
        response: httpx.Response, 
        url: str, 
        request_id: Optional[str]
    ):
        """
        处理下游服务错误，透传具体的错误信息
        
        Args:
            response: 下游服务的错误响应
            url: 请求URL
            request_id: 请求ID
            
        Raises:
            DownstreamServiceError: 透传的下游服务错误
        """
        try:
            # 尝试解析下游服务的错误响应
            error_data = response.json()
            
            # 如果下游服务返回了符合我们规范的错误格式
            if isinstance(error_data, dict) and "error" in error_data:
                error_info = error_data["error"]
                error_code = error_info.get("code", "5003")
                error_message = error_info.get("message", "下游服务返回错误")
                error_details = error_info.get("details", {})
                
                # 记录下游服务错误
                logger.warning(
                    f"下游服务 {self.service_name} 返回业务错误",
                    extra={
                        "request_id": request_id,
                        "service": self.service_name,
                        "status_code": response.status_code,
                        "error_code": error_code,
                        "error_message": error_message,
                        "url": url
                    }
                )
                
                # 透传下游服务的错误
                raise DownstreamServiceError(
                    status_code=response.status_code,
                    error_code=error_code,
                    message=error_message,
                    details=error_details,
                    service_name=self.service_name
                )
            
            # 如果是其他格式的错误响应
            elif isinstance(error_data, dict) and "success" in error_data and not error_data["success"]:
                # 处理success:false格式的响应
                error_message = error_data.get("message", "下游服务返回错误")
                error_details = {"response": error_data}
                
                logger.warning(
                    f"下游服务 {self.service_name} 返回失败响应",
                    extra={
                        "request_id": request_id,
                        "service": self.service_name,
                        "status_code": response.status_code,
                        "error_message": error_message,
                        "url": url
                    }
                )
                
                raise DownstreamServiceError(
                    status_code=response.status_code,
                    error_code="5003",
                    message=error_message,
                    details=error_details,
                    service_name=self.service_name
                )
            
        except ValueError:
            # JSON解析失败，使用原始响应文本
            error_text = response.text
            
        except Exception as e:
            # 其他解析错误
            logger.error(
                f"解析下游服务 {self.service_name} 错误响应失败: {str(e)}",
                extra={
                    "request_id": request_id,
                    "service": self.service_name,
                    "url": url
                }
            )
            error_text = response.text or "未知错误"
        
        # 如果无法解析具体错误，创建通用错误
        logger.warning(
            f"下游服务 {self.service_name} 返回HTTP错误",
            extra={
                "request_id": request_id,
                "service": self.service_name,
                "status_code": response.status_code,
                "response_text": error_text[:500],  # 限制日志长度
                "url": url
            }
        )
        
        raise DownstreamServiceError(
            status_code=response.status_code,
            error_code="5003",
            message=f"下游服务 {self.service_name} 返回错误: {error_text[:100]}",
            details={"url": url, "response_status": response.status_code},
            service_name=self.service_name
        )
    
    def _prepare_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """
        准备请求头
        
        Args:
            headers: 原始请求头
            
        Returns:
            处理后的请求头
        """
        # 复制原始头部
        prepared_headers = dict(headers)
        
        # 确保有User-Agent
        if "User-Agent" not in prepared_headers:
            prepared_headers["User-Agent"] = f"lyss-api-gateway/1.0.0"
        
        # 确保有Accept头部
        if "Accept" not in prepared_headers:
            prepared_headers["Accept"] = "application/json"
        
        # 移除可能导致问题的头部
        headers_to_remove = ["Host", "Content-Length", "Connection"]
        for header in headers_to_remove:
            prepared_headers.pop(header, None)
        
        return prepared_headers
    
    def _is_streaming_response(self, response: httpx.Response) -> bool:
        """
        检查是否为流式响应
        
        Args:
            response: HTTP响应
            
        Returns:
            是否为流式响应
        """
        content_type = response.headers.get("content-type", "")
        return (
            "text/event-stream" in content_type or
            "application/x-ndjson" in content_type or
            "text/stream" in content_type
        )
    
    async def _create_streaming_response(self, response: httpx.Response) -> StreamingResponse:
        """
        创建流式响应
        
        Args:
            response: HTTP响应
            
        Returns:
            流式响应对象
        """
        async def generate():
            async for chunk in response.aiter_bytes():
                yield chunk
        
        return StreamingResponse(
            generate(),
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.headers.get("content-type", "application/octet-stream")
        )
    
    async def health_check(self, request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        健康检查
        
        Args:
            request_id: 请求ID
            
        Returns:
            健康检查结果
        """
        try:
            response = await self.proxy_request(
                "GET",
                "/health",
                request_id=request_id
            )
            
            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "service": self.service_name,
                    "response_time_ms": getattr(response, 'elapsed', 0),
                    "data": response.json() if response.content else {}
                }
            else:
                return {
                    "status": "unhealthy",
                    "service": self.service_name,
                    "status_code": response.status_code,
                    "error": response.text
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "service": self.service_name,
                "error": str(e)
            }


class ServiceClientManager:
    """服务客户端管理器"""
    
    def __init__(self):
        """初始化服务客户端管理器"""
        self.clients: Dict[str, BaseServiceClient] = {}
        self._initialize_clients()
    
    def _initialize_clients(self):
        """初始化所有服务客户端"""
        service_registry = settings.service_registry
        
        # 认证服务客户端
        self.clients["auth"] = BaseServiceClient(
            "auth_service",
            service_registry.auth_service,
            settings.request_timeout
        )
        
        # 租户服务客户端
        self.clients["tenant"] = BaseServiceClient(
            "tenant_service",
            service_registry.tenant_service,
            settings.request_timeout
        )
        
        # EINO服务客户端
        self.clients["eino"] = BaseServiceClient(
            "eino_service",
            service_registry.eino_service,
            settings.request_timeout
        )
        
        # 记忆服务客户端
        self.clients["memory"] = BaseServiceClient(
            "memory_service",
            service_registry.memory_service,
            settings.request_timeout
        )
    
    def get_client(self, service_name: str) -> BaseServiceClient:
        """
        获取服务客户端
        
        Args:
            service_name: 服务名称
            
        Returns:
            服务客户端实例
            
        Raises:
            ValueError: 服务不存在
        """
        if service_name not in self.clients:
            raise ValueError(f"未知的服务: {service_name}")
        
        return self.clients[service_name]
    
    async def close_all(self):
        """关闭所有客户端"""
        for client in self.clients.values():
            await client.close()
    
    async def health_check_all(self, request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        检查所有服务的健康状态
        
        Args:
            request_id: 请求ID
            
        Returns:
            所有服务的健康状态
        """
        results = {}
        
        # 并发检查所有服务
        tasks = [
            self.clients[service_name].health_check(request_id)
            for service_name in self.clients.keys()
        ]
        
        health_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, (service_name, result) in enumerate(zip(self.clients.keys(), health_results)):
            if isinstance(result, Exception):
                results[service_name] = {
                    "status": "unhealthy",
                    "service": service_name,
                    "error": str(result)
                }
            else:
                results[service_name] = result
        
        return results


# 全局服务客户端管理器
service_manager = ServiceClientManager()