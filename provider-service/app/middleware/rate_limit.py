"""
限流中间件

基于Redis的分布式限流实现，支持多种限流策略。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import logging
import time
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status
from redis.asyncio import Redis

from ..core.config import get_settings
from ..core.redis import get_redis

logger = logging.getLogger(__name__)
settings = get_settings()


class RateLimiter:
    """分布式限流器"""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        
    async def is_rate_limited(
        self,
        key: str,
        limit: int,
        window: int,
        tenant_id: str = None
    ) -> tuple[bool, Dict[str, Any]]:
        """
        检查是否触发限流
        
        Args:
            key: 限流键（通常是用户ID或IP）
            limit: 限流次数
            window: 时间窗口（秒）
            tenant_id: 租户ID（可选）
            
        Returns:
            tuple[bool, Dict]: (是否限流, 限流信息)
        """
        # 构建Redis键名
        redis_key = f"rate_limit:{tenant_id}:{key}" if tenant_id else f"rate_limit:{key}"
        current_time = int(time.time())
        
        try:
            # 使用滑动窗口算法
            async with self.redis.pipeline() as pipe:
                # 清理过期记录
                await pipe.zremrangebyscore(
                    redis_key, 
                    0, 
                    current_time - window
                )
                
                # 统计当前窗口内的请求数
                count = await pipe.zcard(redis_key)
                
                if count >= limit:
                    # 触发限流
                    ttl = await self.redis.ttl(redis_key)
                    retry_after = max(1, ttl)
                    
                    return True, {
                        "limited": True,
                        "limit": limit,
                        "remaining": 0,
                        "reset_time": current_time + retry_after,
                        "retry_after": retry_after
                    }
                
                # 添加当前请求
                await pipe.zadd(redis_key, {str(current_time): current_time})
                await pipe.expire(redis_key, window)
                await pipe.execute()
                
                return False, {
                    "limited": False,
                    "limit": limit,
                    "remaining": limit - count - 1,
                    "reset_time": current_time + window,
                    "retry_after": 0
                }
                
        except Exception as e:
            logger.error(f"限流检查失败: {e}")
            # 出错时不限流，但记录日志
            return False, {
                "limited": False,
                "limit": limit,
                "remaining": limit,
                "error": str(e)
            }


# 全局限流器实例
rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """获取限流器实例"""
    global rate_limiter
    if not rate_limiter:
        redis_client = get_redis()
        rate_limiter = RateLimiter(redis_client)
    return rate_limiter


async def rate_limit_middleware(request: Request, call_next):
    """
    限流中间件
    
    对API请求进行限流控制，防止滥用。
    
    Args:
        request: FastAPI请求对象
        call_next: 下一个中间件或路由处理器
        
    Returns:
        Response: 处理后的响应
        
    Raises:
        HTTPException 429: 请求频率过高
    """
    # 跳过不需要限流的路径
    exempt_paths = [
        "/health",
        "/docs", 
        "/openapi.json",
        "/redoc"
    ]
    
    if request.url.path in exempt_paths:
        return await call_next(request)
    
    try:
        # 获取客户端信息
        client_ip = request.client.host
        user_id = getattr(request.state, "user_id", None)
        tenant_id = getattr(request.state, "tenant_id", None)
        
        # 构建限流键
        if user_id and tenant_id:
            # 已认证用户：基于用户ID限流
            rate_key = f"user:{user_id}"
            limit_config = settings.rate_limit_per_user
        else:
            # 未认证请求：基于IP限流
            rate_key = f"ip:{client_ip}"
            limit_config = settings.rate_limit_per_ip
        
        # 解析限流配置
        requests_per_minute = limit_config.get("requests_per_minute", 60)
        requests_per_hour = limit_config.get("requests_per_hour", 1000)
        
        # 获取限流器
        limiter = get_rate_limiter()
        
        # 检查分钟级限流
        is_limited_minute, info_minute = await limiter.is_rate_limited(
            key=f"{rate_key}:minute",
            limit=requests_per_minute,
            window=60,
            tenant_id=tenant_id
        )
        
        # 检查小时级限流
        is_limited_hour, info_hour = await limiter.is_rate_limited(
            key=f"{rate_key}:hour", 
            limit=requests_per_hour,
            window=3600,
            tenant_id=tenant_id
        )
        
        # 判断是否触发限流
        if is_limited_minute or is_limited_hour:
            limit_info = info_minute if is_limited_minute else info_hour
            limit_type = "分钟" if is_limited_minute else "小时"
            
            logger.warning(
                f"触发{limit_type}级限流 - key: {rate_key}, "
                f"tenant: {tenant_id}, limit: {limit_info['limit']}"
            )
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"请求频率过高，请{limit_info['retry_after']}秒后重试",
                headers={
                    "Retry-After": str(limit_info["retry_after"]),
                    "X-RateLimit-Limit": str(limit_info["limit"]),
                    "X-RateLimit-Remaining": str(limit_info["remaining"]),
                    "X-RateLimit-Reset": str(limit_info["reset_time"])
                }
            )
        
        # 添加限流信息到响应头
        response = await call_next(request)
        
        response.headers["X-RateLimit-Limit-Minute"] = str(requests_per_minute)
        response.headers["X-RateLimit-Remaining-Minute"] = str(info_minute["remaining"])
        response.headers["X-RateLimit-Limit-Hour"] = str(requests_per_hour)
        response.headers["X-RateLimit-Remaining-Hour"] = str(info_hour["remaining"])
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"限流中间件处理失败: {e}")
        # 出错时不阻止请求，继续处理
        return await call_next(request)


async def check_api_quota(tenant_id: str, endpoint: str) -> bool:
    """
    检查API配额
    
    验证租户是否还有可用的API调用配额。
    
    Args:
        tenant_id: 租户ID
        endpoint: API端点
        
    Returns:
        bool: 是否有可用配额
    """
    try:
        from ..services.quota_service import QuotaService
        from ..core.database import get_db
        
        # 获取配额服务
        db = next(get_db())
        quota_service = QuotaService(db)
        
        # 检查每日API调用配额
        available, _ = quota_service.check_quota_availability(
            tenant_id=tenant_id,
            quota_type="daily_api_calls",
            requested_amount=1.0
        )
        
        return available
        
    except Exception as e:
        logger.error(f"配额检查失败: {e}")
        # 出错时允许请求通过
        return True