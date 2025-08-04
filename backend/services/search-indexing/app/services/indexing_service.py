import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.core.config import settings
from app.core.database import async_session_factory
from app.core.elasticsearch import es_client
from app.db.models import IndexingJob, IndexedDocument, IndexingMetrics

logger = structlog.get_logger()


class DocumentIndexingService:
    """Service for indexing documents in Elasticsearch"""
    
    def __init__(self):
        self.kafka_consumer = None
        self.kafka_producer = None
        self.consumer_task = None
        self.running = False
        self.batch_size = settings.BATCH_SIZE
        self.index_name = f"{settings.ELASTICSEARCH_INDEX_PREFIX}-documents"
        
    async def initialize(self):
        """Initialize the indexing service"""
        try:
            # Initialize Kafka producer
            self.kafka_producer = KafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda x: json.dumps(x).encode('utf-8'),
                key_serializer=lambda x: str(x).encode('utf-8') if x else None,
                acks='all',
                retries=3,
                max_in_flight_requests_per_connection=1
            )
            
            logger.info("Document indexing service initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize document indexing service", error=str(e))
            raise
    
    async def close(self):
        """Close the indexing service"""
        if self.kafka_producer:
            self.kafka_producer.close()
    
    async def start_kafka_consumer(self):
        """Start Kafka consumer for processing events"""
        try:
            self.kafka_consumer = KafkaConsumer(
                f"{settings.KAFKA_TOPIC_PREFIX}.processing.events",
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id="search-indexing-service",
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                key_deserializer=lambda x: x.decode('utf-8') if x else None,
                auto_offset_reset='latest',
                enable_auto_commit=True
            )
            
            self.running = True
            self.consumer_task = asyncio.create_task(self._consume_events())
            logger.info("Kafka consumer started for document indexing")
            
        except Exception as e:
            logger.error("Failed to start Kafka consumer", error=str(e))
            raise
    
    async def stop_kafka_consumer(self):
        """Stop Kafka consumer"""
        self.running = False
        if self.consumer_task:
            self.consumer_task.cancel()
            try:
                await self.consumer_task
            except asyncio.CancelledError:
                pass
        
        if self.kafka_consumer:
            self.kafka_consumer.close()
    
    async def _consume_events(self):
        """Consume and process Kafka events"""
        while self.running:
            try:
                message_batch = self.kafka_consumer.poll(timeout_ms=1000)
                
                for topic_partition, messages in message_batch.items():
                    for message in messages:
                        try:
                            await self._handle_processing_event(message.value)
                        except Exception as e:
                            logger.error("Failed to handle processing event", 
                                       event=message.value, error=str(e))
                
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
                
            except Exception as e:
                logger.error("Error in Kafka consumer loop", error=str(e))
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _handle_processing_event(self, event: Dict[str, Any]):
        """Handle document processing events"""
        event_type = event.get('event_type')
        
        if event_type == 'document.processing_completed':
            await self._process_completed_document(event)
        elif event_type == 'document.processing_failed':
            logger.info("Document processing failed, skipping indexing", 
                       document_id=event.get('document_id'))
        elif event_type == 'document.deleted':
            await self._process_deleted_document(event)
    
    async def _process_completed_document(self, event: Dict[str, Any]):
        """Process a completed document for indexing"""
        document_id = event.get('document_id')
        
        if not document_id:
            logger.error("No document_id in processing event", event=event)
            return
        
        try:
            # Create indexing job
            job_id = await self._create_indexing_job(
                document_id=document_id,
                job_type='index',
                document_data=event.get('data', {})
            )
            
            # Process the indexing job
            await self._process_indexing_job(job_id)
            
        except Exception as e:
            logger.error("Failed to process completed document", 
                        document_id=document_id, error=str(e))
    
    async def _process_deleted_document(self, event: Dict[str, Any]):
        """Process a deleted document for removal from index"""
        document_id = event.get('document_id')
        
        if not document_id:
            logger.error("No document_id in deletion event", event=event)
            return
        
        try:
            # Create deletion job
            job_id = await self._create_indexing_job(
                document_id=document_id,
                job_type='delete'
            )
            
            # Process the deletion job
            await self._process_indexing_job(job_id)
            
        except Exception as e:
            logger.error("Failed to process deleted document", 
                        document_id=document_id, error=str(e))
    
    async def _create_indexing_job(self, document_id: str, job_type: str, 
                                  document_data: Optional[Dict[str, Any]] = None) -> uuid.UUID:
        """Create a new indexing job"""
        async with async_session_factory() as db:
            job = IndexingJob(
                document_id=uuid.UUID(document_id),
                job_type=job_type,
                elasticsearch_index=self.index_name,
                document_data=document_data,
                status='pending'
            )
            
            db.add(job)
            await db.commit()
            await db.refresh(job)
            
            logger.info("Created indexing job", 
                       job_id=str(job.id), document_id=document_id, job_type=job_type)
            
            return job.id
    
    async def _process_indexing_job(self, job_id: uuid.UUID):
        """Process an indexing job"""
        start_time = time.time()
        
        async with async_session_factory() as db:
            # Get the job
            result = await db.execute(
                select(IndexingJob).where(IndexingJob.id == job_id)
            )
            job = result.scalar_one_or_none()
            
            if not job:
                logger.error("Indexing job not found", job_id=str(job_id))
                return
            
            try:
                # Update job status
                job.status = 'processing'
                job.started_at = datetime.utcnow()
                await db.commit()
                
                # Process based on job type
                if job.job_type == 'index':
                    await self._index_document(job)
                elif job.job_type == 'delete':
                    await self._delete_document(job)
                elif job.job_type == 'update':
                    await self._update_document(job)
                
                # Mark job as completed
                job.status = 'completed'
                job.completed_at = datetime.utcnow()
                job.processing_time_seconds = time.time() - start_time
                
                await db.commit()
                
                logger.info("Indexing job completed", 
                           job_id=str(job_id), job_type=job.job_type,
                           processing_time=job.processing_time_seconds)
                
            except Exception as e:
                # Handle job failure
                await self._handle_job_failure(db, job, str(e))
                logger.error("Indexing job failed", 
                           job_id=str(job_id), error=str(e))
    
    async def _index_document(self, job: IndexingJob):
        """Index a document in Elasticsearch"""
        document_data = job.document_data or {}
        
        # Prepare document for indexing
        doc = {
            "document_id": str(job.document_id),
            "title": document_data.get('title', ''),
            "content": document_data.get('extracted_text', ''),
            "authors": document_data.get('authors', ''),
            "abstract": document_data.get('abstract', ''),
            "keywords": document_data.get('keywords', []),
            "medical_entities": document_data.get('medical_entities', {}),
            "document_type": document_data.get('document_type', 'pdf'),
            "publication_date": document_data.get('publication_date'),
            "language": document_data.get('language', 'en'),
            "file_size": document_data.get('file_size'),
            "page_count": document_data.get('page_count'),
            "quality_score": document_data.get('quality_score'),
            "medical_relevance_score": document_data.get('medical_relevance_score'),
            "created_at": document_data.get('created_at'),
            "updated_at": document_data.get('updated_at'),
            "indexed_at": datetime.utcnow().isoformat()
        }
        
        # Index in Elasticsearch
        await es_client.index(
            index=self.index_name,
            id=str(job.document_id),
            body=doc
        )
        
        # Update indexed document record
        await self._update_indexed_document_record(job, doc)
    
    async def _delete_document(self, job: IndexingJob):
        """Delete a document from Elasticsearch"""
        try:
            await es_client.delete(
                index=self.index_name,
                id=str(job.document_id)
            )
        except Exception as e:
            # Document might not exist, which is fine
            if "not_found" not in str(e).lower():
                raise
        
        # Remove from indexed documents
        async with async_session_factory() as db:
            await db.execute(
                select(IndexedDocument).where(
                    IndexedDocument.document_id == job.document_id
                ).delete()
            )
            await db.commit()
    
    async def _update_document(self, job: IndexingJob):
        """Update a document in Elasticsearch"""
        # For now, treat update as re-index
        await self._index_document(job)
    
    async def _update_indexed_document_record(self, job: IndexingJob, doc: Dict[str, Any]):
        """Update the indexed document record"""
        async with async_session_factory() as db:
            # Check if record exists
            result = await db.execute(
                select(IndexedDocument).where(
                    IndexedDocument.document_id == job.document_id
                )
            )
            indexed_doc = result.scalar_one_or_none()
            
            if indexed_doc:
                # Update existing record
                indexed_doc.last_indexed_at = datetime.utcnow()
                indexed_doc.title = doc.get('title')
                indexed_doc.content_length = len(doc.get('content', ''))
                indexed_doc.quality_score = doc.get('quality_score')
                indexed_doc.medical_relevance_score = doc.get('medical_relevance_score')
                indexed_doc.updated_at = datetime.utcnow()
            else:
                # Create new record
                indexed_doc = IndexedDocument(
                    document_id=job.document_id,
                    elasticsearch_index=self.index_name,
                    elasticsearch_id=str(job.document_id),
                    title=doc.get('title'),
                    content_length=len(doc.get('content', '')),
                    quality_score=doc.get('quality_score'),
                    medical_relevance_score=doc.get('medical_relevance_score')
                )
                db.add(indexed_doc)
            
            await db.commit()
    
    async def _handle_job_failure(self, db: AsyncSession, job: IndexingJob, error_message: str):
        """Handle indexing job failure"""
        job.status = 'failed'
        job.error_message = error_message
        job.retry_count += 1
        job.completed_at = datetime.utcnow()
        
        # Check if we should retry
        if job.retry_count < job.max_retries:
            job.status = 'pending'  # Reset to pending for retry
            logger.info("Indexing job will be retried", 
                       job_id=str(job.id), retry_count=job.retry_count)
        
        await db.commit()
    
    async def get_indexing_stats(self) -> Dict[str, Any]:
        """Get indexing statistics"""
        async with async_session_factory() as db:
            # Count jobs by status
            status_counts = {}
            for status in ['pending', 'processing', 'completed', 'failed']:
                result = await db.execute(
                    select(IndexingJob).where(IndexingJob.status == status)
                )
                status_counts[status] = len(result.scalars().all())
            
            # Count indexed documents
            indexed_count_result = await db.execute(select(IndexedDocument))
            indexed_count = len(indexed_count_result.scalars().all())
            
            return {
                "job_status_counts": status_counts,
                "total_indexed_documents": indexed_count,
                "elasticsearch_index": self.index_name
            }