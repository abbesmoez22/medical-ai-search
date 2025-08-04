"""
Base event schemas and utilities for Kafka event-driven architecture
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Type, TypeVar
from enum import Enum

from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger()

T = TypeVar('T', bound='BaseEvent')


class EventType(str, Enum):
    """Event types for the medical AI platform"""
    
    # User events
    USER_REGISTERED = "user.registered"
    USER_UPDATED = "user.updated"
    USER_DEACTIVATED = "user.deactivated"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    
    # Document events
    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_PROCESSED = "document.processed"
    DOCUMENT_INDEXED = "document.indexed"
    DOCUMENT_FAILED = "document.failed"
    DOCUMENT_DELETED = "document.deleted"
    
    # Search events
    SEARCH_PERFORMED = "search.performed"
    SEARCH_CLICKED = "search.clicked"
    
    # Notification events
    NOTIFICATION_REQUESTED = "notification.requested"
    NOTIFICATION_SENT = "notification.sent"
    NOTIFICATION_FAILED = "notification.failed"
    
    # System events
    SYSTEM_HEALTH_CHECK = "system.health_check"
    SYSTEM_ERROR = "system.error"


class BaseEvent(BaseModel):
    """
    Base event schema for all Kafka events
    
    This provides a consistent structure for all events in the system
    and includes common fields for tracing, correlation, and metadata.
    """
    
    # Event identification
    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this event"
    )
    event_type: EventType = Field(..., description="Type of event")
    
    # Timing
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the event occurred"
    )
    
    # Source tracking
    source_service: str = Field(..., description="Service that generated the event")
    source_version: str = Field(default="1.0.0", description="Version of the source service")
    
    # Correlation and tracing
    correlation_id: Optional[str] = Field(
        default=None,
        description="Correlation ID for tracking related events"
    )
    trace_id: Optional[str] = Field(
        default=None,
        description="Distributed tracing ID"
    )
    span_id: Optional[str] = Field(
        default=None,
        description="Span ID for distributed tracing"
    )
    
    # User context
    user_id: Optional[str] = Field(
        default=None,
        description="ID of the user associated with this event"
    )
    
    # Event metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional event metadata"
    )
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
        }
    
    def to_kafka_message(self) -> Dict[str, Any]:
        """Convert event to Kafka message format"""
        return {
            "key": self.event_id,
            "value": self.dict(),
            "headers": {
                "event_type": self.event_type,
                "source_service": self.source_service,
                "correlation_id": self.correlation_id or "",
                "user_id": self.user_id or "",
            }
        }
    
    @classmethod
    def from_kafka_message(cls: Type[T], message: Dict[str, Any]) -> T:
        """Create event from Kafka message"""
        return cls(**message.get("value", {}))
    
    def with_correlation(self, correlation_id: str) -> 'BaseEvent':
        """Create a copy of the event with a correlation ID"""
        event_dict = self.dict()
        event_dict["correlation_id"] = correlation_id
        return self.__class__(**event_dict)
    
    def with_trace(self, trace_id: str, span_id: Optional[str] = None) -> 'BaseEvent':
        """Create a copy of the event with tracing information"""
        event_dict = self.dict()
        event_dict["trace_id"] = trace_id
        if span_id:
            event_dict["span_id"] = span_id
        return self.__class__(**event_dict)


class UserEvent(BaseEvent):
    """Base class for user-related events"""
    user_id: str = Field(..., description="User ID (required for user events)")


class DocumentEvent(BaseEvent):
    """Base class for document-related events"""
    document_id: str = Field(..., description="Document ID")
    document_title: Optional[str] = Field(None, description="Document title")


class SearchEvent(BaseEvent):
    """Base class for search-related events"""
    query: str = Field(..., description="Search query")
    query_type: str = Field(default="text", description="Type of search query")


class NotificationEvent(BaseEvent):
    """Base class for notification events"""
    recipient_id: str = Field(..., description="Notification recipient user ID")
    notification_type: str = Field(..., description="Type of notification")


class SystemEvent(BaseEvent):
    """Base class for system events"""
    component: str = Field(..., description="System component")
    severity: str = Field(default="info", description="Event severity level")