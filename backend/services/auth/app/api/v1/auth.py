"""
Authentication API endpoints
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import structlog

from app.core.database import get_db
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    generate_password_reset_token,
    verify_password_reset_token,
)
from app.core.redis import redis_client
from app.core.config import settings
from app.db.models import User, UserSession, UserLoginAttempt
from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
    TokenRefresh,
    PasswordChange,
    PasswordReset,
    PasswordResetConfirm,
)
from app.api.dependencies import get_current_user, rate_limit_check

logger = structlog.get_logger()

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(rate_limit_check),
) -> Any:
    """
    Register a new user
    
    Args:
        user_data: User registration data
        request: HTTP request
        db: Database session
        
    Returns:
        UserResponse: Created user data
        
    Raises:
        HTTPException: If email or username already exists
    """
    # Check if email already exists
    email_query = select(User).where(User.email == user_data.email.lower())
    email_result = await db.execute(email_query)
    if email_result.scalar_one_or_none():
        logger.warning("Registration attempt with existing email", email=user_data.email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if username already exists
    username_query = select(User).where(User.username == user_data.username.lower())
    username_result = await db.execute(username_query)
    if username_result.scalar_one_or_none():
        logger.warning("Registration attempt with existing username", username=user_data.username)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Hash password
    password_hash = hash_password(user_data.password)
    
    # Create user
    user = User(
        email=user_data.email.lower(),
        username=user_data.username.lower(),
        password_hash=password_hash,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        role=user_data.role,
        specialty=user_data.specialty,
        institution=user_data.institution,
        medical_license=user_data.medical_license,
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    logger.info(
        "User registered successfully",
        user_id=str(user.id),
        email=user.email,
        username=user.username,
        role=user.role
    )
    
    # TODO: Send email verification (implement in future)
    
    return UserResponse.from_orm(user)


@router.post("/login", response_model=TokenResponse)
async def login_user(
    user_credentials: UserLogin,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(rate_limit_check),
) -> Any:
    """
    Authenticate user and return JWT tokens
    
    Args:
        user_credentials: Login credentials
        request: HTTP request
        response: HTTP response
        db: Database session
        
    Returns:
        TokenResponse: JWT tokens
        
    Raises:
        HTTPException: If credentials are invalid
    """
    # Get client information
    client_ip = request.client.host
    if "x-forwarded-for" in request.headers:
        client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
    
    user_agent = request.headers.get("user-agent")
    
    # Find user by email
    user_query = select(User).where(User.email == user_credentials.email.lower())
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()
    
    # Log login attempt
    login_attempt = UserLoginAttempt(
        user_id=user.id if user else None,
        email=user_credentials.email.lower(),
        success=False,  # Will update if successful
        ip_address=client_ip,
        user_agent=user_agent,
    )
    
    # Validate user and password
    if not user or not verify_password(user_credentials.password, user.password_hash):
        login_attempt.failure_reason = "Invalid credentials"
        db.add(login_attempt)
        
        # Increment failed attempts if user exists
        if user:
            user.failed_login_attempts += 1
            
            # Lock account after 5 failed attempts
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.utcnow() + timedelta(minutes=30)
                logger.warning(
                    "Account locked due to failed attempts",
                    user_id=str(user.id),
                    email=user.email,
                    attempts=user.failed_login_attempts
                )
        
        await db.commit()
        
        logger.warning(
            "Failed login attempt",
            email=user_credentials.email,
            ip_address=client_ip,
            reason="Invalid credentials"
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Check if user is active
    if not user.is_active:
        login_attempt.failure_reason = "Account inactive"
        db.add(login_attempt)
        await db.commit()
        
        logger.warning("Inactive user login attempt", user_id=str(user.id), email=user.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive"
        )
    
    # Check if account is locked
    if user.is_locked:
        login_attempt.failure_reason = "Account locked"
        db.add(login_attempt)
        await db.commit()
        
        logger.warning("Locked user login attempt", user_id=str(user.id), email=user.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is locked. Please try again later."
        )
    
    # Generate tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(str(user.id))
    
    # Get token JTIs for session tracking
    access_payload = verify_token(access_token)
    refresh_payload = verify_token(refresh_token)
    
    # Create sessions in database
    access_session = UserSession(
        user_id=user.id,
        token_jti=access_payload["jti"],
        token_type="access",
        expires_at=datetime.fromtimestamp(access_payload["exp"]),
        user_agent=user_agent,
        ip_address=client_ip,
    )
    
    refresh_session = UserSession(
        user_id=user.id,
        token_jti=refresh_payload["jti"],
        token_type="refresh",
        expires_at=datetime.fromtimestamp(refresh_payload["exp"]),
        user_agent=user_agent,
        ip_address=client_ip,
    )
    
    db.add(access_session)
    db.add(refresh_session)
    
    # Update user login info
    user.last_login = datetime.utcnow()
    user.failed_login_attempts = 0  # Reset failed attempts
    user.locked_until = None  # Unlock account
    
    # Mark login attempt as successful
    login_attempt.success = True
    db.add(login_attempt)
    
    await db.commit()
    
    logger.info(
        "User logged in successfully",
        user_id=str(user.id),
        email=user.email,
        ip_address=client_ip
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_data: TokenRefresh,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(rate_limit_check),
) -> Any:
    """
    Refresh access token using refresh token
    
    Args:
        token_data: Refresh token data
        request: HTTP request
        db: Database session
        
    Returns:
        TokenResponse: New JWT tokens
        
    Raises:
        HTTPException: If refresh token is invalid
    """
    # Verify refresh token
    payload = verify_token(token_data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        logger.warning("Invalid refresh token", token_prefix=token_data.refresh_token[:20])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    token_jti = payload.get("jti")
    
    # Check if refresh token is revoked
    revoked_key = f"revoked_token:{token_jti}"
    if await redis_client.exists(revoked_key):
        logger.warning("Refresh token is revoked", jti=token_jti, user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is revoked"
        )
    
    # Check session in database
    session_query = select(UserSession).where(
        UserSession.token_jti == token_jti,
        UserSession.token_type == "refresh",
        UserSession.is_revoked == False
    )
    session_result = await db.execute(session_query)
    session = session_result.scalar_one_or_none()
    
    if not session or not session.is_valid:
        logger.warning("Invalid refresh session", jti=token_jti, user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    # Get user
    user_query = select(User).where(User.id == uuid.UUID(user_id))
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()
    
    if not user or not user.is_active:
        logger.warning("User not found or inactive", user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Generate new tokens
    new_access_token = create_access_token(data={"sub": str(user.id)})
    new_refresh_token = create_refresh_token(str(user.id))
    
    # Get new token JTIs
    access_payload = verify_token(new_access_token)
    refresh_payload = verify_token(new_refresh_token)
    
    # Revoke old refresh token
    session.is_revoked = True
    session.revoked_at = datetime.utcnow()
    
    # Create new sessions
    client_ip = request.client.host
    if "x-forwarded-for" in request.headers:
        client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
    
    user_agent = request.headers.get("user-agent")
    
    new_access_session = UserSession(
        user_id=user.id,
        token_jti=access_payload["jti"],
        token_type="access",
        expires_at=datetime.fromtimestamp(access_payload["exp"]),
        user_agent=user_agent,
        ip_address=client_ip,
    )
    
    new_refresh_session = UserSession(
        user_id=user.id,
        token_jti=refresh_payload["jti"],
        token_type="refresh",
        expires_at=datetime.fromtimestamp(refresh_payload["exp"]),
        user_agent=user_agent,
        ip_address=client_ip,
    )
    
    db.add(new_access_session)
    db.add(new_refresh_session)
    
    await db.commit()
    
    logger.info("Token refreshed successfully", user_id=user_id)
    
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout")
async def logout_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """
    Logout user by revoking current session tokens
    
    Args:
        request: HTTP request
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Dict[str, str]: Success message
    """
    # Get authorization header
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No token provided"
        )
    
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    token_jti = payload.get("jti")
    
    # Revoke session in database
    session_update = (
        update(UserSession)
        .where(UserSession.token_jti == token_jti)
        .values(is_revoked=True, revoked_at=datetime.utcnow())
    )
    await db.execute(session_update)
    
    # Add token to Redis revocation list
    revoked_key = f"revoked_token:{token_jti}"
    token_exp = payload.get("exp")
    if token_exp:
        ttl = max(0, token_exp - int(datetime.utcnow().timestamp()))
        await redis_client.set(revoked_key, "1", expire=ttl)
    
    await db.commit()
    
    logger.info("User logged out successfully", user_id=str(current_user.id))
    
    return {"message": "Successfully logged out"}


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """
    Change user password
    
    Args:
        password_data: Password change data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Dict[str, str]: Success message
        
    Raises:
        HTTPException: If current password is incorrect
    """
    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        logger.warning("Invalid current password", user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Hash new password
    new_password_hash = hash_password(password_data.new_password)
    
    # Update password
    current_user.password_hash = new_password_hash
    current_user.updated_at = datetime.utcnow()
    
    await db.commit()
    
    logger.info("Password changed successfully", user_id=str(current_user.id))
    
    return {"message": "Password changed successfully"}


@router.post("/forgot-password")
async def forgot_password(
    password_reset: PasswordReset,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(rate_limit_check),
) -> Dict[str, str]:
    """
    Request password reset token
    
    Args:
        password_reset: Password reset request data
        db: Database session
        
    Returns:
        Dict[str, str]: Success message
    """
    # Find user by email
    user_query = select(User).where(User.email == password_reset.email.lower())
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()
    
    # Always return success to prevent email enumeration
    if user and user.is_active:
        # Generate password reset token
        reset_token = generate_password_reset_token(str(user.id))
        
        # Store token in Redis with 1 hour expiration
        reset_key = f"password_reset:{user.id}"
        await redis_client.set(reset_key, reset_token, expire=3600)
        
        logger.info("Password reset requested", user_id=str(user.id), email=user.email)
        
        # TODO: Send email with reset token (implement in future)
        # For now, we'll just log the token (REMOVE IN PRODUCTION)
        if settings.DEBUG:
            logger.info("Password reset token (DEBUG ONLY)", token=reset_token)
    
    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/reset-password")
async def reset_password(
    reset_data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(rate_limit_check),
) -> Dict[str, str]:
    """
    Reset password using reset token
    
    Args:
        reset_data: Password reset confirmation data
        db: Database session
        
    Returns:
        Dict[str, str]: Success message
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    # Verify reset token
    user_id = verify_password_reset_token(reset_data.token)
    if not user_id:
        logger.warning("Invalid password reset token", token_prefix=reset_data.token[:20])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Check if token exists in Redis
    reset_key = f"password_reset:{user_id}"
    stored_token = await redis_client.get(reset_key)
    
    if not stored_token or stored_token != reset_data.token:
        logger.warning("Reset token not found in Redis", user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Get user
    user_query = select(User).where(User.id == uuid.UUID(user_id))
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()
    
    if not user or not user.is_active:
        logger.warning("User not found for password reset", user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user"
        )
    
    # Hash new password
    new_password_hash = hash_password(reset_data.new_password)
    
    # Update password
    user.password_hash = new_password_hash
    user.updated_at = datetime.utcnow()
    user.failed_login_attempts = 0  # Reset failed attempts
    user.locked_until = None  # Unlock account
    
    await db.commit()
    
    # Delete reset token from Redis
    await redis_client.delete(reset_key)
    
    logger.info("Password reset successfully", user_id=user_id)
    
    return {"message": "Password reset successfully"}