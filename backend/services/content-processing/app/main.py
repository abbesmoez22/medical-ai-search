import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import create_tables
from app.services.document_processor import DocumentProcessorService
from app.api.v1.processing import router as processing_router
from app.api.health import router as health_router
import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Global processor service
processor_service = DocumentProcessorService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting Content Processing Service", version="1.0.0")
    
    try:
        # Initialize database tables
        await create_tables()
        logger.info("Database tables initialized")
        
        # Initialize processor service
        await processor_service.initialize()
        logger.info("Document processor service initialized")
        
        # Start Kafka consumer in background
        consumer_task = asyncio.create_task(processor_service.start_kafka_consumer())
        logger.info("Kafka consumer started")
        
        logger.info("Content Processing Service started successfully")
        
    except Exception as e:
        logger.error("Failed to start service", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Content Processing Service")
    
    try:
        # Stop Kafka consumer
        await processor_service.stop_kafka_consumer()
        logger.info("Kafka consumer stopped")
        
        # Close processor service
        await processor_service.close()
        logger.info("Document processor service closed")
        
        logger.info("Content Processing Service shut down successfully")
        
    except Exception as e:
        logger.error("Error during shutdown", error=str(e))


# Create FastAPI application
app = FastAPI(
    title="Content Processing Service",
    description="Medical AI Platform - Content Processing Service",
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
app.include_router(processing_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "content-processing",
        "version": "1.0.0",
        "status": "running",
        "docs_url": "/docs" if settings.DEBUG else None
    }


# Dependency injection for processor service
def get_processor_service() -> DocumentProcessorService:
    return processor_service


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)