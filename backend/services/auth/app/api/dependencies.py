"""
FastAPI dependencies for authentication and authorization
"""

import uuid
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.core.database import get_db
from app.core.security import verify_token
from app.core.redis import redis_client
from app.db.models import User, UserSession, UserRole
from app.schemas.user import UserResponse

logger = structlog.get_logger()

# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    request: Request = None
) -> User:
    """
    Get current authenticated user from JWT token
    
    Args:
        credentials: HTTP Bearer credentials
        db: Database session
        request: HTTP request object
        
    Returns:
        User: Current authenticated user
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Verify JWT token
        payload = verify_token(credentials.credentials)
        if payload is None:
            logger.warning("Invalid JWT token", token_prefix=credentials.credentials[:20])
            raise credentials_exception
        
        # Extract user ID and token JTI
        user_id: str = payload.get("sub")
        token_jti: str = payload.get("jti")
        
        if user_id is None or token_jti is None:
            logger.warning("Missing user_id or jti in token", payload=payload)
            raise credentials_exception
        
        # Check if token is revoked in Redis
        revoked_key = f"revoked_token:{token_jti}"
        if await redis_client.exists(revoked_key):
            logger.warning("Token is revoked", jti=token_jti, user_id=user_id)
            raise credentials_exception
        
        # Check session in database
        session_query = select(UserSession).where(
            UserSession.token_jti == token_jti,
            UserSession.is_revoked == False
        )
        session_result = await db.execute(session_query)
        session = session_result.scalar_one_or_none()
        
        if not session or not session.is_valid:
            logger.warning("Invalid or expired session", jti=token_jti, user_id=user_id)
            raise credentials_exception
        
        # Get user from database
        user_query = select(User).where(User.id == uuid.UUID(user_id))
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if user is None:
            logger.warning("User not found", user_id=user_id)
            raise credentials_exception
        
        # Check if user is active
        if not user.is_active:
            logger.warning("Inactive user attempted access", user_id=user_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user",
            )
        
        # Check if account is locked
        if user.is_locked:
            logger.warning("Locked user attempted access", user_id=user_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is locked",
            )
        
        # Update last login if this is a new session
        if request and session.created_at > user.last_login if user.last_login else True:
            user.last_login = datetime.utcnow()
            await db.commit()
        
        logger.info("User authenticated successfully", user_id=user_id, email=user.email)
        return user
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Authentication error", error=str(e))
        raise credentials_exception


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user (alias for get_current_user with explicit active check)
    """
    return current_user


def require_role(required_role: UserRole):
    """
    Dependency factory for role-based access control
    
    Args:
        required_role: Required user role
        
    Returns:
        Dependency function
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        # Define role hierarchy
        role_hierarchy = {
            UserRole.USER: 0,
            UserRole.STUDENT: 1,
            UserRole.RESEARCHER: 2,
            UserRole.DOCTOR: 3,
            UserRole.ADMIN: 4,
        }
        
        user_level = role_hierarchy.get(current_user.role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        if user_level < required_level:
            logger.warning(
                "Insufficient permissions",
                user_id=str(current_user.id),
                user_role=current_user.role,
                required_role=required_role
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        return current_user
    
    return role_checker


def require_admin(current_user: User = Depends(require_role(UserRole.ADMIN))) -> User:
    """Require admin role"""
    return current_user


def require_doctor(current_user: User = Depends(require_role(UserRole.DOCTOR))) -> User:
    """Require doctor role or higher"""
    return current_user


def require_researcher(current_user: User = Depends(require_role(UserRole.RESEARCHER))) -> User:
    """Require researcher role or higher"""
    return current_user


async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None
    Useful for endpoints that work for both authenticated and anonymous users
    """
    try:
        # Try to get authorization header
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return None
        
        token = authorization.split(" ")[1]
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        
        return await get_current_user(credentials, db, request)
    
    except HTTPException:
        return None
    except Exception as e:
        logger.debug("Optional user authentication failed", error=str(e))
        return None


async def rate_limit_check(
    request: Request,
    window_seconds: int = 60,
    max_requests: int = 100
) -> bool:
    """
    Rate limiting dependency using Redis
    
    Args:
        request: HTTP request
        window_seconds: Time window in seconds
        max_requests: Maximum requests per window
        
    Returns:
        bool: True if request is allowed
        
    Raises:
        HTTPException: If rate limit exceeded
    """
    # Get client IP
    client_ip = request.client.host
    if "x-forwarded-for" in request.headers:
        client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
    
    # Create rate limit key
    rate_limit_key = f"rate_limit:{client_ip}:{request.url.path}"
    
    try:
        # Get current count
        current_requests = await redis_client.get(rate_limit_key)
        
        if current_requests is None:
            # First request in window
            await redis_client.set(rate_limit_key, "1", expire=window_seconds)
            return True
        
        current_count = int(current_requests)
        
        if current_count >= max_requests:
            logger.warning(
                "Rate limit exceeded",
                client_ip=client_ip,
                path=request.url.path,
                count=current_count,
                limit=max_requests
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )
        
        # Increment counter
        await redis_client.increment(rate_limit_key)
        return True
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Rate limiting error", error=str(e))
        # Allow request if rate limiting fails
        return True