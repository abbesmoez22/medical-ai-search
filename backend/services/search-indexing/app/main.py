import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import create_tables
from app.core.elasticsearch import create_indices
from app.services.indexing_service import DocumentIndexingService
from app.api.v1.indexing import router as indexing_router
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
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
indexing_service = DocumentIndexingService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Search Indexing Service")
    
    try:
        # Create database tables
        await create_tables()
        logger.info("Database tables created")
        
        # Create Elasticsearch indices
        await create_indices()
        logger.info("Elasticsearch indices created")
        
        # Initialize indexing service
        await indexing_service.initialize()
        logger.info("Indexing service initialized")
        
        # Start Kafka consumer
        await indexing_service.start_kafka_consumer()
        logger.info("Kafka consumer started")
        
    except Exception as e:
        logger.error("Failed to start Search Indexing Service", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Search Indexing Service")
    await indexing_service.stop_kafka_consumer()
    await indexing_service.close()


app = FastAPI(
    title="Search Indexing Service",
    description="Medical AI Platform - Search Indexing Service",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(indexing_router)


@app.get("/")
async def root():
    return {
        "service": "search-indexing",
        "version": "1.0.0",
        "status": "running"
    }


def get_indexing_service() -> DocumentIndexingService:
    return indexing_service


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)