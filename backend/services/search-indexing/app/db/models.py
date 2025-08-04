import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Integer, DateTime, Boolean, Float, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class IndexingJob(Base):
    """Track document indexing jobs"""
    __tablename__ = "indexing_jobs"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'index', 'update', 'delete'
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    
    # Job details
    elasticsearch_index: Mapped[Optional[str]] = mapped_column(String(100))
    document_data: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Processing info
    processing_time_seconds: Mapped[Optional[float]] = mapped_column(Float)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Metadata
    created_by: Mapped[Optional[str]] = mapped_column(String(100))
    notes: Mapped[Optional[str]] = mapped_column(Text)


class IndexedDocument(Base):
    """Track successfully indexed documents"""
    __tablename__ = "indexed_documents"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    elasticsearch_index: Mapped[str] = mapped_column(String(100), nullable=False)
    elasticsearch_id: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Document metadata
    title: Mapped[Optional[str]] = mapped_column(String(500))
    content_length: Mapped[Optional[int]] = mapped_column(Integer)
    entity_count: Mapped[Optional[int]] = mapped_column(Integer)
    quality_score: Mapped[Optional[float]] = mapped_column(Float)
    medical_relevance_score: Mapped[Optional[float]] = mapped_column(Float)
    
    # Indexing info
    indexing_version: Mapped[str] = mapped_column(String(20), default="1.0")
    last_indexed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    index_size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class IndexingMetrics(Base):
    """Store indexing performance metrics"""
    __tablename__ = "indexing_metrics"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    
    # Volume metrics
    documents_indexed: Mapped[int] = mapped_column(Integer, default=0)
    documents_updated: Mapped[int] = mapped_column(Integer, default=0)
    documents_deleted: Mapped[int] = mapped_column(Integer, default=0)
    failed_jobs: Mapped[int] = mapped_column(Integer, default=0)
    
    # Performance metrics
    avg_indexing_time_seconds: Mapped[Optional[float]] = mapped_column(Float)
    total_processing_time_seconds: Mapped[Optional[float]] = mapped_column(Float)
    peak_queue_size: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Quality metrics
    avg_quality_score: Mapped[Optional[float]] = mapped_column(Float)
    avg_medical_relevance: Mapped[Optional[float]] = mapped_column(Float)
    total_entities_indexed: Mapped[Optional[int]] = mapped_column(Integer)
    
    # System metrics
    elasticsearch_response_time_ms: Mapped[Optional[float]] = mapped_column(Float)
    memory_usage_mb: Mapped[Optional[float]] = mapped_column(Float)
    cpu_usage_percent: Mapped[Optional[float]] = mapped_column(Float)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)