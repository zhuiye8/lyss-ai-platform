"""
限流中间件

基于Redis实现的分布式限流系统，支持多种限流策略：
- IP限流：防止单个IP过度请求
- 用户限流：防止单个用户滥用API
- 接口限流：保护关键接口不被压垮
- 全局限流：系统总体流量控制

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import time
import asyncio
from typing import Optional, Dict, Tuple, Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import json

from ..utils.redis_client import RedisClient, get_redis_client
from ..utils.logging import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    分布式限流中间件
    
    功能特性：
    - 多维度限流（IP、用户、接口、全局）
    - 滑动窗口算法实现
    - 动态限流配置
    - 限流状态缓存
    - 优雅降级策略
    """
    
    def __init__(
        self,
        app,
        redis_client_factory: Optional[Callable] = None,
        global_rate_limit: Optional[Tuple[int, int]] = None,  # (requests, window_seconds)
        ip_rate_limit: Optional[Tuple[int, int]] = None,
        user_rate_limit: Optional[Tuple[int, int]] = None,
        endpoint_rate_limits: Optional[Dict[str, Tuple[int, int]]] = None,
        enable_rate_limit_headers: bool = True,
        skip_successful_requests: bool = False
    ):
        super().__init__(app)
        self.redis_client_factory = redis_client_factory or get_redis_client
        
        # 默认限流配置
        self.global_rate_limit = global_rate_limit or (10000, 3600)  # 10000 req/hour
        self.ip_rate_limit = ip_rate_limit or (1000, 3600)  # 1000 req/hour per IP
        self.user_rate_limit = user_rate_limit or (5000, 3600)  # 5000 req/hour per user
        
        # 特定接口限流配置
        self.endpoint_rate_limits = endpoint_rate_limits or {
            "/api/v1/auth/login": (10, 300),  # 10次/5分钟
            "/api/v1/auth/register": (5, 300),  # 5次/5分钟  
            "/api/v1/auth/password/reset/request": (3, 300),  # 3次/5分钟
        }
        
        self.enable_rate_limit_headers = enable_rate_limit_headers
        self.skip_successful_requests = skip_successful_requests
    
    async def dispatch(self, request: Request, call_next):
        """处理请求限流"""
        start_time = time.time()
        
        try:
            redis_client = self.redis_client_factory()
            
            # 获取客户端标识信息
            client_info = self._extract_client_info(request)
            
            # 执行多维度限流检查
            rate_limit_result = await self._check_rate_limits(
                redis_client, request, client_info
            )
            
            if rate_limit_result["limited"]:
                return self._create_rate_limit_response(rate_limit_result)
            
            # 执行请求处理
            response = await call_next(request)
            
            # 记录成功请求（用于统计）
            if not self.skip_successful_requests or response.status_code >= 400:
                await self._record_request(redis_client, request, client_info, response.status_code)
            
            # 添加限流信息头
            if self.enable_rate_limit_headers:
                self._add_rate_limit_headers(response, rate_limit_result)
            
            # 记录请求处理时间
            process_time = time.time() - start_time
            response.headers["X-RateLimit-Process-Time"] = f"{process_time:.3f}"
            
            return response
            
        except Exception as e:
            logger.error(
                f"限流中间件异常: {str(e)}",
                operation="rate_limit_middleware",
                data={
                    "path": request.url.path,
                    "error": str(e)
                }
            )
            # 限流服务异常时允许请求通过，但记录错误
            return await call_next(request)
    
    def _extract_client_info(self, request: Request) -> dict:
        """提取客户端识别信息"""
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
            "path": request.url.path,
            "method": request.method
        }
    
    async def _check_rate_limits(
        self, 
        redis_client: RedisClient, 
        request: Request, 
        client_info: dict
    ) -> dict:
        """执行多维度限流检查"""
        current_time = time.time()
        rate_limit_results = {}
        
        try:
            # 1. 全局限流检查
            global_limited, global_usage = await self._check_sliding_window_limit(
                redis_client,
                f"global_rate_limit",
                self.global_rate_limit[0],
                self.global_rate_limit[1],
                current_time
            )
            rate_limit_results["global"] = {
                "limited": global_limited,
                "usage": global_usage,
                "limit": self.global_rate_limit[0],
                "window": self.global_rate_limit[1]
            }
            
            if global_limited:
                logger.warning(
                    f"全局限流触发: {global_usage}/{self.global_rate_limit[0]}",
                    operation="global_rate_limit",
                    data=client_info
                )
                return {
                    "limited": True,
                    "reason": "全局访问量超限",
                    "retry_after": self.global_rate_limit[1],
                    "details": rate_limit_results
                }
            
            # 2. IP限流检查
            if client_info["ip_address"] != "unknown":
                ip_limited, ip_usage = await self._check_sliding_window_limit(
                    redis_client,
                    f"ip_rate_limit:{client_info['ip_address']}",
                    self.ip_rate_limit[0],
                    self.ip_rate_limit[1],
                    current_time
                )
                rate_limit_results["ip"] = {
                    "limited": ip_limited,
                    "usage": ip_usage,
                    "limit": self.ip_rate_limit[0],
                    "window": self.ip_rate_limit[1]
                }
                
                if ip_limited:
                    logger.warning(
                        f"IP限流触发: IP={client_info['ip_address']}, {ip_usage}/{self.ip_rate_limit[0]}",
                        operation="ip_rate_limit",
                        data=client_info
                    )
                    return {
                        "limited": True,
                        "reason": "IP访问频率过高",
                        "retry_after": self.ip_rate_limit[1],
                        "details": rate_limit_results
                    }
            
            # 3. 用户限流检查
            if client_info["user_id"]:
                user_limited, user_usage = await self._check_sliding_window_limit(
                    redis_client,
                    f"user_rate_limit:{client_info['user_id']}",
                    self.user_rate_limit[0],
                    self.user_rate_limit[1],
                    current_time
                )
                rate_limit_results["user"] = {
                    "limited": user_limited,
                    "usage": user_usage,
                    "limit": self.user_rate_limit[0],
                    "window": self.user_rate_limit[1]
                }
                
                if user_limited:
                    logger.warning(
                        f"用户限流触发: User={client_info['user_id']}, {user_usage}/{self.user_rate_limit[0]}",
                        operation="user_rate_limit",
                        data=client_info
                    )
                    return {
                        "limited": True,
                        "reason": "用户访问频率过高",
                        "retry_after": self.user_rate_limit[1],
                        "details": rate_limit_results
                    }
            
            # 4. 接口特定限流检查
            endpoint_key = f"{request.method}:{request.url.path}"
            if request.url.path in self.endpoint_rate_limits:
                limit, window = self.endpoint_rate_limits[request.url.path]
                
                # 构建更细粒度的键（结合IP或用户）
                if client_info["user_id"]:
                    endpoint_limit_key = f"endpoint_rate_limit:{endpoint_key}:user:{client_info['user_id']}"
                else:
                    endpoint_limit_key = f"endpoint_rate_limit:{endpoint_key}:ip:{client_info['ip_address']}"
                
                endpoint_limited, endpoint_usage = await self._check_sliding_window_limit(
                    redis_client,
                    endpoint_limit_key,
                    limit,
                    window,
                    current_time
                )
                rate_limit_results["endpoint"] = {
                    "limited": endpoint_limited,
                    "usage": endpoint_usage,
                    "limit": limit,
                    "window": window,
                    "endpoint": request.url.path
                }
                
                if endpoint_limited:
                    logger.warning(
                        f"接口限流触发: {endpoint_key}, {endpoint_usage}/{limit}",
                        operation="endpoint_rate_limit", 
                        data=client_info
                    )
                    return {
                        "limited": True,
                        "reason": f"接口 {request.url.path} 访问频率过高",
                        "retry_after": window,
                        "details": rate_limit_results
                    }
            
            return {
                "limited": False,
                "details": rate_limit_results
            }
            
        except Exception as e:
            logger.error(
                f"限流检查异常: {str(e)}",
                operation="rate_limit_check",
                data=client_info
            )
            # 异常时不限流，确保服务可用性
            return {"limited": False, "error": str(e)}
    
    async def _check_sliding_window_limit(
        self,
        redis_client: RedisClient,
        key: str,
        limit: int,
        window_seconds: int,
        current_time: float
    ) -> Tuple[bool, int]:
        """滑动窗口限流检查"""
        try:
            # 使用Redis的ZSET实现滑动窗口
            window_start = current_time - window_seconds
            
            # 清理过期记录
            await redis_client._redis.zremrangebyscore(key, 0, window_start)
            
            # 获取当前窗口内的请求数
            current_count = await redis_client._redis.zcard(key)
            
            if current_count >= limit:
                return True, current_count
            
            # 添加当前请求记录
            await redis_client._redis.zadd(key, {str(current_time): current_time})
            
            # 设置键的过期时间（窗口大小的2倍，确保清理）
            await redis_client._redis.expire(key, window_seconds * 2)
            
            return False, current_count + 1
            
        except Exception as e:
            logger.error(
                f"滑动窗口检查异常: {str(e)}",
                operation="sliding_window_check",
                data={"key": key, "error": str(e)}
            )
            # 异常时不限流
            return False, 0
    
    async def _record_request(
        self,
        redis_client: RedisClient,
        request: Request,
        client_info: dict,
        status_code: int
    ):
        """记录请求统计信息"""
        try:
            current_time = time.time()
            
            # 记录请求统计（用于监控）
            stats_key = f"request_stats:{int(current_time // 60)}"  # 按分钟统计
            
            await redis_client._redis.hincrby(stats_key, "total_requests", 1)
            await redis_client._redis.hincrby(stats_key, f"status_{status_code}", 1)
            await redis_client._redis.hincrby(stats_key, f"path_{request.url.path}", 1)
            
            # 设置统计数据过期时间（保留1小时）
            await redis_client._redis.expire(stats_key, 3600)
            
        except Exception as e:
            logger.error(
                f"请求统计记录异常: {str(e)}",
                operation="record_request_stats",
                data=client_info
            )
    
    def _create_rate_limit_response(self, rate_limit_result: dict) -> Response:
        """创建限流响应"""
        error_data = {
            "success": False,
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": rate_limit_result["reason"],
                "details": {
                    "retry_after": rate_limit_result.get("retry_after"),
                    "timestamp": time.time()
                }
            }
        }
        
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Retry-After": str(rate_limit_result.get("retry_after", 60))
        }
        
        # 添加限流详情头
        if rate_limit_result.get("details"):
            details = rate_limit_result["details"]
            for limit_type, info in details.items():
                if not info.get("limited"):
                    headers[f"X-RateLimit-{limit_type.title()}-Limit"] = str(info.get("limit", 0))
                    headers[f"X-RateLimit-{limit_type.title()}-Remaining"] = str(
                        max(0, info.get("limit", 0) - info.get("usage", 0))
                    )
                    headers[f"X-RateLimit-{limit_type.title()}-Reset"] = str(
                        int(time.time() + info.get("window", 60))
                    )
        
        return Response(
            content=json.dumps(error_data, ensure_ascii=False),
            status_code=429,
            headers=headers
        )
    
    def _add_rate_limit_headers(self, response: Response, rate_limit_result: dict):
        """添加限流信息头"""
        if not rate_limit_result.get("details"):
            return
        
        details = rate_limit_result["details"]
        
        for limit_type, info in details.items():
            if info.get("limit") and info.get("usage") is not None:
                response.headers[f"X-RateLimit-{limit_type.title()}-Limit"] = str(info["limit"])
                response.headers[f"X-RateLimit-{limit_type.title()}-Remaining"] = str(
                    max(0, info["limit"] - info["usage"])
                )
                response.headers[f"X-RateLimit-{limit_type.title()}-Reset"] = str(
                    int(time.time() + info.get("window", 60))
                )


class DynamicRateLimitMiddleware(RateLimitMiddleware):
    """
    动态限流中间件
    
    根据系统负载、用户等级等因素动态调整限流参数
    """
    
    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.user_tier_limits = {
            "premium": (10000, 3600),  # 高级用户更宽松的限制
            "standard": (5000, 3600),  # 标准用户
            "basic": (1000, 3600)      # 基础用户更严格的限制
        }
    
    async def _get_user_rate_limit(self, client_info: dict) -> Tuple[int, int]:
        """根据用户等级获取限流配置"""
        user_tier = client_info.get("user_tier", "standard")
        return self.user_tier_limits.get(user_tier, self.user_rate_limit)