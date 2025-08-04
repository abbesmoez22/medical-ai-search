import redis.asyncio as redis
from app.core.config import settings
import structlog

logger = structlog.get_logger()

# Create Redis client
redis_client = redis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5,
    retry_on_timeout=True,
    max_connections=20
)


async def get_redis():
    """Dependency to get Redis client"""
    return redis_client