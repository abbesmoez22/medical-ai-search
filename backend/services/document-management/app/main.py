from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.database import create_tables
from app.core.redis import close_redis_client
from app.events.publisher import document_event_publisher
from app.api.v1.router import router as v1_router
from app.api.health import router as health_router
import structlog

# Configure logging
configure_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting Document Management Service", version="1.0.0")
    
    try:
        # Initialize database tables
        await create_tables()
        logger.info("Database tables initialized")
        
        # Initialize Kafka producer
        await document_event_publisher.initialize()
        logger.info("Kafka producer initialized")
        
        logger.info("Document Management Service started successfully")
        
    except Exception as e:
        logger.error("Failed to start service", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Document Management Service")
    
    try:
        # Close Kafka producer
        await document_event_publisher.close()
        logger.info("Kafka producer closed")
        
        # Close Redis connection
        await close_redis_client()
        logger.info("Redis connection closed")
        
        logger.info("Document Management Service shut down successfully")
        
    except Exception as e:
        logger.error("Error during shutdown", error=str(e))


# Create FastAPI application
app = FastAPI(
    title="Document Management Service",
    description="Medical AI Platform - Document Management Service",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else ["https://medical-ai-platform.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(v1_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "document-management",
        "version": "1.0.0",
        "status": "running",
        "docs_url": "/docs" if settings.DEBUG else None
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)