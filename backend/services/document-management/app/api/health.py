from datetime import datetime
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db
from app.core.redis import get_redis
from app.services.storage import get_storage_service, S3StorageService
from app.events.publisher import get_event_publisher, DocumentEventPublisher
import structlog

logger = structlog.get_logger()
router = APIRouter()


@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis),
    storage: S3StorageService = Depends(get_storage_service),
    event_publisher: DocumentEventPublisher = Depends(get_event_publisher)
):
    """Comprehensive health check for all dependencies"""
    
    health_status = {
        "service": "document-management",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "dependencies": {}
    }
    
    # Check database
    try:
        await db.execute(text("SELECT 1"))
        health_status["dependencies"]["database"] = "healthy"
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        health_status["dependencies"]["database"] = "unhealthy"
        health_status["status"] = "unhealthy"
    
    # Check Redis
    try:
        await redis_client.ping()
        health_status["dependencies"]["redis"] = "healthy"
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        health_status["dependencies"]["redis"] = "unhealthy"
        health_status["status"] = "unhealthy"
    
    # Check S3 connectivity
    try:
        # Try to list objects (limit 1) to test S3 connection
        storage.s3_client.list_objects_v2(Bucket=storage.bucket_name, MaxKeys=1)
        health_status["dependencies"]["s3"] = "healthy"
    except Exception as e:
        logger.error("S3 health check failed", error=str(e))
        health_status["dependencies"]["s3"] = "unhealthy"
        health_status["status"] = "unhealthy"
    
    # Check Kafka producer
    try:
        if event_publisher.producer:
            # Simple check if producer is available
            health_status["dependencies"]["kafka"] = "healthy"
        else:
            health_status["dependencies"]["kafka"] = "unhealthy"
            health_status["status"] = "unhealthy"
    except Exception as e:
        logger.error("Kafka health check failed", error=str(e))
        health_status["dependencies"]["kafka"] = "unhealthy"
        health_status["status"] = "unhealthy"
    
    # Set appropriate HTTP status code
    status_code = status.HTTP_200_OK if health_status["status"] == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return health_status


@router.get("/ready")
async def readiness_check():
    """Simple readiness check"""
    return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}


@router.get("/live")
async def liveness_check():
    """Simple liveness check"""
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}