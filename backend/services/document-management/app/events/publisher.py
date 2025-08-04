import json
import uuid
from datetime import datetime
from typing import Dict, Any
from kafka import KafkaProducer
from kafka.errors import KafkaError
import structlog
from app.core.config import settings

logger = structlog.get_logger()


class DocumentEventPublisher:
    def __init__(self):
        self.producer = None
        self.topic_prefix = settings.KAFKA_TOPIC_PREFIX
        
    async def initialize(self):
        """Initialize Kafka producer"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda x: json.dumps(x).encode('utf-8'),
                key_serializer=lambda x: str(x).encode('utf-8') if x else None,
                acks='all',
                retries=3,
                max_in_flight_requests_per_connection=1
            )
            logger.info("Kafka producer initialized", servers=settings.KAFKA_BOOTSTRAP_SERVERS)
        except Exception as e:
            logger.error("Failed to initialize Kafka producer", error=str(e))
            raise
    
    async def close(self):
        """Close Kafka producer"""
        if self.producer:
            self.producer.close()
            logger.info("Kafka producer closed")
    
    async def publish_document_event(self, event_type: str, data: Dict[str, Any], 
                                   correlation_id: str = None, user_id: str = None) -> bool:
        """Publish document-related event"""
        if not self.producer:
            logger.error("Kafka producer not initialized")
            return False
        
        try:
            event = {
                "event_id": str(uuid.uuid4()),
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "source_service": "document-management",
                "correlation_id": correlation_id or str(uuid.uuid4()),
                "user_id": user_id,
                "data": data
            }
            
            topic = f"{self.topic_prefix}.document.events"
            key = data.get('document_id') if data else None
            
            future = self.producer.send(topic, value=event, key=key)
            record_metadata = future.get(timeout=10)
            
            logger.info(
                "Document event published",
                event_type=event_type,
                topic=topic,
                partition=record_metadata.partition,
                offset=record_metadata.offset
            )
            return True
            
        except KafkaError as e:
            logger.error("Failed to publish document event", error=str(e), event_type=event_type)
            return False
        except Exception as e:
            logger.error("Unexpected error publishing event", error=str(e), event_type=event_type)
            return False


# Global instance
document_event_publisher = DocumentEventPublisher()


async def get_event_publisher() -> DocumentEventPublisher:
    """Dependency to get event publisher"""
    return document_event_publisher


async def publish_document_uploaded(document_id: str, s3_bucket: str, s3_key: str, 
                                  mime_type: str, uploaded_by: str, correlation_id: str = None):
    """Publish document uploaded event"""
    await document_event_publisher.publish_document_event(
        "document.uploaded",
        {
            "document_id": document_id,
            "s3_bucket": s3_bucket,
            "s3_key": s3_key,
            "mime_type": mime_type,
            "uploaded_by": uploaded_by
        },
        correlation_id=correlation_id,
        user_id=uploaded_by
    )


async def publish_document_updated(document_id: str, updated_fields: Dict[str, Any], 
                                 updated_by: str, correlation_id: str = None):
    """Publish document updated event"""
    await document_event_publisher.publish_document_event(
        "document.updated",
        {
            "document_id": document_id,
            "updated_fields": updated_fields,
            "updated_by": updated_by
        },
        correlation_id=correlation_id,
        user_id=updated_by
    )


async def publish_document_deleted(document_id: str, deleted_by: str, correlation_id: str = None):
    """Publish document deleted event"""
    await document_event_publisher.publish_document_event(
        "document.deleted",
        {
            "document_id": document_id,
            "deleted_by": deleted_by
        },
        correlation_id=correlation_id,
        user_id=deleted_by
    )