"""
Redis client and connection management
"""
import json
import asyncio
from typing import Optional, Any, Dict, Union, List
from contextlib import asynccontextmanager
import redis.asyncio as redis
from redis.asyncio import Redis

from .config import get_settings

settings = get_settings()


class RedisManager:
    """Redis connection manager"""
    
    def __init__(self):
        self.redis_client: Optional[Redis] = None
        self._is_connected = False
        self.connection_pool = None
    
    async def connect(self) -> None:
        """Initialize Redis connection"""
        if self._is_connected:
            return
        
        try:
            self.connection_pool = redis.ConnectionPool.from_url(
                settings.redis_url,
                max_connections=settings.redis_max_connections,
                socket_timeout=settings.redis_socket_timeout,
                socket_connect_timeout=settings.redis_socket_connect_timeout,
                decode_responses=True
            )
            
            self.redis_client = redis.Redis(connection_pool=self.connection_pool)
            
            # Test connection
            await self.redis_client.ping()
            self._is_connected = True
            print("Redis connected successfully")
        except Exception as e:
            print(f"Redis connection failed: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close Redis connection"""
        if not self._is_connected:
            return
        
        try:
            if self.redis_client:
                await self.redis_client.close()
            if self.connection_pool:
                await self.connection_pool.disconnect()
            self._is_connected = False
            print("Redis disconnected successfully")
        except Exception as e:
            print(f"Redis disconnection failed: {e}")
            raise
    
    async def health_check(self) -> bool:
        """Check Redis health"""
        try:
            if not self.redis_client:
                return False
            await self.redis_client.ping()
            return True
        except Exception:
            return False
    
    def get_client(self) -> Redis:
        """Get Redis client instance"""
        if not self._is_connected or not self.redis_client:
            raise RuntimeError("Redis is not connected")
        return self.redis_client


# Global Redis manager instance
redis_manager = RedisManager()


class TenantRedisClient:
    """Tenant-aware Redis client wrapper"""
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.redis_client = redis_manager.get_client()
    
    def _get_key(self, key: str) -> str:
        """Get tenant-prefixed key"""
        return f"tenant:{self.tenant_id}:{key}"
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        return await self.redis_client.get(self._get_key(key))
    
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set value with optional expiration"""
        return await self.redis_client.set(self._get_key(key), value, ex=ex)
    
    async def delete(self, key: str) -> int:
        """Delete key"""
        return await self.redis_client.delete(self._get_key(key))
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        return bool(await self.redis_client.exists(self._get_key(key)))
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for key"""
        return await self.redis_client.expire(self._get_key(key), seconds)
    
    async def ttl(self, key: str) -> int:
        """Get time to live for key"""
        return await self.redis_client.ttl(self._get_key(key))
    
    async def incr(self, key: str) -> int:
        """Increment key value"""
        return await self.redis_client.incr(self._get_key(key))
    
    async def decr(self, key: str) -> int:
        """Decrement key value"""
        return await self.redis_client.decr(self._get_key(key))
    
    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get hash field value"""
        return await self.redis_client.hget(self._get_key(name), key)
    
    async def hset(self, name: str, key: str, value: str) -> int:
        """Set hash field value"""
        return await self.redis_client.hset(self._get_key(name), key, value)
    
    async def hgetall(self, name: str) -> Dict[str, str]:
        """Get all hash fields"""
        return await self.redis_client.hgetall(self._get_key(name))
    
    async def hdel(self, name: str, *keys: str) -> int:
        """Delete hash fields"""
        return await self.redis_client.hdel(self._get_key(name), *keys)
    
    async def sadd(self, name: str, *values: str) -> int:
        """Add to set"""
        return await self.redis_client.sadd(self._get_key(name), *values)
    
    async def srem(self, name: str, *values: str) -> int:
        """Remove from set"""
        return await self.redis_client.srem(self._get_key(name), *values)
    
    async def smembers(self, name: str) -> set:
        """Get all set members"""
        return await self.redis_client.smembers(self._get_key(name))
    
    async def sismember(self, name: str, value: str) -> bool:
        """Check if value is in set"""
        return await self.redis_client.sismember(self._get_key(name), value)


class CacheManager:
    """High-level cache management"""
    
    def __init__(self, tenant_id: str):
        self.tenant_client = TenantRedisClient(tenant_id)
    
    async def get_json(self, key: str) -> Optional[Any]:
        """Get JSON value"""
        value = await self.tenant_client.get(key)
        if value:
            return json.loads(value)
        return None
    
    async def set_json(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Set JSON value"""
        json_value = json.dumps(value, ensure_ascii=False)
        return await self.tenant_client.set(key, json_value, ex=ex)
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get user session"""
        return await self.get_json(f"session:{session_id}")
    
    async def set_session(self, session_id: str, session_data: Dict[str, Any], 
                         ex: int = 3600) -> bool:
        """Set user session"""
        return await self.set_json(f"session:{session_id}", session_data, ex=ex)
    
    async def delete_session(self, session_id: str) -> int:
        """Delete user session"""
        return await self.tenant_client.delete(f"session:{session_id}")
    
    async def get_rate_limit(self, key: str) -> Optional[int]:
        """Get rate limit counter"""
        value = await self.tenant_client.get(f"rate_limit:{key}")
        return int(value) if value else None
    
    async def increment_rate_limit(self, key: str, window: int = 60) -> int:
        """Increment rate limit counter"""
        full_key = f"rate_limit:{key}"
        current = await self.tenant_client.incr(full_key)
        if current == 1:
            await self.tenant_client.expire(full_key, window)
        return current
    
    async def get_conversation_cache(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation cache"""
        return await self.get_json(f"conversation:{conversation_id}")
    
    async def set_conversation_cache(self, conversation_id: str, 
                                   conversation_data: Dict[str, Any], 
                                   ex: int = 3600) -> bool:
        """Set conversation cache"""
        return await self.set_json(f"conversation:{conversation_id}", conversation_data, ex=ex)


class RateLimiter:
    """Rate limiting utility"""
    
    def __init__(self, tenant_id: str, user_id: str):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.cache = CacheManager(tenant_id)
    
    async def check_rate_limit(self, action: str, limit: int, window: int = 60) -> tuple[bool, int]:
        """Check if action is within rate limit"""
        key = f"user:{self.user_id}:{action}"
        current = await self.cache.increment_rate_limit(key, window)
        
        is_allowed = current <= limit
        remaining = max(0, limit - current)
        
        return is_allowed, remaining
    
    async def get_rate_limit_info(self, action: str) -> tuple[int, int]:
        """Get current rate limit info"""
        key = f"user:{self.user_id}:{action}"
        current = await self.cache.get_rate_limit(key) or 0
        ttl = await self.cache.tenant_client.ttl(f"rate_limit:{key}")
        
        return current, ttl


# Redis lifecycle management
async def init_redis() -> None:
    """Initialize Redis on startup"""
    await redis_manager.connect()


async def close_redis() -> None:
    """Close Redis on shutdown"""
    await redis_manager.disconnect()


# Dependency functions for FastAPI
async def get_redis() -> Redis:
    """FastAPI dependency for Redis client"""
    return redis_manager.get_client()


async def get_tenant_redis(tenant_id: str) -> TenantRedisClient:
    """FastAPI dependency for tenant-specific Redis client"""
    return TenantRedisClient(tenant_id)


async def get_cache_manager(tenant_id: str) -> CacheManager:
    """FastAPI dependency for cache manager"""
    return CacheManager(tenant_id)