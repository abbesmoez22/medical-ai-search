from fastapi import APIRouter, HTTPException, status
from app.core.config import settings
import structlog

logger = structlog.get_logger()
router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Comprehensive health check for Search API Service"""
    health_status = {
        "service": "search-api",
        "version": "1.0.0",
        "status": "healthy",
        "timestamp": "",
        "checks": {}
    }
    
    overall_healthy = True
    
    # Import here to avoid circular dependencies
    from app.services.search_service import SearchService
    search_service = SearchService()
    
    # Redis check
    try:
        await search_service.redis_client.ping()
        health_status["checks"]["redis"] = {
            "status": "healthy",
            "message": "Redis connection successful"
        }
    except Exception as e:
        overall_healthy = False
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "message": f"Redis connection failed: {str(e)}"
        }
    
    # Elasticsearch check
    try:
        info = await search_service.es_client.info()
        health_status["checks"]["elasticsearch"] = {
            "status": "healthy",
            "message": "Elasticsearch connection successful",
            "version": info.get("version", {}).get("number", "unknown")
        }
    except Exception as e:
        overall_healthy = False
        health_status["checks"]["elasticsearch"] = {
            "status": "unhealthy",
            "message": f"Elasticsearch connection failed: {str(e)}"
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
    
    # Index check
    try:
        index_exists = await search_service.es_client.indices.exists(
            index=search_service.index_name
        )
        if index_exists:
            health_status["checks"]["search_index"] = {
                "status": "healthy",
                "message": f"Search index '{search_service.index_name}' exists"
            }
        else:
            health_status["checks"]["search_index"] = {
                "status": "warning",
                "message": f"Search index '{search_service.index_name}' does not exist"
            }
    except Exception as e:
        health_status["checks"]["search_index"] = {
            "status": "warning",
            "message": f"Failed to check search index: {str(e)}"
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
        from app.services.search_service import SearchService
        search_service = SearchService()
        
        # Check critical dependencies only
        await search_service.es_client.info()
        
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
        "service": "search-api",
        "version": "1.0.0"
    }