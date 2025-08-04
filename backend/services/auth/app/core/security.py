"""
Security utilities for JWT tokens, password hashing, and authentication
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
import structlog

from app.core.config import settings

logger = structlog.get_logger()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token
    
    Args:
        data: Token payload data
        expires_delta: Custom expiration time
        
    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Add standard JWT claims
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": str(uuid.uuid4()),  # JWT ID for token revocation
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    logger.info(
        "Access token created",
        user_id=data.get("sub"),
        expires_at=expire.isoformat(),
        jti=to_encode["jti"]
    )
    
    return encoded_jwt


def create_refresh_token(user_id: str) -> str:
    """
    Create JWT refresh token
    
    Args:
        user_id: User identifier
        
    Returns:
        str: Encoded JWT refresh token
    """
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": str(uuid.uuid4()),
    }
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    logger.info(
        "Refresh token created",
        user_id=user_id,
        expires_at=expire.isoformat(),
        jti=to_encode["jti"]
    )
    
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode JWT token
    
    Args:
        token: JWT token to verify
        
    Returns:
        Dict[str, Any] | None: Token payload or None if invalid
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        # Check if token is expired
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            logger.warning("Token expired", jti=payload.get("jti"))
            return None
        
        return payload
    
    except JWTError as e:
        logger.warning("Token verification failed", error=str(e))
        return None


def hash_password(password: str) -> str:
    """
    Hash password using bcrypt
    
    Args:
        password: Plain text password
        
    Returns:
        str: Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hash
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database
        
    Returns:
        bool: True if password matches
    """
    return pwd_context.verify(plain_password, hashed_password)


def generate_password_reset_token(user_id: str) -> str:
    """
    Generate password reset token
    
    Args:
        user_id: User identifier
        
    Returns:
        str: Password reset token
    """
    expire = datetime.utcnow() + timedelta(hours=1)  # 1 hour expiration
    
    to_encode = {
        "sub": user_id,
        "type": "password_reset",
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": str(uuid.uuid4()),
    }
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_password_reset_token(token: str) -> Optional[str]:
    """
    Verify password reset token and return user ID
    
    Args:
        token: Password reset token
        
    Returns:
        str | None: User ID if token is valid
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        if payload.get("type") != "password_reset":
            return None
        
        # Check if token is expired
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            return None
        
        return payload.get("sub")
    
    except JWTError:
        return None