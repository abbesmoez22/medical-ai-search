import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Integer, DateTime, Boolean, Float, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    
    # Primary identification
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    
    # Job status and progress
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, processing, completed, failed
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    
    # Processing configuration
    processing_options: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Results
    extracted_text: Mapped[Optional[str]] = mapped_column(Text)
    medical_entities: Mapped[Optional[dict]] = mapped_column(JSON)
    document_structure: Mapped[Optional[dict]] = mapped_column(JSON)
    quality_metrics: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Processing metadata
    extraction_method: Mapped[Optional[str]] = mapped_column(String(50))
    processing_time_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    text_length: Mapped[Optional[int]] = mapped_column(Integer)
    entity_count: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # File information
    s3_bucket: Mapped[Optional[str]] = mapped_column(String(100))
    s3_key: Mapped[Optional[str]] = mapped_column(String(500))
    original_filename: Mapped[Optional[str]] = mapped_column(String(255))
    file_size: Mapped[Optional[int]] = mapped_column(Integer)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100))


class ExtractedEntity(Base):
    __tablename__ = "extracted_entities"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    processing_job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    
    # Entity information
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # disease, drug, procedure, etc.
    entity_text: Mapped[str] = mapped_column(String(500), nullable=False)
    entity_label: Mapped[Optional[str]] = mapped_column(String(100))  # spaCy label
    
    # Position and confidence
    confidence_score: Mapped[Optional[float]] = mapped_column(Float)
    start_position: Mapped[Optional[int]] = mapped_column(Integer)
    end_position: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Context
    context: Mapped[Optional[str]] = mapped_column(Text)
    
    # Metadata
    extraction_method: Mapped[Optional[str]] = mapped_column(String(50))  # spacy, regex, custom
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProcessingMetrics(Base):
    __tablename__ = "processing_metrics"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    processing_job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    
    # Performance metrics
    total_processing_time: Mapped[Optional[float]] = mapped_column(Float)
    pdf_extraction_time: Mapped[Optional[float]] = mapped_column(Float)
    ner_processing_time: Mapped[Optional[float]] = mapped_column(Float)
    text_analysis_time: Mapped[Optional[float]] = mapped_column(Float)
    
    # Quality metrics
    text_quality_score: Mapped[Optional[float]] = mapped_column(Float)
    medical_relevance_score: Mapped[Optional[float]] = mapped_column(Float)
    structure_completeness: Mapped[Optional[float]] = mapped_column(Float)
    entity_confidence_avg: Mapped[Optional[float]] = mapped_column(Float)
    
    # Content metrics
    word_count: Mapped[Optional[int]] = mapped_column(Integer)
    sentence_count: Mapped[Optional[int]] = mapped_column(Integer)
    paragraph_count: Mapped[Optional[int]] = mapped_column(Integer)
    page_count: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Medical content metrics
    disease_count: Mapped[Optional[int]] = mapped_column(Integer)
    drug_count: Mapped[Optional[int]] = mapped_column(Integer)
    procedure_count: Mapped[Optional[int]] = mapped_column(Integer)
    anatomy_count: Mapped[Optional[int]] = mapped_column(Integer)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)