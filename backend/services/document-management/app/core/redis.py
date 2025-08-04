import redis.asyncio as redis
from app.core.config import settings
import structlog

logger = structlog.get_logger()

# Global Redis client
redis_client: redis.Redis = None


async def get_redis_client() -> redis.Redis:
    """Get Redis client instance"""
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_keepalive=True,
            socket_keepalive_options={},
            health_check_interval=30,
        )
    return redis_client


async def close_redis_client():
    """Close Redis client connection"""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None


async def get_redis() -> redis.Redis:
    """Dependency to get Redis client"""
    return await get_redis_client()