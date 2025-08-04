import uuid
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis
import structlog
import httpx

logger = structlog.get_logger()
security = HTTPBearer()


class CurrentUser:
    def __init__(self, id: uuid.UUID, email: str, username: str, role: str, is_active: bool):
        self.id = id
        self.email = email
        self.username = username
        self.role = role
        self.is_active = is_active


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Verify JWT token"""
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    token_data: dict = Depends(verify_token),
    redis_client = Depends(get_redis)
) -> CurrentUser:
    """Get current user from token"""
    try:
        user_id = token_data.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Try to get user from cache first
        cached_user = await redis_client.get(f"user:{user_id}")
        if cached_user:
            import json
            user_data = json.loads(cached_user)
            return CurrentUser(
                id=uuid.UUID(user_data["id"]),
                email=user_data["email"],
                username=user_data["username"],
                role=user_data["role"],
                is_active=user_data["is_active"]
            )
        
        # If not in cache, fetch from auth service
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.AUTH_SERVICE_URL}/api/v1/users/me",
                headers={"Authorization": f"Bearer {token_data}"},
                timeout=10.0
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not fetch user information"
                )
            
            user_data = response.json()
            
            # Cache user data for 5 minutes
            import json
            await redis_client.setex(
                f"user:{user_id}",
                300,  # 5 minutes
                json.dumps(user_data)
            )
            
            return CurrentUser(
                id=uuid.UUID(user_data["id"]),
                email=user_data["email"],
                username=user_data["username"],
                role=user_data["role"],
                is_active=user_data["is_active"]
            )
            
    except Exception as e:
        logger.error("Failed to get current user", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate user"
        )


async def get_current_active_user(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def require_role(required_role: str):
    """Dependency to require specific role"""
    def role_checker(current_user: CurrentUser = Depends(get_current_active_user)) -> CurrentUser:
        if current_user.role != required_role and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    return role_checker


async def get_db_session() -> AsyncSession:
    """Get database session dependency"""
    async for session in get_db():
        yield session