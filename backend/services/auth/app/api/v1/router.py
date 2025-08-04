"""
API v1 router configuration
"""

from fastapi import APIRouter

from app.api.v1 import auth, users

# Create API v1 router
api_router = APIRouter()

# Include route modules
api_router.include_router(auth.router)
api_router.include_router(users.router)