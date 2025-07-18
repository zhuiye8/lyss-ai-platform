"""
Auth Service Redis缓存客户端
实现Redis连接管理和缓存操作
用于速率限制、令牌黑名单等功能
"""

import json
from typing import Any, Optional, Union
from datetime import timedelta

import redis.asyncio as redis
from redis.asyncio import Redis
from redis.exceptions import ConnectionError, RedisError

from ..core.exceptions import RedisConnectionError
from ..config import settings


class RedisClient:
    """Redis异步客户端封装"""

    def __init__(self):
        self._redis: Optional[Redis] = None

    async def connect(self) -> None:
        """建立Redis连接"""
        try:
            self._redis = await redis.from_url(
                settings.get_redis_url(),
                max_connections=settings.redis_max_connections,
                decode_responses=True,
                encoding="utf-8",
            )
            # 测试连接
            await self._redis.ping()
        except ConnectionError as e:
            raise RedisConnectionError(
                message="无法连接到Redis服务器",
                details={"redis_url": settings.get_redis_url(), "error": str(e)},
            )

    async def disconnect(self) -> None:
        """断开Redis连接"""
        if self._redis:
            await self._redis.close()
            self._redis = None

    async def is_connected(self) -> bool:
        """检查Redis连接状态"""
        if not self._redis:
            return False
        try:
            await self._redis.ping()
            return True
        except RedisError:
            return False

    async def set(
        self,
        key: str,
        value: Union[str, dict, list, int, float],
        expire: Optional[Union[int, timedelta]] = None,
    ) -> bool:
        """
        设置键值对

        Args:
            key: 键名
            value: 值（自动序列化JSON）
            expire: 过期时间（秒或timedelta对象）

        Returns:
            bool: 操作是否成功
        """
        if not self._redis:
            raise RedisConnectionError("Redis客户端未连接")

        try:
            # 序列化值
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value, ensure_ascii=False)
            else:
                serialized_value = str(value)

            # 设置键值
            result = await self._redis.set(key, serialized_value, ex=expire)
            return result is True
        except RedisError as e:
            raise RedisConnectionError(
                message="Redis设置操作失败",
                details={"key": key, "error": str(e)},
            )

    async def get(self, key: str) -> Optional[Any]:
        """
        获取键值

        Args:
            key: 键名

        Returns:
            Any: 键对应的值，不存在返回None
        """
        if not self._redis:
            raise RedisConnectionError("Redis客户端未连接")

        try:
            value = await self._redis.get(key)
            if value is None:
                return None

            # 尝试解析JSON
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                # 不是JSON格式，返回原始字符串
                return value
        except RedisError as e:
            raise RedisConnectionError(
                message="Redis获取操作失败",
                details={"key": key, "error": str(e)},
            )

    async def delete(self, key: str) -> bool:
        """
        删除键

        Args:
            key: 键名

        Returns:
            bool: 是否删除成功
        """
        if not self._redis:
            raise RedisConnectionError("Redis客户端未连接")

        try:
            result = await self._redis.delete(key)
            return result > 0
        except RedisError as e:
            raise RedisConnectionError(
                message="Redis删除操作失败",
                details={"key": key, "error": str(e)},
            )

    async def exists(self, key: str) -> bool:
        """
        检查键是否存在

        Args:
            key: 键名

        Returns:
            bool: 键是否存在
        """
        if not self._redis:
            raise RedisConnectionError("Redis客户端未连接")

        try:
            result = await self._redis.exists(key)
            return result > 0
        except RedisError as e:
            raise RedisConnectionError(
                message="Redis检查操作失败",
                details={"key": key, "error": str(e)},
            )

    async def increment(self, key: str, amount: int = 1) -> int:
        """
        原子性递增

        Args:
            key: 键名
            amount: 递增量

        Returns:
            int: 递增后的值
        """
        if not self._redis:
            raise RedisConnectionError("Redis客户端未连接")

        try:
            return await self._redis.incrby(key, amount)
        except RedisError as e:
            raise RedisConnectionError(
                message="Redis递增操作失败",
                details={"key": key, "amount": amount, "error": str(e)},
            )

    async def expire(self, key: str, seconds: int) -> bool:
        """
        设置键过期时间

        Args:
            key: 键名
            seconds: 过期时间（秒）

        Returns:
            bool: 操作是否成功
        """
        if not self._redis:
            raise RedisConnectionError("Redis客户端未连接")

        try:
            result = await self._redis.expire(key, seconds)
            return result is True
        except RedisError as e:
            raise RedisConnectionError(
                message="Redis设置过期时间失败",
                details={"key": key, "seconds": seconds, "error": str(e)},
            )

    async def ttl(self, key: str) -> int:
        """
        获取键的剩余过期时间

        Args:
            key: 键名

        Returns:
            int: 剩余秒数，-1表示永不过期，-2表示键不存在
        """
        if not self._redis:
            raise RedisConnectionError("Redis客户端未连接")

        try:
            return await self._redis.ttl(key)
        except RedisError as e:
            raise RedisConnectionError(
                message="Redis获取TTL失败",
                details={"key": key, "error": str(e)},
            )


class RateLimiter:
    """基于Redis的速率限制器"""

    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client

    async def is_rate_limited(
        self, 
        identifier: str, 
        max_attempts: int, 
        window_seconds: int
    ) -> tuple[bool, int]:
        """
        检查是否触发速率限制

        Args:
            identifier: 标识符（如IP地址）
            max_attempts: 最大尝试次数
            window_seconds: 时间窗口（秒）

        Returns:
            tuple: (是否被限制, 当前尝试次数)
        """
        key = f"rate_limit:{identifier}"

        try:
            # 获取当前计数
            current_count = await self.redis.get(key)
            if current_count is None:
                current_count = 0
            else:
                current_count = int(current_count)

            # 检查是否超限
            if current_count >= max_attempts:
                return True, current_count

            # 递增计数器
            new_count = await self.redis.increment(key)

            # 如果是第一次访问，设置过期时间
            if new_count == 1:
                await self.redis.expire(key, window_seconds)

            return new_count > max_attempts, new_count

        except Exception as e:
            # Redis错误时不应阻止正常业务，记录日志并允许通过
            from ..utils.logging import logger
            logger.warning(
                f"速率限制检查失败，Redis错误: {str(e)}",
                operation="rate_limit_check",
                data={
                    "identifier": identifier,
                    "error": str(e),
                    "fallback_behavior": "allow_through"
                }
            )
            return False, 0

    async def reset_rate_limit(self, identifier: str) -> bool:
        """
        重置速率限制计数器

        Args:
            identifier: 标识符

        Returns:
            bool: 操作是否成功
        """
        key = f"rate_limit:{identifier}"
        return await self.redis.delete(key)


class TokenBlacklist:
    """JWT令牌黑名单管理"""

    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client

    async def add_token(self, jti: str, expires_at: int) -> bool:
        """
        将令牌添加到黑名单

        Args:
            jti: JWT令牌唯一标识
            expires_at: 令牌过期时间戳

        Returns:
            bool: 操作是否成功
        """
        key = f"blacklist:token:{jti}"
        
        # 计算TTL，黑名单只需保存到令牌过期
        import time
        ttl = max(1, expires_at - int(time.time()))
        
        return await self.redis.set(key, "blacklisted", expire=ttl)

    async def is_blacklisted(self, jti: str) -> bool:
        """
        检查令牌是否在黑名单中

        Args:
            jti: JWT令牌唯一标识

        Returns:
            bool: 令牌是否被拉黑
        """
        key = f"blacklist:token:{jti}"
        try:
            return await self.redis.exists(key)
        except Exception as e:
            # Redis错误时保守处理，假设令牌有效，记录错误日志
            from ..utils.logging import logger
            logger.warning(
                f"黑名单检查失败，Redis错误: {str(e)}",
                operation="blacklist_check",
                data={
                    "jti": jti,
                    "error": str(e),
                    "fallback_behavior": "assume_valid"
                }
            )
            return False


# 全局Redis客户端实例
redis_client = RedisClient()
rate_limiter = RateLimiter(redis_client)
token_blacklist = TokenBlacklist(redis_client)