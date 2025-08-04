"""
Shared events package for Kafka event-driven architecture
"""

from .base import BaseEvent, EventType, UserEvent, DocumentEvent, SearchEvent, NotificationEvent, SystemEvent
from .user_events import UserRegisteredEvent, UserUpdatedEvent, UserDeactivatedEvent, UserLoginEvent, UserLogoutEvent
from .kafka_client import KafkaEventProducer, KafkaEventConsumer, kafka_producer, kafka_consumer

__all__ = [
    # Base classes
    "BaseEvent",
    "EventType",
    "UserEvent",
    "DocumentEvent", 
    "SearchEvent",
    "NotificationEvent",
    "SystemEvent",
    
    # User events
    "UserRegisteredEvent",
    "UserUpdatedEvent", 
    "UserDeactivatedEvent",
    "UserLoginEvent",
    "UserLogoutEvent",
    
    # Kafka clients
    "KafkaEventProducer",
    "KafkaEventConsumer",
    "kafka_producer",
    "kafka_consumer",
]