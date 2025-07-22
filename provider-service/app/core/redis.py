"""
Redis连接和配置管理

提供Redis连接池管理、异步操作支持和缓存功能。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import logging
from typing import Optional, Any
import redis.asyncio as redis
from redis.asyncio import Redis

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# 全局Redis连接实例
_redis_client: Optional[Redis] = None


async def init_redis() -> None:
    """
    初始化Redis连接
    
    创建Redis连接池并验证连接。
    """
    global _redis_client
    
    try:
        # 创建Redis连接
        _redis_client = redis.from_url(
            settings.redis_url,
            password=settings.redis_password,
            max_connections=settings.redis_pool_size,
            socket_timeout=settings.redis_timeout,
            socket_connect_timeout=10,
            health_check_interval=30,
            decode_responses=True
        )
        
        # 测试连接
        await _redis_client.ping()
        
        logger.info("Redis连接初始化成功")
        
    except Exception as e:
        logger.error(f"Redis连接初始化失败: {e}")
        raise


def get_redis() -> Redis:
    """
    获取Redis连接实例
    
    Returns:
        Redis: Redis连接实例
        
    Raises:
        RuntimeError: 如果Redis未初始化
    """
    if _redis_client is None:
        raise RuntimeError("Redis未初始化，请先调用init_redis()")
    
    return _redis_client


async def close_redis() -> None:
    """
    关闭Redis连接
    """
    global _redis_client
    
    if _redis_client:
        try:
            await _redis_client.close()
            logger.info("Redis连接已关闭")
        except Exception as e:
            logger.error(f"关闭Redis连接失败: {e}")
        finally:
            _redis_client = None


class RedisCache:
    """
    Redis缓存辅助类
    
    提供常用的缓存操作方法。
    """
    
    def __init__(self, redis_client: Optional[Redis] = None):
        self.redis = redis_client or get_redis()
    
    async def get(self, key: str) -> Optional[str]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            Optional[str]: 缓存值或None
        """
        try:
            return await self.redis.get(key)
        except Exception as e:
            logger.error(f"Redis GET操作失败 - key: {key}, error: {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: str, 
        ttl: Optional[int] = None
    ) -> bool:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒）
            
        Returns:
            bool: 是否设置成功
        """
        try:
            if ttl:
                return await self.redis.setex(key, ttl, value)
            else:
                return await self.redis.set(key, value)
        except Exception as e:
            logger.error(f"Redis SET操作失败 - key: {key}, error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        删除缓存键
        
        Args:
            key: 缓存键
            
        Returns:
            bool: 是否删除成功
        """
        try:
            result = await self.redis.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis DELETE操作失败 - key: {key}, error: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        检查键是否存在
        
        Args:
            key: 缓存键
            
        Returns:
            bool: 键是否存在
        """
        try:
            result = await self.redis.exists(key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis EXISTS操作失败 - key: {key}, error: {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """
        设置键的过期时间
        
        Args:
            key: 缓存键
            ttl: 过期时间（秒）
            
        Returns:
            bool: 是否设置成功
        """
        try:
            return await self.redis.expire(key, ttl)
        except Exception as e:
            logger.error(f"Redis EXPIRE操作失败 - key: {key}, ttl: {ttl}, error: {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """
        获取键的剩余过期时间
        
        Args:
            key: 缓存键
            
        Returns:
            int: 剩余时间（秒），-1表示永不过期，-2表示键不存在
        """
        try:
            return await self.redis.ttl(key)
        except Exception as e:
            logger.error(f"Redis TTL操作失败 - key: {key}, error: {e}")
            return -2
    
    async def hget(self, key: str, field: str) -> Optional[str]:
        """
        获取哈希字段值
        
        Args:
            key: 哈希键
            field: 字段名
            
        Returns:
            Optional[str]: 字段值或None
        """
        try:
            return await self.redis.hget(key, field)
        except Exception as e:
            logger.error(f"Redis HGET操作失败 - key: {key}, field: {field}, error: {e}")
            return None
    
    async def hset(self, key: str, field: str, value: str) -> bool:
        """
        设置哈希字段值
        
        Args:
            key: 哈希键
            field: 字段名
            value: 字段值
            
        Returns:
            bool: 是否设置成功
        """
        try:
            result = await self.redis.hset(key, field, value)
            return result >= 0
        except Exception as e:
            logger.error(f"Redis HSET操作失败 - key: {key}, field: {field}, error: {e}")
            return False
    
    async def hdel(self, key: str, field: str) -> bool:
        """
        删除哈希字段
        
        Args:
            key: 哈希键
            field: 字段名
            
        Returns:
            bool: 是否删除成功
        """
        try:
            result = await self.redis.hdel(key, field)
            return result > 0
        except Exception as e:
            logger.error(f"Redis HDEL操作失败 - key: {key}, field: {field}, error: {e}")
            return False
    
    async def hgetall(self, key: str) -> dict:
        """
        获取哈希的所有字段和值
        
        Args:
            key: 哈希键
            
        Returns:
            dict: 所有字段和值的字典
        """
        try:
            return await self.redis.hgetall(key)
        except Exception as e:
            logger.error(f"Redis HGETALL操作失败 - key: {key}, error: {e}")
            return {}
    
    async def sadd(self, key: str, *members: str) -> int:
        """
        向集合添加成员
        
        Args:
            key: 集合键
            members: 成员列表
            
        Returns:
            int: 添加的成员数量
        """
        try:
            return await self.redis.sadd(key, *members)
        except Exception as e:
            logger.error(f"Redis SADD操作失败 - key: {key}, error: {e}")
            return 0
    
    async def srem(self, key: str, *members: str) -> int:
        """
        从集合移除成员
        
        Args:
            key: 集合键
            members: 成员列表
            
        Returns:
            int: 移除的成员数量
        """
        try:
            return await self.redis.srem(key, *members)
        except Exception as e:
            logger.error(f"Redis SREM操作失败 - key: {key}, error: {e}")
            return 0
    
    async def sismember(self, key: str, member: str) -> bool:
        """
        检查成员是否在集合中
        
        Args:
            key: 集合键
            member: 成员
            
        Returns:
            bool: 是否在集合中
        """
        try:
            return await self.redis.sismember(key, member)
        except Exception as e:
            logger.error(f"Redis SISMEMBER操作失败 - key: {key}, member: {member}, error: {e}")
            return False
    
    async def smembers(self, key: str) -> set:
        """
        获取集合的所有成员
        
        Args:
            key: 集合键
            
        Returns:
            set: 成员集合
        """
        try:
            return await self.redis.smembers(key)
        except Exception as e:
            logger.error(f"Redis SMEMBERS操作失败 - key: {key}, error: {e}")
            return set()


def get_cache() -> RedisCache:
    """
    获取Redis缓存实例
    
    Returns:
        RedisCache: 缓存操作实例
    """
    return RedisCache()


async def health_check() -> bool:
    """
    Redis健康检查
    
    Returns:
        bool: Redis是否正常
    """
    try:
        redis_client = get_redis()
        await redis_client.ping()
        return True
    except Exception as e:
        logger.error(f"Redis健康检查失败: {e}")
        return False