"""
User management API endpoints
"""

import uuid
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload
import structlog

from app.core.database import get_db
from app.db.models import User, UserSession, UserLoginAttempt
from app.schemas.user import (
    UserResponse,
    UserProfile,
    UserUpdate,
    UserSessionResponse,
)
from app.api.dependencies import (
    get_current_user,
    require_admin,
    require_role,
    rate_limit_check,
)
from app.db.models import UserRole

logger = structlog.get_logger()

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
) -> UserProfile:
    """
    Get current user's profile
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        UserProfile: User profile data
    """
    logger.info("User profile accessed", user_id=str(current_user.id))
    
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        role=current_user.role,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        specialty=current_user.specialty,
        institution=current_user.institution,
        medical_license=current_user.medical_license,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        last_login=current_user.last_login,
        full_name=current_user.full_name,
        failed_login_attempts=current_user.failed_login_attempts,
        is_locked=current_user.is_locked,
    )


@router.put("/me", response_model=UserProfile)
async def update_current_user_profile(
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfile:
    """
    Update current user's profile
    
    Args:
        user_update: User update data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        UserProfile: Updated user profile
    """
    # Update user fields
    update_data = user_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    current_user.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(current_user)
    
    logger.info(
        "User profile updated",
        user_id=str(current_user.id),
        updated_fields=list(update_data.keys())
    )
    
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        role=current_user.role,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        specialty=current_user.specialty,
        institution=current_user.institution,
        medical_license=current_user.medical_license,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        last_login=current_user.last_login,
        full_name=current_user.full_name,
        failed_login_attempts=current_user.failed_login_attempts,
        is_locked=current_user.is_locked,
    )


@router.get("/me/sessions", response_model=List[UserSessionResponse])
async def get_user_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    active_only: bool = Query(default=True, description="Show only active sessions"),
) -> List[UserSessionResponse]:
    """
    Get current user's sessions
    
    Args:
        db: Database session
        current_user: Current authenticated user
        active_only: Filter to show only active sessions
        
    Returns:
        List[UserSessionResponse]: User sessions
    """
    query = select(UserSession).where(UserSession.user_id == current_user.id)
    
    if active_only:
        query = query.where(
            UserSession.is_revoked == False,
            UserSession.expires_at > datetime.utcnow()
        )
    
    query = query.order_by(UserSession.created_at.desc())
    
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    logger.info(
        "User sessions retrieved",
        user_id=str(current_user.id),
        session_count=len(sessions),
        active_only=active_only
    )
    
    return [
        UserSessionResponse(
            id=session.id,
            token_jti=session.token_jti,
            token_type=session.token_type,
            expires_at=session.expires_at,
            created_at=session.created_at,
            user_agent=session.user_agent,
            ip_address=session.ip_address,
            is_revoked=session.is_revoked,
            is_expired=session.is_expired,
            is_valid=session.is_valid,
        )
        for session in sessions
    ]


@router.delete("/me/sessions/{session_id}")
async def revoke_user_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Revoke a specific user session
    
    Args:
        session_id: Session ID to revoke
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If session not found or doesn't belong to user
    """
    # Find session
    session_query = select(UserSession).where(
        UserSession.id == session_id,
        UserSession.user_id == current_user.id
    )
    session_result = await db.execute(session_query)
    session = session_result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Revoke session
    session.is_revoked = True
    session.revoked_at = datetime.utcnow()
    
    await db.commit()
    
    logger.info(
        "User session revoked",
        user_id=str(current_user.id),
        session_id=str(session_id),
        jti=session.token_jti
    )
    
    return {"message": "Session revoked successfully"}


# Admin endpoints
@router.get("/", response_model=List[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    skip: int = Query(default=0, ge=0, description="Number of users to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Number of users to return"),
    role: Optional[UserRole] = Query(default=None, description="Filter by role"),
    is_active: Optional[bool] = Query(default=None, description="Filter by active status"),
    search: Optional[str] = Query(default=None, description="Search by email or username"),
) -> List[UserResponse]:
    """
    List users (admin only)
    
    Args:
        db: Database session
        admin_user: Admin user
        skip: Number of users to skip
        limit: Number of users to return
        role: Filter by role
        is_active: Filter by active status
        search: Search term
        
    Returns:
        List[UserResponse]: List of users
    """
    query = select(User)
    
    # Apply filters
    if role:
        query = query.where(User.role == role)
    
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    
    if search:
        search_term = f"%{search.lower()}%"
        query = query.where(
            (User.email.ilike(search_term)) |
            (User.username.ilike(search_term)) |
            (User.first_name.ilike(search_term)) |
            (User.last_name.ilike(search_term))
        )
    
    # Apply pagination
    query = query.offset(skip).limit(limit).order_by(User.created_at.desc())
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    logger.info(
        "Users listed by admin",
        admin_id=str(admin_user.id),
        user_count=len(users),
        filters={"role": role, "is_active": is_active, "search": search}
    )
    
    return [UserResponse.from_orm(user) for user in users]


@router.get("/{user_id}", response_model=UserProfile)
async def get_user_by_id(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
) -> UserProfile:
    """
    Get user by ID (admin only)
    
    Args:
        user_id: User ID
        db: Database session
        admin_user: Admin user
        
    Returns:
        UserProfile: User profile
        
    Raises:
        HTTPException: If user not found
    """
    user_query = select(User).where(User.id == user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    logger.info(
        "User profile accessed by admin",
        admin_id=str(admin_user.id),
        target_user_id=str(user_id)
    )
    
    return UserProfile(
        id=user.id,
        email=user.email,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        is_active=user.is_active,
        is_verified=user.is_verified,
        specialty=user.specialty,
        institution=user.institution,
        medical_license=user.medical_license,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login=user.last_login,
        full_name=user.full_name,
        failed_login_attempts=user.failed_login_attempts,
        is_locked=user.is_locked,
    )


@router.put("/{user_id}/status")
async def update_user_status(
    user_id: uuid.UUID,
    is_active: bool,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
) -> dict:
    """
    Update user active status (admin only)
    
    Args:
        user_id: User ID
        is_active: New active status
        db: Database session
        admin_user: Admin user
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If user not found or trying to deactivate self
    """
    if user_id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify your own status"
        )
    
    user_query = select(User).where(User.id == user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = is_active
    user.updated_at = datetime.utcnow()
    
    await db.commit()
    
    logger.info(
        "User status updated by admin",
        admin_id=str(admin_user.id),
        target_user_id=str(user_id),
        new_status=is_active
    )
    
    return {"message": f"User {'activated' if is_active else 'deactivated'} successfully"}


@router.put("/{user_id}/role")
async def update_user_role(
    user_id: uuid.UUID,
    new_role: UserRole,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
) -> dict:
    """
    Update user role (admin only)
    
    Args:
        user_id: User ID
        new_role: New user role
        db: Database session
        admin_user: Admin user
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If user not found or trying to modify self
    """
    if user_id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify your own role"
        )
    
    user_query = select(User).where(User.id == user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    old_role = user.role
    user.role = new_role
    user.updated_at = datetime.utcnow()
    
    await db.commit()
    
    logger.info(
        "User role updated by admin",
        admin_id=str(admin_user.id),
        target_user_id=str(user_id),
        old_role=old_role,
        new_role=new_role
    )
    
    return {"message": f"User role updated to {new_role}"}