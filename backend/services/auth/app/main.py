"""
FastAPI Authentication Service
Enterprise-grade authentication service with JWT, RBAC, and Redis session management
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import engine, create_tables
from app.core.redis import redis_client
from app.core.logging import setup_logging
#from app.events.publisher import auth_event_publisher


# Setup structured logging
setup_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting authentication service", version=settings.VERSION)
    
    # Create database tables
    await create_tables()
    
    # Test Redis connection
    try:
        await redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error("Redis connection failed", error=str(e))
        raise
    
    # Initialize event publisher
    try:
        #await auth_event_publisher.initialize()
        logger.info("Event publisher initialized")
    except Exception as e:
        logger.error("Event publisher initialization failed", error=str(e))
        # Don't raise - service can work without events
    
    yield
    
    # Shutdown
    logger.info("Shutting down authentication service")
    #await auth_event_publisher.close()
    await redis_client.close()


# Create FastAPI application
app = FastAPI(
    title="Medical AI Authentication Service",
    description="Enterprise-grade authentication service for medical AI search platform",
    version=settings.VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_hosts_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts_list,
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log all HTTP requests with structured logging"""
    start_time = datetime.utcnow()
    
    # Get client IP
    client_ip = request.client.host
    if "x-forwarded-for" in request.headers:
        client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
    
    response = await call_next(request)
    
    process_time = (datetime.utcnow() - start_time).total_seconds()
    
    logger.info(
        "HTTP request processed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        process_time=process_time,
        client_ip=client_ip,
        user_agent=request.headers.get("user-agent"),
        service="auth-service"
    )
    
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with structured logging"""
    logger.error(
        "Unhandled exception",
        error=str(exc),
        error_type=type(exc).__name__,
        url=str(request.url),
        method=request.method,
        service="auth-service"
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }
    )


# Health check endpoint
@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for load balancer and monitoring"""
    try:
        # Check Redis connection
        redis_status = "healthy"
        try:
            await redis_client.ping()
        except Exception:
            redis_status = "unhealthy"
        
        # Check database connection
        db_status = "healthy"
        try:
            from sqlalchemy import text
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception:
            db_status = "unhealthy"
        
        overall_status = "healthy" if all([
            redis_status == "healthy",
            db_status == "healthy"
        ]) else "unhealthy"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.VERSION,
            "service": "auth-service",
            "dependencies": {
                "redis": redis_status,
                "database": db_status
            }
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
        )


# Include API routes
app.include_router(api_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_config=None  # Use our custom logging
    )