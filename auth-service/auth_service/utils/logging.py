"""
Auth Service 统一日志配置
使用structlog实现结构化JSON日志
严格遵循 docs/STANDARDS.md 中的日志规范
"""

import json
import logging
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import structlog
from structlog.types import EventDict, Processor

from ..config import settings


def add_timestamp(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """添加时间戳处理器"""
    event_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"
    return event_dict


def add_service_info(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """添加服务信息处理器"""
    event_dict["service"] = "lyss-auth-service"
    return event_dict


def add_log_level(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """添加日志级别处理器"""
    event_dict["level"] = method_name.upper()
    return event_dict


def format_chinese_message(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """确保日志消息为中文格式"""
    if "event" in event_dict:
        # structlog使用event作为消息字段名
        event_dict["message"] = event_dict.pop("event")
    return event_dict


class RequestContextProcessor:
    """请求上下文处理器，注入请求ID和租户信息"""

    def __call__(self, logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
        # 这些值应该从请求上下文中获取
        # 在FastAPI中间件中设置
        from contextvars import ContextVar
        
        request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
        tenant_id_var: ContextVar[Optional[str]] = ContextVar("tenant_id", default=None)
        user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)

        request_id = request_id_var.get()
        tenant_id = tenant_id_var.get()
        user_id = user_id_var.get()

        if request_id:
            event_dict["request_id"] = request_id
        if tenant_id:
            event_dict["tenant_id"] = tenant_id
        if user_id:
            event_dict["user_id"] = user_id

        return event_dict


def configure_logging():
    """配置structlog日志系统"""
    
    # 配置标准库logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )

    # 配置structlog处理器链
    processors: list[Processor] = [
        # 过滤日志级别
        structlog.stdlib.filter_by_level,
        # 添加时间戳
        add_timestamp,
        # 添加服务信息
        add_service_info,
        # 添加日志级别
        add_log_level,
        # 添加请求上下文
        RequestContextProcessor(),
        # 格式化中文消息
        format_chinese_message,
        # 添加调用栈信息（仅在开发环境）
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        # 处理异常
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        # JSON序列化
        structlog.processors.JSONRenderer(ensure_ascii=False),
    ]

    # 配置structlog
    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


class AuthServiceLogger:
    """Auth Service专用日志器"""

    def __init__(self):
        self.logger = structlog.get_logger()

    def info(
        self,
        message: str,
        operation: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
        success: bool = True,
        **kwargs
    ):
        """记录信息日志"""
        log_data = {
            "operation": operation,
            "data": data,
            "duration_ms": duration_ms,
            "success": success,
            **kwargs
        }
        # 移除None值
        log_data = {k: v for k, v in log_data.items() if v is not None}
        
        self.logger.info(message, **log_data)

    def warning(
        self,
        message: str,
        operation: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """记录警告日志"""
        log_data = {
            "operation": operation,
            "data": data,
            **kwargs
        }
        log_data = {k: v for k, v in log_data.items() if v is not None}
        
        self.logger.warning(message, **log_data)

    def error(
        self,
        message: str,
        operation: Optional[str] = None,
        error_code: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """记录错误日志"""
        log_data = {
            "operation": operation,
            "error_code": error_code,
            "data": data,
            "success": False,
            **kwargs
        }
        log_data = {k: v for k, v in log_data.items() if v is not None}
        
        self.logger.error(message, **log_data)

    def debug(
        self,
        message: str,
        operation: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """记录调试日志"""
        if not settings.debug:
            return
            
        log_data = {
            "operation": operation,
            "data": data,
            **kwargs
        }
        log_data = {k: v for k, v in log_data.items() if v is not None}
        
        self.logger.debug(message, **log_data)

    def log_auth_event(
        self,
        event_type: str,
        message: str,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_code: Optional[str] = None,
        **kwargs
    ):
        """记录认证事件日志"""
        log_data = {
            "event_type": event_type,
            "user_id": user_id,
            "email": email,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "success": success,
            "error_code": error_code,
            **kwargs
        }
        log_data = {k: v for k, v in log_data.items() if v is not None}

        if success:
            self.logger.info(message, **log_data)
        else:
            self.logger.warning(message, **log_data)

    def log_security_event(
        self,
        event_type: str,
        message: str,
        ip_address: Optional[str] = None,
        failed_attempts: Optional[int] = None,
        time_window: Optional[str] = None,
        **kwargs
    ):
        """记录安全审计日志"""
        log_data = {
            "event_type": event_type,
            "ip_address": ip_address,
            "failed_attempts": failed_attempts,
            "time_window": time_window,
            **kwargs
        }
        log_data = {k: v for k, v in log_data.items() if v is not None}

        self.logger.warning(message, **log_data)


# 初始化日志配置
configure_logging()

# 全局日志器实例
logger = AuthServiceLogger()