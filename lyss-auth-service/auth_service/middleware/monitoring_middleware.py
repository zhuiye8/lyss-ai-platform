"""
监控中间件

提供全面的应用监控和性能度量功能：
- 请求响应时间追踪
- API使用统计和分析
- 错误率监控和告警
- 用户行为分析
- 系统健康状态监控

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import time
import asyncio
import json
import uuid
from typing import Optional, Dict, List, Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from contextvars import ContextVar
import threading

from ..utils.redis_client import RedisClient, get_redis_client
from ..utils.logging import get_logger

logger = get_logger(__name__)

# 请求上下文变量
request_id_var: ContextVar[str] = ContextVar("request_id")
request_start_time_var: ContextVar[float] = ContextVar("request_start_time")


class MonitoringMiddleware(BaseHTTPMiddleware):
    """
    监控中间件
    
    功能特性：
    - 请求响应时间统计
    - API调用计数和分析
    - 错误率追踪
    - 用户活跃度统计
    - 性能指标收集
    - 实时健康检查
    """
    
    def __init__(
        self,
        app,
        redis_client_factory: Optional[Callable] = None,
        enable_detailed_logging: bool = True,
        enable_performance_tracking: bool = True,
        enable_user_analytics: bool = True,
        slow_request_threshold: float = 1.0,  # 慢请求阈值（秒）
        metrics_retention_hours: int = 24
    ):
        super().__init__(app)
        self.redis_client_factory = redis_client_factory or get_redis_client
        self.enable_detailed_logging = enable_detailed_logging
        self.enable_performance_tracking = enable_performance_tracking
        self.enable_user_analytics = enable_user_analytics
        self.slow_request_threshold = slow_request_threshold
        self.metrics_retention_hours = metrics_retention_hours
        
        # 内存中的指标缓存（用于快速访问）
        self._metrics_cache = {
            "request_count": 0,
            "error_count": 0,
            "total_response_time": 0.0,
            "active_connections": 0
        }
        self._cache_lock = threading.Lock()
    
    async def dispatch(self, request: Request, call_next):
        """处理请求监控"""
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # 设置请求上下文
        request_id_var.set(request_id)
        request_start_time_var.set(start_time)
        
        # 添加请求ID到request对象
        request.state.request_id = request_id
        
        # 获取客户端信息
        client_info = self._extract_client_info(request)
        
        # 增加活跃连接数
        with self._cache_lock:
            self._metrics_cache["active_connections"] += 1
        
        logger.info(
            f"请求开始: {request.method} {request.url.path}",
            operation="request_start",
            data={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client_ip": client_info["ip_address"],
                "user_agent": client_info["user_agent"][:200],  # 限制长度
                "user_id": client_info.get("user_id")
            }
        )
        
        try:
            # 处理请求
            response = await call_next(request)
            
            # 计算响应时间
            end_time = time.time()
            response_time = end_time - start_time
            
            # 更新内存指标
            with self._cache_lock:
                self._metrics_cache["request_count"] += 1
                self._metrics_cache["total_response_time"] += response_time
                self._metrics_cache["active_connections"] -= 1
                
                if response.status_code >= 400:
                    self._metrics_cache["error_count"] += 1
            
            # 异步记录详细指标
            if self.enable_performance_tracking:
                asyncio.create_task(
                    self._record_request_metrics(
                        request, response, client_info, response_time
                    )
                )
            
            # 记录用户分析数据
            if self.enable_user_analytics and client_info.get("user_id"):
                asyncio.create_task(
                    self._record_user_analytics(
                        client_info, request, response, response_time
                    )
                )
            
            # 检查慢请求
            if response_time > self.slow_request_threshold:
                logger.warning(
                    f"慢请求检测: {response_time:.3f}s > {self.slow_request_threshold}s",
                    operation="slow_request",
                    data={
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "response_time": response_time,
                        "status_code": response.status_code,
                        "user_id": client_info.get("user_id")
                    }
                )
            
            # 记录请求完成日志
            if self.enable_detailed_logging:
                log_level = "error" if response.status_code >= 500 else \
                           "warning" if response.status_code >= 400 else "info"
                
                getattr(logger, log_level)(
                    f"请求完成: {request.method} {request.url.path} - "
                    f"{response.status_code} ({response_time:.3f}s)",
                    operation="request_complete",
                    data={
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "response_time": response_time,
                        "user_id": client_info.get("user_id"),
                        "tenant_id": client_info.get("tenant_id")
                    }
                )
            
            # 添加响应头
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{response_time:.3f}"
            
            return response
            
        except Exception as e:
            # 处理异常情况
            end_time = time.time()
            response_time = end_time - start_time
            
            with self._cache_lock:
                self._metrics_cache["error_count"] += 1
                self._metrics_cache["active_connections"] -= 1
            
            logger.error(
                f"请求处理异常: {str(e)}",
                operation="request_error",
                data={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "response_time": response_time,
                    "error": str(e),
                    "user_id": client_info.get("user_id")
                }
            )
            
            # 记录异常指标
            if self.enable_performance_tracking:
                asyncio.create_task(
                    self._record_error_metrics(request, client_info, str(e))
                )
            
            raise
    
    def _extract_client_info(self, request: Request) -> dict:
        """提取客户端信息"""
        # 获取真实IP地址
        ip_address = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if not ip_address:
            ip_address = request.headers.get("x-real-ip", "")
        if not ip_address and request.client:
            ip_address = request.client.host
        
        # 获取用户信息
        user_id = None
        tenant_id = None
        if hasattr(request.state, "user") and request.state.user:
            user_id = request.state.user.get("sub")
            tenant_id = request.state.user.get("tenant_id")
        
        return {
            "ip_address": ip_address or "unknown",
            "user_id": user_id,
            "tenant_id": tenant_id,
            "user_agent": request.headers.get("user-agent", ""),
            "referer": request.headers.get("referer", ""),
            "accept_language": request.headers.get("accept-language", "")
        }
    
    async def _record_request_metrics(
        self,
        request: Request,
        response: Response,
        client_info: dict,
        response_time: float
    ):
        """记录请求指标到Redis"""
        try:
            redis_client = self.redis_client_factory()
            current_time = int(time.time())
            
            # 构建指标键
            minute_key = f"metrics:minute:{current_time // 60}"
            hour_key = f"metrics:hour:{current_time // 3600}"
            
            # 记录基础指标
            pipe = redis_client._redis.pipeline()
            
            # 请求计数
            pipe.hincrby(minute_key, "request_count", 1)
            pipe.hincrby(hour_key, "request_count", 1)
            
            # 状态码统计
            pipe.hincrby(minute_key, f"status_{response.status_code}", 1)
            pipe.hincrby(hour_key, f"status_{response.status_code}", 1)
            
            # 路径统计
            path_key = request.url.path.replace("/", "_").replace(":", "_")
            pipe.hincrby(minute_key, f"path_{path_key}", 1)
            pipe.hincrby(hour_key, f"path_{path_key}", 1)
            
            # 响应时间统计
            pipe.hincrby(minute_key, "total_response_time", int(response_time * 1000))
            pipe.hincrby(hour_key, "total_response_time", int(response_time * 1000))
            
            # IP统计
            if client_info["ip_address"] != "unknown":
                pipe.hincrby(minute_key, f"ip_{client_info['ip_address']}", 1)
                pipe.hincrby(hour_key, f"ip_{client_info['ip_address']}", 1)
            
            # 设置过期时间
            pipe.expire(minute_key, 3600)  # 1小时
            pipe.expire(hour_key, 86400 * self.metrics_retention_hours)
            
            await pipe.execute()
            
        except Exception as e:
            logger.error(
                f"记录请求指标异常: {str(e)}",
                operation="record_request_metrics",
                data={"error": str(e)}
            )
    
    async def _record_user_analytics(
        self,
        client_info: dict,
        request: Request,
        response: Response,
        response_time: float
    ):
        """记录用户行为分析数据"""
        try:
            redis_client = self.redis_client_factory()
            user_id = client_info["user_id"]
            tenant_id = client_info["tenant_id"]
            current_time = int(time.time())
            
            # 用户活跃度统计
            day_key = f"user_analytics:day:{current_time // 86400}"
            hour_key = f"user_analytics:hour:{current_time // 3600}"
            
            pipe = redis_client._redis.pipeline()
            
            # 记录活跃用户
            pipe.sadd(f"{day_key}:active_users", user_id)
            pipe.sadd(f"{hour_key}:active_users", user_id)
            
            if tenant_id:
                pipe.sadd(f"{day_key}:tenant_{tenant_id}:active_users", user_id)
                pipe.sadd(f"{hour_key}:tenant_{tenant_id}:active_users", user_id)
            
            # 用户请求统计
            user_stats_key = f"user_stats:{user_id}:{current_time // 3600}"
            pipe.hincrby(user_stats_key, "request_count", 1)
            pipe.hincrby(user_stats_key, "total_response_time", int(response_time * 1000))
            pipe.hincrby(user_stats_key, f"status_{response.status_code}", 1)
            
            # 记录用户最后活跃时间
            pipe.hset(f"user_last_activity:{user_id}", mapping={
                "last_seen": current_time,
                "last_ip": client_info["ip_address"],
                "last_path": request.url.path,
                "tenant_id": tenant_id or ""
            })
            
            # 设置过期时间
            pipe.expire(f"{day_key}:active_users", 86400 * 7)  # 7天
            pipe.expire(f"{hour_key}:active_users", 86400)  # 1天
            pipe.expire(user_stats_key, 86400 * 7)  # 7天
            pipe.expire(f"user_last_activity:{user_id}", 86400 * 30)  # 30天
            
            if tenant_id:
                pipe.expire(f"{day_key}:tenant_{tenant_id}:active_users", 86400 * 7)
                pipe.expire(f"{hour_key}:tenant_{tenant_id}:active_users", 86400)
            
            await pipe.execute()
            
        except Exception as e:
            logger.error(
                f"记录用户分析数据异常: {str(e)}",
                operation="record_user_analytics",
                data={"user_id": client_info.get("user_id"), "error": str(e)}
            )
    
    async def _record_error_metrics(
        self,
        request: Request,
        client_info: dict,
        error_message: str
    ):
        """记录错误指标"""
        try:
            redis_client = self.redis_client_factory()
            current_time = int(time.time())
            
            error_key = f"errors:{current_time // 300}"  # 5分钟窗口
            
            pipe = redis_client._redis.pipeline()
            
            # 错误统计
            pipe.hincrby(error_key, "total_errors", 1)
            pipe.hincrby(error_key, f"path_{request.url.path}", 1)
            
            if client_info.get("user_id"):
                pipe.hincrby(error_key, f"user_{client_info['user_id']}", 1)
            
            if client_info["ip_address"] != "unknown":
                pipe.hincrby(error_key, f"ip_{client_info['ip_address']}", 1)
            
            # 记录错误详情（限制数量）
            error_detail = {
                "timestamp": current_time,
                "path": request.url.path,
                "method": request.method,
                "error": error_message[:500],  # 限制长度
                "user_id": client_info.get("user_id"),
                "ip": client_info["ip_address"]
            }
            
            pipe.lpush("recent_errors", json.dumps(error_detail, ensure_ascii=False))
            pipe.ltrim("recent_errors", 0, 99)  # 只保留最近100个错误
            
            # 设置过期时间
            pipe.expire(error_key, 3600)  # 1小时
            pipe.expire("recent_errors", 86400)  # 1天
            
            await pipe.execute()
            
        except Exception as e:
            logger.error(
                f"记录错误指标异常: {str(e)}",
                operation="record_error_metrics",
                data={"error": str(e)}
            )
    
    def get_current_metrics(self) -> dict:
        """获取当前内存中的指标"""
        with self._cache_lock:
            metrics = self._metrics_cache.copy()
        
        # 计算平均响应时间
        if metrics["request_count"] > 0:
            metrics["avg_response_time"] = metrics["total_response_time"] / metrics["request_count"]
        else:
            metrics["avg_response_time"] = 0.0
        
        # 计算错误率
        if metrics["request_count"] > 0:
            metrics["error_rate"] = metrics["error_count"] / metrics["request_count"]
        else:
            metrics["error_rate"] = 0.0
        
        return metrics
    
    async def get_detailed_metrics(self, time_range: str = "hour") -> dict:
        """获取详细的指标数据"""
        try:
            redis_client = self.redis_client_factory()
            current_time = int(time.time())
            
            if time_range == "hour":
                key = f"metrics:hour:{current_time // 3600}"
            elif time_range == "minute":
                key = f"metrics:minute:{current_time // 60}"
            else:
                key = f"metrics:hour:{current_time // 3600}"
            
            metrics = await redis_client._redis.hgetall(key)
            
            if not metrics:
                return {"message": f"暂无{time_range}级别的指标数据"}
            
            # 转换数据类型
            processed_metrics = {}
            for field, value in metrics.items():
                try:
                    processed_metrics[field] = int(value)
                except (ValueError, TypeError):
                    processed_metrics[field] = value
            
            # 计算衍生指标
            if processed_metrics.get("request_count", 0) > 0:
                processed_metrics["avg_response_time"] = (
                    processed_metrics.get("total_response_time", 0) / 
                    processed_metrics["request_count"] / 1000  # 转换为秒
                )
                
                error_count = sum(
                    v for k, v in processed_metrics.items() 
                    if k.startswith("status_") and int(k.split("_")[1]) >= 400
                )
                processed_metrics["error_rate"] = error_count / processed_metrics["request_count"]
            
            return processed_metrics
            
        except Exception as e:
            logger.error(
                f"获取详细指标异常: {str(e)}",
                operation="get_detailed_metrics",
                data={"time_range": time_range, "error": str(e)}
            )
            return {"error": str(e)}


def get_request_id() -> Optional[str]:
    """获取当前请求ID"""
    try:
        return request_id_var.get()
    except LookupError:
        return None


def get_request_duration() -> Optional[float]:
    """获取当前请求持续时间"""
    try:
        start_time = request_start_time_var.get()
        return time.time() - start_time
    except LookupError:
        return None