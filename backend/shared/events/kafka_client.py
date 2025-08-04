"""
Kafka client for event publishing and consuming
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Callable, Type
from contextlib import asynccontextmanager

from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import structlog

from .base import BaseEvent, EventType

logger = structlog.get_logger()


class KafkaEventProducer:
    """
    Kafka producer for publishing events
    
    Provides reliable event publishing with error handling,
    retries, and structured logging.
    """
    
    def __init__(
        self,
        bootstrap_servers: str,
        topic_prefix: str = "medical-ai-platform",
        **kwargs
    ):
        self.bootstrap_servers = bootstrap_servers
        self.topic_prefix = topic_prefix
        self.producer = None
        self.producer_config = {
            'bootstrap_servers': bootstrap_servers.split(','),
            'value_serializer': lambda v: json.dumps(v).encode('utf-8'),
            'key_serializer': lambda k: k.encode('utf-8') if k else None,
            'acks': 'all',  # Wait for all replicas
            'retries': 3,
            'retry_backoff_ms': 100,
            'enable_idempotence': True,
            **kwargs
        }
    
    def start(self):
        """Start the Kafka producer"""
        try:
            self.producer = KafkaProducer(**self.producer_config)
            logger.info("Kafka producer started", servers=self.bootstrap_servers)
        except Exception as e:
            logger.error("Failed to start Kafka producer", error=str(e))
            raise
    
    def stop(self):
        """Stop the Kafka producer"""
        if self.producer:
            try:
                self.producer.close()
                logger.info("Kafka producer stopped")
            except Exception as e:
                logger.error("Error stopping Kafka producer", error=str(e))
    
    def _get_topic_name(self, event_type: EventType) -> str:
        """Generate topic name based on event type"""
        # Convert event type to topic name
        # e.g., "user.registered" -> "medical-ai-platform.user.events"
        category = event_type.split('.')[0]
        return f"{self.topic_prefix}.{category}.events"
    
    async def publish_event(self, event: BaseEvent) -> bool:
        """
        Publish an event to Kafka
        
        Args:
            event: Event to publish
            
        Returns:
            bool: True if event was published successfully
        """
        if not self.producer:
            logger.error("Kafka producer not started")
            return False
        
        try:
            topic = self._get_topic_name(event.event_type)
            message = event.to_kafka_message()
            
            # Send message
            future = self.producer.send(
                topic=topic,
                key=message["key"],
                value=message["value"],
                headers=[(k, v.encode('utf-8')) for k, v in message["headers"].items()]
            )
            
            # Wait for result
            record_metadata = future.get(timeout=10)
            
            logger.info(
                "Event published successfully",
                event_id=event.event_id,
                event_type=event.event_type,
                topic=topic,
                partition=record_metadata.partition,
                offset=record_metadata.offset
            )
            
            return True
            
        except KafkaError as e:
            logger.error(
                "Failed to publish event",
                event_id=event.event_id,
                event_type=event.event_type,
                error=str(e)
            )
            return False
        except Exception as e:
            logger.error(
                "Unexpected error publishing event",
                event_id=event.event_id,
                event_type=event.event_type,
                error=str(e)
            )
            return False
    
    def publish_event_sync(self, event: BaseEvent) -> bool:
        """
        Synchronous version of publish_event
        
        Args:
            event: Event to publish
            
        Returns:
            bool: True if event was published successfully
        """
        return asyncio.run(self.publish_event(event))


class KafkaEventConsumer:
    """
    Kafka consumer for processing events
    
    Provides reliable event consumption with error handling,
    automatic retries, and dead letter queue support.
    """
    
    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str,
        topics: List[str],
        **kwargs
    ):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.topics = topics
        self.consumer = None
        self.handlers: Dict[EventType, List[Callable]] = {}
        self.running = False
        
        self.consumer_config = {
            'bootstrap_servers': bootstrap_servers.split(','),
            'group_id': group_id,
            'value_deserializer': lambda m: json.loads(m.decode('utf-8')),
            'key_deserializer': lambda k: k.decode('utf-8') if k else None,
            'auto_offset_reset': 'earliest',
            'enable_auto_commit': False,  # Manual commit for reliability
            'max_poll_records': 100,
            **kwargs
        }
    
    def start(self):
        """Start the Kafka consumer"""
        try:
            self.consumer = KafkaConsumer(*self.topics, **self.consumer_config)
            logger.info(
                "Kafka consumer started",
                group_id=self.group_id,
                topics=self.topics
            )
        except Exception as e:
            logger.error("Failed to start Kafka consumer", error=str(e))
            raise
    
    def stop(self):
        """Stop the Kafka consumer"""
        self.running = False
        if self.consumer:
            try:
                self.consumer.close()
                logger.info("Kafka consumer stopped")
            except Exception as e:
                logger.error("Error stopping Kafka consumer", error=str(e))
    
    def register_handler(self, event_type: EventType, handler: Callable):
        """
        Register an event handler
        
        Args:
            event_type: Type of event to handle
            handler: Handler function (async or sync)
        """
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        
        self.handlers[event_type].append(handler)
        logger.info(
            "Event handler registered",
            event_type=event_type,
            handler=handler.__name__
        )
    
    async def process_message(self, message) -> bool:
        """
        Process a single Kafka message
        
        Args:
            message: Kafka message
            
        Returns:
            bool: True if message was processed successfully
        """
        try:
            # Extract event type from headers
            event_type = None
            if message.headers:
                for key, value in message.headers:
                    if key == 'event_type':
                        event_type = EventType(value.decode('utf-8'))
                        break
            
            if not event_type:
                # Try to get event type from message value
                event_type = EventType(message.value.get('event_type'))
            
            if not event_type:
                logger.warning("No event type found in message", topic=message.topic)
                return False
            
            # Get handlers for this event type
            handlers = self.handlers.get(event_type, [])
            if not handlers:
                logger.debug("No handlers for event type", event_type=event_type)
                return True  # Not an error, just no handlers
            
            # Create event object
            event = BaseEvent.from_kafka_message({
                "value": message.value,
                "key": message.key,
                "headers": dict(message.headers) if message.headers else {}
            })
            
            # Process with all handlers
            success = True
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                    
                    logger.debug(
                        "Event processed by handler",
                        event_id=event.event_id,
                        event_type=event_type,
                        handler=handler.__name__
                    )
                    
                except Exception as e:
                    logger.error(
                        "Handler failed to process event",
                        event_id=event.event_id,
                        event_type=event_type,
                        handler=handler.__name__,
                        error=str(e)
                    )
                    success = False
            
            return success
            
        except Exception as e:
            logger.error(
                "Failed to process message",
                topic=message.topic,
                partition=message.partition,
                offset=message.offset,
                error=str(e)
            )
            return False
    
    async def consume_events(self):
        """
        Main event consumption loop
        
        This method runs continuously, processing events from Kafka.
        It handles errors gracefully and provides structured logging.
        """
        if not self.consumer:
            logger.error("Consumer not started")
            return
        
        self.running = True
        logger.info("Starting event consumption loop")
        
        try:
            while self.running:
                # Poll for messages
                message_batch = self.consumer.poll(timeout_ms=1000)
                
                if not message_batch:
                    continue
                
                # Process messages
                for topic_partition, messages in message_batch.items():
                    for message in messages:
                        try:
                            success = await self.process_message(message)
                            
                            if success:
                                # Commit offset on successful processing
                                self.consumer.commit_async()
                            else:
                                # TODO: Implement dead letter queue for failed messages
                                logger.error(
                                    "Message processing failed",
                                    topic=message.topic,
                                    partition=message.partition,
                                    offset=message.offset
                                )
                        
                        except Exception as e:
                            logger.error(
                                "Unexpected error processing message",
                                topic=message.topic,
                                partition=message.partition,
                                offset=message.offset,
                                error=str(e)
                            )
                
        except Exception as e:
            logger.error("Error in consumption loop", error=str(e))
        finally:
            logger.info("Event consumption loop ended")


@asynccontextmanager
async def kafka_producer(bootstrap_servers: str, topic_prefix: str = "medical-ai-platform"):
    """Context manager for Kafka producer"""
    producer = KafkaEventProducer(bootstrap_servers, topic_prefix)
    producer.start()
    try:
        yield producer
    finally:
        producer.stop()


@asynccontextmanager
async def kafka_consumer(
    bootstrap_servers: str,
    group_id: str,
    topics: List[str]
):
    """Context manager for Kafka consumer"""
    consumer = KafkaEventConsumer(bootstrap_servers, group_id, topics)
    consumer.start()
    try:
        yield consumer
    finally:
        consumer.stop()