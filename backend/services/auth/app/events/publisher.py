"""
Event publisher for authentication service
"""

from typing import Optional
import structlog

# Import shared events (will need to add to Python path)
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))

from events import KafkaEventProducer, UserRegisteredEvent, UserLoginEvent, UserLogoutEvent
from app.core.config import settings

logger = structlog.get_logger()


class AuthEventPublisher:
    """
    Event publisher for authentication service
    
    Handles publishing user-related events to Kafka for other services
    to consume and react to authentication events.
    """
    
    def __init__(self):
        self.producer: Optional[KafkaEventProducer] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the Kafka producer"""
        if self._initialized:
            return
        
        try:
            self.producer = KafkaEventProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                topic_prefix=settings.KAFKA_TOPIC_PREFIX
            )
            self.producer.start()
            self._initialized = True
            logger.info("Auth event publisher initialized")
        except Exception as e:
            logger.error("Failed to initialize auth event publisher", error=str(e))
            raise
    
    async def close(self):
        """Close the Kafka producer"""
        if self.producer:
            self.producer.stop()
            self._initialized = False
            logger.info("Auth event publisher closed")
    
    async def publish_user_registered(
        self,
        user_id: str,
        email: str,
        username: str,
        role: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        specialty: Optional[str] = None,
        institution: Optional[str] = None,
        medical_license: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> bool:
        """
        Publish user registration event
        
        Args:
            user_id: User ID
            email: User email
            username: Username
            role: User role
            first_name: First name
            last_name: Last name
            specialty: Medical specialty
            institution: Institution
            medical_license: Medical license
            ip_address: Registration IP
            user_agent: User agent
            correlation_id: Correlation ID
            
        Returns:
            bool: True if event was published successfully
        """
        if not self.producer:
            logger.error("Event publisher not initialized")
            return False
        
        try:
            event = UserRegisteredEvent(
                source_service="auth-service",
                user_id=user_id,
                email=email,
                username=username,
                role=role,
                first_name=first_name,
                last_name=last_name,
                specialty=specialty,
                institution=institution,
                medical_license=medical_license,
                ip_address=ip_address,
                user_agent=user_agent,
                correlation_id=correlation_id
            )
            
            success = await self.producer.publish_event(event)
            
            if success:
                logger.info(
                    "User registration event published",
                    user_id=user_id,
                    email=email,
                    event_id=event.event_id
                )
            
            return success
            
        except Exception as e:
            logger.error(
                "Failed to publish user registration event",
                user_id=user_id,
                email=email,
                error=str(e)
            )
            return False
    
    async def publish_user_login(
        self,
        user_id: str,
        success: bool,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        failure_reason: Optional[str] = None,
        is_suspicious: bool = False,
        location: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> bool:
        """
        Publish user login event
        
        Args:
            user_id: User ID
            success: Whether login was successful
            session_id: Session ID
            ip_address: Login IP
            user_agent: User agent
            failure_reason: Failure reason if unsuccessful
            is_suspicious: Whether login appears suspicious
            location: Estimated location
            correlation_id: Correlation ID
            
        Returns:
            bool: True if event was published successfully
        """
        if not self.producer:
            logger.error("Event publisher not initialized")
            return False
        
        try:
            event = UserLoginEvent(
                source_service="auth-service",
                user_id=user_id,
                success=success,
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent,
                failure_reason=failure_reason,
                is_suspicious=is_suspicious,
                location=location,
                correlation_id=correlation_id
            )
            
            success_published = await self.producer.publish_event(event)
            
            if success_published:
                logger.info(
                    "User login event published",
                    user_id=user_id,
                    success=success,
                    event_id=event.event_id
                )
            
            return success_published
            
        except Exception as e:
            logger.error(
                "Failed to publish user login event",
                user_id=user_id,
                success=success,
                error=str(e)
            )
            return False
    
    async def publish_user_logout(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        logout_type: str = "manual",
        session_duration: Optional[int] = None,
        correlation_id: Optional[str] = None
    ) -> bool:
        """
        Publish user logout event
        
        Args:
            user_id: User ID
            session_id: Session ID
            logout_type: Type of logout
            session_duration: Session duration in seconds
            correlation_id: Correlation ID
            
        Returns:
            bool: True if event was published successfully
        """
        if not self.producer:
            logger.error("Event publisher not initialized")
            return False
        
        try:
            event = UserLogoutEvent(
                source_service="auth-service",
                user_id=user_id,
                session_id=session_id,
                logout_type=logout_type,
                session_duration=session_duration,
                correlation_id=correlation_id
            )
            
            success = await self.producer.publish_event(event)
            
            if success:
                logger.info(
                    "User logout event published",
                    user_id=user_id,
                    logout_type=logout_type,
                    event_id=event.event_id
                )
            
            return success
            
        except Exception as e:
            logger.error(
                "Failed to publish user logout event",
                user_id=user_id,
                logout_type=logout_type,
                error=str(e)
            )
            return False


# Global event publisher instance
auth_event_publisher = AuthEventPublisher()