"""
Redis client configuration for session management and caching
"""

import json
from typing import Any, Optional, Union
from redis.asyncio import Redis, ConnectionPool
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class RedisClient:
    """Redis client wrapper with connection pooling and error handling"""
    
    def __init__(self):
        self.pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            decode_responses=True,
        )
        self.redis = Redis(connection_pool=self.pool)
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        try:
            return await self.redis.get(key)
        except Exception as e:
            logger.error("Redis GET failed", key=key, error=str(e))
            return None
    
    async def set(
        self, 
        key: str, 
        value: Union[str, dict, list], 
        expire: Optional[int] = None
    ) -> bool:
        """Set key-value pair with optional expiration"""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            result = await self.redis.set(key, value, ex=expire)
            return bool(result)
        except Exception as e:
            logger.error("Redis SET failed", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key"""
        try:
            result = await self.redis.delete(key)
            return bool(result)
        except Exception as e:
            logger.error("Redis DELETE failed", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            result = await self.redis.exists(key)
            return bool(result)
        except Exception as e:
            logger.error("Redis EXISTS failed", key=key, error=str(e))
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment counter"""
        try:
            result = await self.redis.incrby(key, amount)
            return result
        except Exception as e:
            logger.error("Redis INCR failed", key=key, error=str(e))
            return None
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key"""
        try:
            result = await self.redis.expire(key, seconds)
            return bool(result)
        except Exception as e:
            logger.error("Redis EXPIRE failed", key=key, error=str(e))
            return False
    
    async def get_json(self, key: str) -> Optional[Any]:
        """Get JSON value by key"""
        try:
            value = await self.get(key)
            if value:
                return json.loads(value)
            return None
        except (json.JSONDecodeError, Exception) as e:
            logger.error("Redis GET_JSON failed", key=key, error=str(e))
            return None
    
    async def set_json(
        self, 
        key: str, 
        value: Any, 
        expire: Optional[int] = None
    ) -> bool:
        """Set JSON value with optional expiration"""
        try:
            json_value = json.dumps(value)
            return await self.set(key, json_value, expire)
        except (TypeError, Exception) as e:
            logger.error("Redis SET_JSON failed", key=key, error=str(e))
            return False
    
    async def ping(self) -> bool:
        """Test Redis connection"""
        try:
            result = await self.redis.ping()
            return result
        except Exception as e:
            logger.error("Redis PING failed", error=str(e))
            return False
    
    async def close(self):
        """Close Redis connection"""
        try:
            await self.redis.close()
        except Exception as e:
            logger.error("Redis close failed", error=str(e))


# Global Redis client instance
redis_client = RedisClient()