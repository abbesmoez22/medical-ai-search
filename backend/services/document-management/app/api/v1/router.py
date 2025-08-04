from fastapi import APIRouter
from app.api.v1.documents import router as documents_router

router = APIRouter(prefix="/api/v1")

# Include all v1 routers
router.include_router(documents_router)