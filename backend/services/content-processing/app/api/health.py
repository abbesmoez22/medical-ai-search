from fastapi import APIRouter, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db, engine
from app.core.config import settings
import structlog
import boto3
from botocore.exceptions import ClientError
from kafka import KafkaProducer
from kafka.errors import KafkaError
import asyncio
from sqlalchemy import text

logger = structlog.get_logger()
router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Comprehensive health check for Content Processing Service"""
    health_status = {
        "service": "content-processing",
        "version": "1.0.0",
        "status": "healthy",
        "timestamp": "",
        "checks": {}
    }
    
    overall_healthy = True
    
    # Database check
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        overall_healthy = False
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
    
    # S3 check
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        # Try to list buckets to verify connection
        s3_client.list_buckets()
        health_status["checks"]["s3"] = {
            "status": "healthy",
            "message": "S3 connection successful"
        }
    except ClientError as e:
        overall_healthy = False
        health_status["checks"]["s3"] = {
            "status": "unhealthy",
            "message": f"S3 connection failed: {str(e)}"
        }
    except Exception as e:
        # For development, S3 might not be available
        health_status["checks"]["s3"] = {
            "status": "warning",
            "message": f"S3 connection warning: {str(e)}"
        }
    
    # Kafka check
    try:
        producer = KafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            request_timeout_ms=5000,
            api_version=(0, 10, 1)
        )
        producer.close()
        health_status["checks"]["kafka"] = {
            "status": "healthy",
            "message": "Kafka connection successful"
        }
    except KafkaError as e:
        overall_healthy = False
        health_status["checks"]["kafka"] = {
            "status": "unhealthy",
            "message": f"Kafka connection failed: {str(e)}"
        }
    except Exception as e:
        overall_healthy = False
        health_status["checks"]["kafka"] = {
            "status": "unhealthy",
            "message": f"Kafka connection error: {str(e)}"
        }
    
    # Auth Service check
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.AUTH_SERVICE_URL}/health",
                timeout=5.0
            )
            if response.status_code == 200:
                health_status["checks"]["auth_service"] = {
                    "status": "healthy",
                    "message": "Auth service connection successful"
                }
            else:
                health_status["checks"]["auth_service"] = {
                    "status": "warning",
                    "message": f"Auth service returned status {response.status_code}"
                }
    except Exception as e:
        health_status["checks"]["auth_service"] = {
            "status": "warning",
            "message": f"Auth service connection warning: {str(e)}"
        }
    
    # Overall status
    if not overall_healthy:
        health_status["status"] = "unhealthy"
        return health_status
    
    # Check for warnings
    warning_count = sum(1 for check in health_status["checks"].values() 
                       if check["status"] == "warning")
    if warning_count > 0:
        health_status["status"] = "degraded"
    
    from datetime import datetime
    health_status["timestamp"] = datetime.utcnow().isoformat()
    
    return health_status


@router.get("/ready")
async def readiness_check():
    """Readiness probe - checks if service is ready to handle requests"""
    try:
        # Check critical dependencies only
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        
        return {
            "status": "ready",
            "message": "Service is ready to handle requests"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not ready: {str(e)}"
        )


@router.get("/live")
async def liveness_check():
    """Liveness probe - basic service health"""
    return {
        "status": "alive",
        "service": "content-processing",
        "version": "1.0.0"
    }