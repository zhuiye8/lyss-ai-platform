"""
日志配置模块

提供结构化JSON日志记录功能
"""

import json
import logging
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from pythonjsonlogger import jsonlogger

from ..config import settings


class LyssJSONFormatter(jsonlogger.JsonFormatter):
    """Lyss平台JSON日志格式化器"""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        """添加自定义字段到日志记录"""
        super().add_fields(log_record, record, message_dict)
        
        # 添加时间戳
        if not log_record.get("timestamp"):
            log_record["timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        # 添加服务名称
        log_record["service"] = "lyss-api-gateway"
        
        # 添加日志级别
        log_record["level"] = record.levelname
        
        # 添加请求相关信息
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
        
        if hasattr(record, "tenant_id"):
            log_record["tenant_id"] = record.tenant_id
        
        if hasattr(record, "user_id"):
            log_record["user_id"] = record.user_id
        
        if hasattr(record, "operation"):
            log_record["operation"] = record.operation
        
        if hasattr(record, "duration_ms"):
            log_record["duration_ms"] = record.duration_ms
        
        if hasattr(record, "success"):
            log_record["success"] = record.success
        
        if hasattr(record, "error_code"):
            log_record["error_code"] = record.error_code
        
        if hasattr(record, "data"):
            log_record["data"] = record.data


def setup_logging() -> None:
    """设置日志配置"""
    
    # 移除现有的处理器
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    
    # 设置日志格式
    if settings.log_format.lower() == "json":
        formatter = LyssJSONFormatter(
            fmt="%(timestamp)s %(level)s %(service)s %(message)s"
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    console_handler.setFormatter(formatter)
    
    # 设置日志级别
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    console_handler.setLevel(log_level)
    root_logger.setLevel(log_level)
    
    # 添加处理器
    root_logger.addHandler(console_handler)
    
    # 配置第三方库日志级别
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    获取日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        日志记录器实例
    """
    return logging.getLogger(name)


def log_api_request(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: int,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    target_service: Optional[str] = None,
    success: bool = True,
    error_code: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None
) -> None:
    """
    记录API请求日志
    
    Args:
        logger: 日志记录器
        method: HTTP方法
        path: 请求路径
        status_code: 状态码
        duration_ms: 请求耗时(毫秒)
        request_id: 请求ID
        user_id: 用户ID
        tenant_id: 租户ID
        target_service: 目标服务
        success: 是否成功
        error_code: 错误代码
        data: 附加数据
    """
    message = f"API请求 {method} {path} -> {status_code}"
    
    extra = {
        "request_id": request_id,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": duration_ms,
        "success": success,
        "operation": "api_request"
    }
    
    if target_service:
        extra["target_service"] = target_service
    
    if error_code:
        extra["error_code"] = error_code
    
    if data:
        extra["data"] = data
    
    if success:
        logger.info(message, extra=extra)
    else:
        logger.error(message, extra=extra)


def log_service_call(
    logger: logging.Logger,
    service_name: str,
    method: str,
    path: str,
    status_code: int,
    duration_ms: int,
    request_id: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None
) -> None:
    """
    记录服务调用日志
    
    Args:
        logger: 日志记录器
        service_name: 服务名称
        method: HTTP方法
        path: 请求路径
        status_code: 状态码
        duration_ms: 请求耗时(毫秒)
        request_id: 请求ID
        success: 是否成功
        error_message: 错误信息
        data: 附加数据
    """
    message = f"服务调用 {service_name} {method} {path} -> {status_code}"
    
    extra = {
        "request_id": request_id,
        "target_service": service_name,
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": duration_ms,
        "success": success,
        "operation": "service_call"
    }
    
    if error_message:
        extra["error_message"] = error_message
    
    if data:
        extra["data"] = data
    
    if success:
        logger.info(message, extra=extra)
    else:
        logger.error(message, extra=extra)


def log_auth_event(
    logger: logging.Logger,
    event_type: str,
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    request_id: Optional[str] = None,
    success: bool = True,
    error_code: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None
) -> None:
    """
    记录认证事件日志
    
    Args:
        logger: 日志记录器
        event_type: 事件类型
        user_id: 用户ID
        tenant_id: 租户ID
        request_id: 请求ID
        success: 是否成功
        error_code: 错误代码
        data: 附加数据
    """
    message = f"认证事件: {event_type}"
    
    extra = {
        "request_id": request_id,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "operation": "auth_event",
        "event_type": event_type,
        "success": success
    }
    
    if error_code:
        extra["error_code"] = error_code
    
    if data:
        extra["data"] = data
    
    if success:
        logger.info(message, extra=extra)
    else:
        logger.warning(message, extra=extra)