"""
Pydantic schemas for user-related API requests and responses
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, validator

from app.db.models import UserRole


# Base schemas
class UserBase(BaseModel):
    """Base user schema with common fields"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    specialty: Optional[str] = Field(None, max_length=100)
    institution: Optional[str] = Field(None, max_length=255)
    medical_license: Optional[str] = Field(None, max_length=100)


# Request schemas
class UserCreate(UserBase):
    """Schema for user registration"""
    password: str = Field(..., min_length=8, max_length=100)
    role: UserRole = UserRole.USER
    
    @validator("password")
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        # Check for at least one uppercase, lowercase, digit, and special character
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain at least one special character")
        
        return v
    
    @validator("username")
    def validate_username(cls, v):
        """Validate username format"""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username can only contain letters, numbers, hyphens, and underscores")
        return v.lower()


class UserUpdate(BaseModel):
    """Schema for user profile updates"""
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    specialty: Optional[str] = Field(None, max_length=100)
    institution: Optional[str] = Field(None, max_length=255)
    medical_license: Optional[str] = Field(None, max_length=100)


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str = Field(..., min_length=1)


class PasswordChange(BaseModel):
    """Schema for password change"""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)
    
    @validator("new_password")
    def validate_new_password(cls, v):
        """Validate new password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        # Check for at least one uppercase, lowercase, digit, and special character
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain at least one special character")
        
        return v


class PasswordReset(BaseModel):
    """Schema for password reset request"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation"""
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)
    
    @validator("new_password")
    def validate_new_password(cls, v):
        """Validate new password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        # Check for at least one uppercase, lowercase, digit, and special character
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain at least one special character")
        
        return v


# Response schemas
class UserResponse(UserBase):
    """Schema for user response"""
    id: uuid.UUID
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserProfile(UserResponse):
    """Extended user profile with additional information"""
    full_name: str
    failed_login_attempts: int
    is_locked: bool


class TokenResponse(BaseModel):
    """Schema for authentication token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenRefresh(BaseModel):
    """Schema for token refresh request"""
    refresh_token: str = Field(..., min_length=1)


class UserSessionResponse(BaseModel):
    """Schema for user session information"""
    id: uuid.UUID
    token_jti: str
    token_type: str
    expires_at: datetime
    created_at: datetime
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    is_revoked: bool
    is_expired: bool
    is_valid: bool
    
    class Config:
        from_attributes = True