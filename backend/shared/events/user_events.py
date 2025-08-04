"""
User-related event schemas
"""

from datetime import datetime
from typing import Optional, Dict, Any

from pydantic import Field

from .base import UserEvent, EventType


class UserRegisteredEvent(UserEvent):
    """Event published when a new user registers"""
    
    event_type: EventType = EventType.USER_REGISTERED
    
    # User details
    email: str = Field(..., description="User email")
    username: str = Field(..., description="Username")
    role: str = Field(..., description="User role")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    
    # Professional information
    specialty: Optional[str] = Field(None, description="Medical specialty")
    institution: Optional[str] = Field(None, description="Institution")
    medical_license: Optional[str] = Field(None, description="Medical license number")
    
    # Registration context
    registration_source: str = Field(default="web", description="Registration source")
    ip_address: Optional[str] = Field(None, description="Registration IP address")
    user_agent: Optional[str] = Field(None, description="User agent")


class UserUpdatedEvent(UserEvent):
    """Event published when user profile is updated"""
    
    event_type: EventType = EventType.USER_UPDATED
    
    # Updated fields
    updated_fields: list[str] = Field(..., description="List of updated field names")
    old_values: Dict[str, Any] = Field(default_factory=dict, description="Previous values")
    new_values: Dict[str, Any] = Field(default_factory=dict, description="New values")
    
    # Update context
    updated_by: str = Field(..., description="ID of user who made the update")
    update_reason: Optional[str] = Field(None, description="Reason for update")


class UserDeactivatedEvent(UserEvent):
    """Event published when a user is deactivated"""
    
    event_type: EventType = EventType.USER_DEACTIVATED
    
    # Deactivation details
    deactivated_by: str = Field(..., description="ID of user who deactivated the account")
    deactivation_reason: Optional[str] = Field(None, description="Reason for deactivation")
    is_permanent: bool = Field(default=False, description="Whether deactivation is permanent")


class UserLoginEvent(UserEvent):
    """Event published when user logs in"""
    
    event_type: EventType = EventType.USER_LOGIN
    
    # Login details
    login_method: str = Field(default="password", description="Login method used")
    success: bool = Field(..., description="Whether login was successful")
    
    # Session information
    session_id: Optional[str] = Field(None, description="Session ID")
    ip_address: Optional[str] = Field(None, description="Login IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    
    # Failure information (if applicable)
    failure_reason: Optional[str] = Field(None, description="Reason for login failure")
    
    # Security context
    is_suspicious: bool = Field(default=False, description="Whether login appears suspicious")
    location: Optional[str] = Field(None, description="Estimated login location")


class UserLogoutEvent(UserEvent):
    """Event published when user logs out"""
    
    event_type: EventType = EventType.USER_LOGOUT
    
    # Logout details
    logout_type: str = Field(default="manual", description="Type of logout (manual, timeout, forced)")
    session_id: Optional[str] = Field(None, description="Session ID that was terminated")
    session_duration: Optional[int] = Field(None, description="Session duration in seconds")