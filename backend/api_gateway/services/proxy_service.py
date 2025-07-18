"""
代理服务模块

负责请求路由和转发逻辑
"""

import time
from typing import Dict, Any, Optional, Union, Tuple
from urllib.parse import urlparse, parse_qs
from fastapi import Request, Response
from starlette.responses import StreamingResponse

from .base_client import service_manager
from ..core.logging import get_logger, log_api_request
from ..utils.exceptions import ServiceUnavailableError, InvalidInputError
from ..utils.helpers import extract_path_without_prefix, mask_sensitive_data
from ..utils.constants import ROUTE_PREFIXES, HTTP_METHODS
from ..config import settings


logger = get_logger(__name__)


class ProxyService:
    """代理服务"""
    
    def __init__(self):
        """初始化代理服务"""
        self.route_config = settings.route_config
    
    async def route_request(
        self,
        request: Request,
        path: str,
        method: str
    ) -> Union[Response, StreamingResponse]:
        """
        路由请求到对应的微服务
        
        Args:
            request: FastAPI请求对象
            path: 请求路径
            method: HTTP方法
            
        Returns:
            HTTP响应或流式响应
            
        Raises:
            ServiceUnavailableError: 服务不可用
            InvalidInputError: 无效的路径
        """
        start_time = time.time()
        request_id = getattr(request.state, "request_id", "")
        user_info = getattr(request.state, "user_info", {})
        
        # 查找匹配的路由配置
        route_config = self._find_matching_route(path)
        if not route_config:
            raise InvalidInputError(
                f"未找到匹配的路由: {path}",
                details={"path": path, "method": method}
            )
        
        # 获取目标服务客户端
        service_client = self._get_service_client(route_config["service_name"])
        
        # 提取目标路径
        target_path = self._extract_target_path(path, route_config)
        
        # 准备请求头
        headers = await self._prepare_request_headers(request, user_info, request_id)
        
        # 获取请求参数
        params = dict(request.query_params)
        
        # 获取请求体
        body_data = await self._get_request_body(request)
        
        # 检查是否为流式请求
        is_stream = self._is_stream_request(request)
        
        try:
            # 发送代理请求
            response = await service_client.proxy_request(
                method=method,
                path=target_path,
                headers=headers,
                params=params,
                **body_data,
                stream=is_stream,
                request_id=request_id
            )
            
            # 计算耗时
            duration_ms = int((time.time() - start_time) * 1000)
            
            # 记录成功日志
            log_api_request(
                logger,
                method,
                path,
                response.status_code if hasattr(response, 'status_code') else 200,
                duration_ms,
                request_id,
                user_info.get("user_id"),
                user_info.get("tenant_id"),
                route_config["service_name"],
                success=True,
                data={
                    "target_path": target_path,
                    "params": mask_sensitive_data(params) if params else None
                }
            )
            
            return response
            
        except Exception as e:
            # 计算耗时
            duration_ms = int((time.time() - start_time) * 1000)
            
            # 记录错误日志
            log_api_request(
                logger,
                method,
                path,
                500,
                duration_ms,
                request_id,
                user_info.get("user_id"),
                user_info.get("tenant_id"),
                route_config["service_name"],
                success=False,
                error_code=getattr(e, 'error_code', '5003'),
                data={
                    "target_path": target_path,
                    "error": str(e)
                }
            )
            
            raise e
    
    def _find_matching_route(self, path: str) -> Optional[Dict[str, Any]]:
        """
        查找匹配的路由配置
        
        Args:
            path: 请求路径
            
        Returns:
            匹配的路由配置或None
        """
        for route_prefix, config in self.route_config.items():
            if path.startswith(route_prefix):
                return {
                    "prefix": route_prefix,
                    "target": config.target,
                    "require_auth": config.require_auth,
                    "service_name": config.service_name,
                    "timeout": config.timeout
                }
        return None
    
    def _get_service_client(self, service_name: str):
        """
        获取服务客户端
        
        Args:
            service_name: 服务名称
            
        Returns:
            服务客户端实例
        """
        client_mapping = {
            "auth_service": "auth",
            "tenant_service": "tenant",
            "eino_service": "eino",
            "memory_service": "memory"
        }
        
        client_key = client_mapping.get(service_name)
        if not client_key:
            raise ServiceUnavailableError(
                service_name,
                f"未知的服务: {service_name}"
            )
        
        return service_manager.get_client(client_key)
    
    def _extract_target_path(self, original_path: str, route_config: Dict[str, Any]) -> str:
        """
        提取目标路径
        
        Args:
            original_path: 原始路径
            route_config: 路由配置
            
        Returns:
            目标路径
        """
        # 根据API Gateway规范文档，所有微服务都期望完整的API路径
        # 包括 /api/v1 前缀，而不是相对路径
        # 这样可以保持路由的一致性和可预测性
        return original_path
    
    async def _prepare_request_headers(
        self,
        request: Request,
        user_info: Dict[str, Any],
        request_id: str
    ) -> Dict[str, str]:
        """
        准备请求头
        
        Args:
            request: FastAPI请求对象
            user_info: 用户信息
            request_id: 请求ID
            
        Returns:
            处理后的请求头
        """
        # 复制原始头部
        headers = dict(request.headers)
        
        # 确保有请求ID
        headers["X-Request-ID"] = request_id
        
        # 如果有用户信息，添加认证头部
        if user_info:
            # 添加调试日志
            logger.info(
                f"准备认证头部，用户信息: {user_info}",
                extra={
                    "request_id": request_id,
                    "user_info_keys": list(user_info.keys()) if user_info else [],
                    "operation": "prepare_auth_headers"
                }
            )
            
            # 添加请求头调试日志
            logger.info(
                f"最终请求头内容",
                extra={
                    "request_id": request_id,
                    "auth_headers": {
                        "X-User-ID": user_info.get("user_id", ""),
                        "X-Tenant-ID": user_info.get("tenant_id", ""),
                        "X-User-Role": user_info.get("role", ""),
                        "X-User-Email": user_info.get("email", "")
                    },
                    "operation": "prepare_auth_headers"
                }
            )
            
            headers["X-User-ID"] = user_info.get("user_id", "")
            headers["X-Tenant-ID"] = user_info.get("tenant_id", "")
            headers["X-User-Role"] = user_info.get("role", "")
            headers["X-User-Email"] = user_info.get("email", "")
        else:
            logger.warning(
                "用户信息为空，无法添加认证头部",
                extra={
                    "request_id": request_id,
                    "operation": "prepare_auth_headers"
                }
            )
        
        # 移除可能导致问题的头部（不区分大小写）
        headers_to_remove = ["host", "content-length", "connection", "transfer-encoding"]
        headers_lower = {k.lower(): k for k in headers.keys()}
        
        for header_lower in headers_to_remove:
            if header_lower in headers_lower:
                original_key = headers_lower[header_lower]
                headers.pop(original_key, None)
        
        return headers
    
    async def _get_request_body(self, request: Request) -> Dict[str, Any]:
        """
        获取请求体数据
        
        Args:
            request: FastAPI请求对象
            
        Returns:
            请求体数据字典
        """
        content_type = request.headers.get("content-type", "")
        
        try:
            if "application/json" in content_type:
                # JSON数据
                json_data = await request.json()
                return {"json": json_data}
                
            elif "application/x-www-form-urlencoded" in content_type:
                # 表单数据
                form_data = await request.form()
                return {"data": dict(form_data)}
                
            elif "multipart/form-data" in content_type:
                # 多部分表单数据（包含文件）
                form_data = await request.form()
                files = {}
                data = {}
                
                for key, value in form_data.items():
                    if hasattr(value, 'read'):  # 文件对象
                        files[key] = (value.filename, await value.read(), value.content_type)
                    else:
                        data[key] = value
                
                result = {}
                if files:
                    result["files"] = files
                if data:
                    result["data"] = data
                
                return result
                
            else:
                # 其他类型，尝试获取原始数据
                body = await request.body()
                if body:
                    return {"data": body}
                
        except Exception as e:
            logger.warning(
                f"获取请求体失败: {str(e)}",
                extra={
                    "request_id": getattr(request.state, "request_id", ""),
                    "content_type": content_type,
                    "path": request.url.path
                }
            )
        
        return {}
    
    def _is_stream_request(self, request: Request) -> bool:
        """
        检查是否为流式请求
        
        Args:
            request: FastAPI请求对象
            
        Returns:
            是否为流式请求
        """
        # 检查Accept头部
        accept = request.headers.get("accept", "")
        if "text/event-stream" in accept:
            return True
        
        # 检查查询参数
        stream_param = request.query_params.get("stream", "").lower()
        if stream_param in ["true", "1", "yes"]:
            return True
        
        # 检查路径
        if "/stream" in request.url.path:
            return True
        
        return False


# 全局代理服务实例
proxy_service = ProxyService()