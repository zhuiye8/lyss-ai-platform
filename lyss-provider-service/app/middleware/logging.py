"""
请求日志中间件

记录API请求和响应的详细信息，支持结构化日志和审计功能。

Author: Lyss AI Team  
Created: 2025-01-21
Modified: 2025-01-21
"""

import json
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import Request, Response

from ..core.config import get_settings

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("audit")
settings = get_settings()


async def request_logging_middleware(request: Request, call_next):
    """
    请求日志中间件
    
    记录所有API请求和响应的详细信息。
    
    Args:
        request: FastAPI请求对象
        call_next: 下一个中间件或路由处理器
        
    Returns:
        Response: 处理后的响应
    """
    # 生成请求ID
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # 记录请求开始时间
    start_time = time.time()
    
    # 收集请求信息
    request_info = {
        "request_id": request_id,
        "method": request.method,
        "url": str(request.url),
        "path": request.url.path,
        "query_params": dict(request.query_params),
        "headers": dict(request.headers),
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "timestamp": datetime.utcnow().isoformat(),
        "tenant_id": getattr(request.state, "tenant_id", None),
        "user_id": getattr(request.state, "user_id", None)
    }
    
    # 记录请求体（仅对POST/PUT/PATCH请求）
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            # 读取请求体
            body = await request.body()
            if body:
                # 尝试解析JSON
                try:
                    request_info["body"] = json.loads(body)
                except json.JSONDecodeError:
                    request_info["body"] = body.decode("utf-8", errors="ignore")[:1000]
        except Exception as e:
            logger.warning(f"无法读取请求体: {e}")
    
    # 过滤敏感信息
    request_info = _filter_sensitive_data(request_info)
    
    # 记录请求日志
    logger.info(f"API请求开始", extra={"request_info": request_info})
    
    # 处理请求
    try:
        response = await call_next(request)
        
        # 计算响应时间
        response_time = (time.time() - start_time) * 1000
        
        # 收集响应信息
        response_info = {
            "request_id": request_id,
            "status_code": response.status_code,
            "response_time_ms": round(response_time, 2),
            "response_headers": dict(response.headers),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 添加响应时间到响应头
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{response_time:.2f}ms"
        
        # 记录响应日志
        log_level = logging.INFO if response.status_code < 400 else logging.WARNING
        logger.log(
            log_level,
            f"API请求完成 - {response.status_code} - {response_time:.2f}ms",
            extra={"response_info": response_info}
        )
        
        # 记录审计日志（仅对重要操作）
        if _should_audit(request):
            await _record_audit_log(request_info, response_info)
        
        return response
        
    except Exception as e:
        # 计算响应时间
        response_time = (time.time() - start_time) * 1000
        
        # 记录错误信息
        error_info = {
            "request_id": request_id,
            "error": str(e),
            "error_type": type(e).__name__,
            "response_time_ms": round(response_time, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.error(
            f"API请求异常 - {error_info['error_type']} - {response_time:.2f}ms",
            extra={"error_info": error_info},
            exc_info=True
        )
        
        raise


def _filter_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    过滤敏感数据
    
    Args:
        data: 原始数据
        
    Returns:
        Dict[str, Any]: 过滤后的数据
    """
    # 敏感字段列表
    sensitive_fields = [
        "authorization", "api-key", "x-api-key",
        "password", "secret", "token", "key",
        "credentials", "api_key", "access_token"
    ]
    
    filtered_data = data.copy()
    
    # 过滤请求头中的敏感信息
    if "headers" in filtered_data:
        headers = filtered_data["headers"]
        for field in sensitive_fields:
            if field in headers:
                headers[field] = "[MASKED]"
            # 也检查小写版本
            if field.lower() in headers:
                headers[field.lower()] = "[MASKED]"
    
    # 过滤请求体中的敏感信息
    if "body" in filtered_data and isinstance(filtered_data["body"], dict):
        body = filtered_data["body"]
        for field in sensitive_fields:
            if field in body:
                body[field] = "[MASKED]"
    
    return filtered_data


def _should_audit(request: Request) -> bool:
    """
    判断是否需要记录审计日志
    
    Args:
        request: 请求对象
        
    Returns:
        bool: 是否需要审计
    """
    # 需要审计的路径模式
    audit_paths = [
        "/api/v1/providers",  # 供应商管理
        "/api/v1/channels",   # 渠道管理
        "/api/v1/proxy/",     # 代理请求
    ]
    
    # 需要审计的方法
    audit_methods = ["POST", "PUT", "DELETE", "PATCH"]
    
    path = request.url.path
    method = request.method
    
    # 检查是否匹配审计条件
    if method in audit_methods:
        for audit_path in audit_paths:
            if path.startswith(audit_path):
                return True
    
    return False


async def _record_audit_log(request_info: Dict[str, Any], response_info: Dict[str, Any]):
    """
    记录审计日志
    
    Args:
        request_info: 请求信息
        response_info: 响应信息
    """
    try:
        audit_record = {
            "event_type": "api_access",
            "request_id": request_info["request_id"],
            "tenant_id": request_info.get("tenant_id"),
            "user_id": request_info.get("user_id"),
            "method": request_info["method"],
            "path": request_info["path"],
            "client_ip": request_info["client_ip"],
            "user_agent": request_info.get("user_agent"),
            "status_code": response_info["status_code"],
            "response_time_ms": response_info["response_time_ms"],
            "timestamp": request_info["timestamp"],
            "success": response_info["status_code"] < 400
        }
        
        # 添加请求体信息（仅对重要操作）
        if request_info.get("body") and request_info["method"] in ["POST", "PUT", "PATCH"]:
            audit_record["request_body"] = request_info["body"]
        
        # 记录审计日志
        audit_logger.info(
            f"审计记录 - {audit_record['method']} {audit_record['path']} - {audit_record['status_code']}",
            extra={"audit_record": audit_record}
        )
        
        # 可以在这里添加到审计数据库或外部审计系统
        
    except Exception as e:
        logger.error(f"记录审计日志失败: {e}")


class RequestContextFilter(logging.Filter):
    """
    请求上下文过滤器
    
    为日志记录添加请求上下文信息。
    """
    
    def filter(self, record):
        """
        添加请求上下文到日志记录
        
        Args:
            record: 日志记录
            
        Returns:
            bool: 是否保留此日志记录
        """
        # 如果没有额外的上下文信息，创建一个空字典
        if not hasattr(record, 'request_info') and not hasattr(record, 'response_info'):
            record.context = {}
        
        return True


def setup_logging():
    """
    配置日志系统
    """
    # 配置请求日志格式
    request_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 配置审计日志格式
    audit_formatter = logging.Formatter(
        '%(asctime)s - AUDIT - %(message)s'
    )
    
    # 添加请求上下文过滤器
    context_filter = RequestContextFilter()
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.addFilter(context_filter)
    
    # 配置审计日志记录器
    audit_logger.setLevel(logging.INFO)
    
    if settings.environment != "development":
        # 生产环境使用文件日志
        audit_handler = logging.FileHandler("logs/audit.log")
        audit_handler.setFormatter(audit_formatter)
        audit_logger.addHandler(audit_handler)