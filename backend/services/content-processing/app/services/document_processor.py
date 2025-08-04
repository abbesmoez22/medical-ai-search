import asyncio
import json
import tempfile
import os
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
import boto3
from botocore.exceptions import ClientError
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.database import async_session_factory
from app.db.models import ProcessingJob, ExtractedEntity, ProcessingMetrics
from app.services.pdf_processor import PDFProcessor
from app.services.medical_ner import MedicalNERService

logger = structlog.get_logger()


class DocumentProcessorService:
    def __init__(self):
        self.pdf_processor = PDFProcessor()
        self.medical_ner = MedicalNERService()
        self.s3_client = None
        self.kafka_consumer = None
        self.kafka_producer = None
        self.consumer_task = None
        self.running = False
    
    async def initialize(self):
        """Initialize the document processor service"""
        try:
            # Initialize S3 client
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
            
            # Initialize Kafka producer
            self.kafka_producer = KafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda x: json.dumps(x).encode('utf-8'),
                key_serializer=lambda x: str(x).encode('utf-8') if x else None,
                acks='all',
                retries=3,
                max_in_flight_requests_per_connection=1,
                enable_idempotence=True
            )
            
            logger.info("Document processor service initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize document processor service", error=str(e))
            raise
    
    async def close(self):
        """Close the document processor service"""
        try:
            if self.kafka_producer:
                self.kafka_producer.close()
            
            logger.info("Document processor service closed")
            
        except Exception as e:
            logger.error("Error closing document processor service", error=str(e))
    
    async def start_kafka_consumer(self):
        """Start Kafka consumer for document events"""
        try:
            self.kafka_consumer = KafkaConsumer(
                f"{settings.KAFKA_TOPIC_PREFIX}.document.events",
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                auto_offset_reset='latest',
                enable_auto_commit=True,
                group_id='content-processing-service',
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            
            self.running = True
            logger.info("Kafka consumer started for document events")
            
            # Process messages
            for message in self.kafka_consumer:
                if not self.running:
                    break
                
                try:
                    event = message.value
                    await self._handle_document_event(event)
                    
                except Exception as e:
                    logger.error("Error processing Kafka message", error=str(e), message=message.value)
                    continue
                    
        except Exception as e:
            logger.error("Kafka consumer error", error=str(e))
        finally:
            if self.kafka_consumer:
                self.kafka_consumer.close()
    
    async def stop_kafka_consumer(self):
        """Stop Kafka consumer"""
        self.running = False
        if self.kafka_consumer:
            self.kafka_consumer.close()
        logger.info("Kafka consumer stopped")
    
    async def _handle_document_event(self, event: Dict[str, Any]):
        """Handle document-related events"""
        event_type = event.get('event_type')
        
        if event_type == 'document.uploaded':
            await self._process_uploaded_document(event)
        elif event_type == 'document.updated':
            # Handle document updates if needed
            pass
        elif event_type == 'document.deleted':
            # Clean up processing jobs for deleted documents
            await self._cleanup_deleted_document(event)
    
    async def _process_uploaded_document(self, event: Dict[str, Any]):
        """Process newly uploaded document"""
        try:
            data = event.get('data', {})
            document_id = data.get('document_id')
            s3_bucket = data.get('s3_bucket')
            s3_key = data.get('s3_key')
            mime_type = data.get('mime_type')
            
            if not all([document_id, s3_bucket, s3_key]):
                logger.error("Missing required data in document event", event=event)
                return
            
            # Create processing job
            job_id = await self._create_processing_job(
                document_id=document_id,
                s3_bucket=s3_bucket,
                s3_key=s3_key,
                mime_type=mime_type
            )
            
            # Process document
            await self._process_document_job(job_id)
            
        except Exception as e:
            logger.error("Error processing uploaded document", error=str(e), event=event)
    
    async def _create_processing_job(self, document_id: str, s3_bucket: str, 
                                   s3_key: str, mime_type: str) -> uuid.UUID:
        """Create a new processing job"""
        async with async_session_factory() as db:
            try:
                job = ProcessingJob(
                    document_id=uuid.UUID(document_id),
                    s3_bucket=s3_bucket,
                    s3_key=s3_key,
                    mime_type=mime_type,
                    status="pending",
                    processing_options={
                        "extract_entities": True,
                        "extract_structure": True,
                        "calculate_quality": True
                    }
                )
                
                db.add(job)
                await db.commit()
                await db.refresh(job)
                
                logger.info("Processing job created", job_id=str(job.id), document_id=document_id)
                return job.id
                
            except Exception as e:
                await db.rollback()
                logger.error("Failed to create processing job", error=str(e))
                raise
    
    async def _process_document_job(self, job_id: uuid.UUID):
        """Process a document processing job"""
        start_time = time.time()
        
        async with async_session_factory() as db:
            try:
                # Get job
                result = await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))
                job = result.scalar_one_or_none()
                
                if not job:
                    logger.error("Processing job not found", job_id=str(job_id))
                    return
                
                # Update job status
                job.status = "processing"
                job.started_at = datetime.utcnow()
                job.progress = 10
                await db.commit()
                
                # Download file from S3
                temp_file_path = await self._download_from_s3(job.s3_bucket, job.s3_key)
                job.progress = 20
                await db.commit()
                
                try:
                    # Extract text from PDF
                    pdf_start = time.time()
                    extraction_result = await self.pdf_processor.extract_text(temp_file_path)
                    pdf_time = time.time() - pdf_start
                    
                    job.progress = 50
                    job.extracted_text = extraction_result['text']
                    job.document_structure = extraction_result['document_structure']
                    job.quality_metrics = extraction_result['quality_metrics']
                    job.extraction_method = extraction_result['extraction_method']
                    job.text_length = len(extraction_result['text'])
                    await db.commit()
                    
                    # Perform medical NER
                    ner_start = time.time()
                    medical_entities = await self.medical_ner.extract_entities(extraction_result['text'])
                    medical_relevance = await self.medical_ner.analyze_medical_relevance(extraction_result['text'])
                    ner_time = time.time() - ner_start
                    
                    job.progress = 80
                    job.medical_entities = medical_entities
                    job.entity_count = sum(len(entities) for entities in medical_entities.values())
                    await db.commit()
                    
                    # Store individual entities
                    await self._store_extracted_entities(db, job_id, medical_entities)
                    
                    # Calculate and store metrics
                    await self._store_processing_metrics(
                        db, job_id, extraction_result, medical_entities, medical_relevance,
                        pdf_time, ner_time, time.time() - start_time
                    )
                    
                    # Complete job
                    job.status = "completed"
                    job.completed_at = datetime.utcnow()
                    job.processing_time_seconds = int(time.time() - start_time)
                    job.progress = 100
                    await db.commit()
                    
                    # Publish completion event
                    await self._publish_processing_complete_event(job, extraction_result, medical_entities)
                    
                    logger.info("Document processing completed successfully", 
                               job_id=str(job_id), 
                               processing_time=job.processing_time_seconds)
                
                finally:
                    # Clean up temporary file
                    if os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)
                
            except Exception as e:
                # Handle job failure
                await self._handle_job_failure(db, job_id, str(e))
                logger.error("Document processing failed", job_id=str(job_id), error=str(e))
    
    async def _download_from_s3(self, bucket: str, key: str) -> str:
        """Download file from S3 to temporary file"""
        try:
            # Create temporary file
            temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf')
            os.close(temp_fd)
            
            # Download from S3
            self.s3_client.download_file(bucket, key, temp_path)
            
            logger.info("File downloaded from S3", bucket=bucket, key=key, temp_path=temp_path)
            return temp_path
            
        except ClientError as e:
            logger.error("S3 download failed", error=str(e), bucket=bucket, key=key)
            raise
    
    async def _store_extracted_entities(self, db: AsyncSession, job_id: uuid.UUID, 
                                      medical_entities: Dict[str, Any]):
        """Store extracted entities in database"""
        try:
            entities_to_store = []
            
            for entity_type, entities in medical_entities.items():
                for entity in entities:
                    entity_record = ExtractedEntity(
                        processing_job_id=job_id,
                        entity_type=entity_type,
                        entity_text=entity['text'],
                        entity_label=entity.get('label'),
                        confidence_score=entity.get('confidence'),
                        start_position=entity.get('start'),
                        end_position=entity.get('end'),
                        extraction_method='medical_ner'
                    )
                    entities_to_store.append(entity_record)
            
            if entities_to_store:
                db.add_all(entities_to_store)
                await db.commit()
                
                logger.info("Stored extracted entities", 
                           job_id=str(job_id), 
                           entity_count=len(entities_to_store))
            
        except Exception as e:
            logger.error("Failed to store extracted entities", error=str(e))
            raise
    
    async def _store_processing_metrics(self, db: AsyncSession, job_id: uuid.UUID,
                                      extraction_result: Dict[str, Any],
                                      medical_entities: Dict[str, Any],
                                      medical_relevance: Dict[str, Any],
                                      pdf_time: float, ner_time: float, total_time: float):
        """Store processing metrics"""
        try:
            quality_metrics = extraction_result.get('quality_metrics', {})
            
            metrics = ProcessingMetrics(
                processing_job_id=job_id,
                total_processing_time=total_time,
                pdf_extraction_time=pdf_time,
                ner_processing_time=ner_time,
                text_quality_score=quality_metrics.get('overall_score'),
                medical_relevance_score=medical_relevance.get('medical_relevance_score'),
                structure_completeness=quality_metrics.get('structure_score'),
                word_count=extraction_result.get('word_count'),
                sentence_count=quality_metrics.get('sentence_count'),
                page_count=extraction_result.get('page_count'),
                disease_count=len(medical_entities.get('diseases', [])),
                drug_count=len(medical_entities.get('drugs', [])),
                procedure_count=len(medical_entities.get('procedures', [])),
                anatomy_count=len(medical_entities.get('anatomy', []))
            )
            
            db.add(metrics)
            await db.commit()
            
            logger.info("Processing metrics stored", job_id=str(job_id))
            
        except Exception as e:
            logger.error("Failed to store processing metrics", error=str(e))
            # Don't raise - metrics are not critical
    
    async def _handle_job_failure(self, db: AsyncSession, job_id: uuid.UUID, error_message: str):
        """Handle processing job failure"""
        try:
            result = await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))
            job = result.scalar_one_or_none()
            
            if job:
                job.status = "failed"
                job.error_message = error_message
                job.completed_at = datetime.utcnow()
                job.retry_count += 1
                await db.commit()
                
                # Publish failure event
                await self._publish_processing_failed_event(job, error_message)
            
        except Exception as e:
            logger.error("Failed to handle job failure", error=str(e))
    
    async def _publish_processing_complete_event(self, job: ProcessingJob, 
                                               extraction_result: Dict[str, Any],
                                               medical_entities: Dict[str, Any]):
        """Publish processing completion event"""
        try:
            event = {
                "event_id": str(uuid.uuid4()),
                "event_type": "document.processing_completed",
                "timestamp": datetime.utcnow().isoformat(),
                "source_service": "content-processing",
                "correlation_id": str(job.id),
                "data": {
                    "document_id": str(job.document_id),
                    "processing_job_id": str(job.id),
                    "text_length": job.text_length,
                    "entity_count": job.entity_count,
                    "quality_score": extraction_result.get('quality_metrics', {}).get('overall_score'),
                    "medical_entities": medical_entities,
                    "processing_time_seconds": job.processing_time_seconds
                }
            }
            
            topic = f"{settings.KAFKA_TOPIC_PREFIX}.processing.events"
            future = self.kafka_producer.send(topic, value=event, key=str(job.document_id))
            future.get(timeout=10)
            
            logger.info("Processing completion event published", 
                       document_id=str(job.document_id),
                       job_id=str(job.id))
            
        except Exception as e:
            logger.error("Failed to publish processing completion event", error=str(e))
    
    async def _publish_processing_failed_event(self, job: ProcessingJob, error_message: str):
        """Publish processing failure event"""
        try:
            event = {
                "event_id": str(uuid.uuid4()),
                "event_type": "document.processing_failed",
                "timestamp": datetime.utcnow().isoformat(),
                "source_service": "content-processing",
                "correlation_id": str(job.id),
                "data": {
                    "document_id": str(job.document_id),
                    "processing_job_id": str(job.id),
                    "error_message": error_message,
                    "retry_count": job.retry_count
                }
            }
            
            topic = f"{settings.KAFKA_TOPIC_PREFIX}.processing.events"
            future = self.kafka_producer.send(topic, value=event, key=str(job.document_id))
            future.get(timeout=10)
            
            logger.info("Processing failure event published", 
                       document_id=str(job.document_id),
                       job_id=str(job.id))
            
        except Exception as e:
            logger.error("Failed to publish processing failure event", error=str(e))
    
    async def _cleanup_deleted_document(self, event: Dict[str, Any]):
        """Clean up processing jobs for deleted documents"""
        try:
            data = event.get('data', {})
            document_id = data.get('document_id')
            
            if not document_id:
                return
            
            async with async_session_factory() as db:
                # Find and delete processing jobs for this document
                result = await db.execute(
                    select(ProcessingJob).where(ProcessingJob.document_id == uuid.UUID(document_id))
                )
                jobs = result.scalars().all()
                
                for job in jobs:
                    await db.delete(job)
                
                await db.commit()
                
                logger.info("Cleaned up processing jobs for deleted document", 
                           document_id=document_id, 
                           jobs_deleted=len(jobs))
            
        except Exception as e:
            logger.error("Failed to cleanup deleted document", error=str(e))