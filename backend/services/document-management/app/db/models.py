import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Integer, DateTime, Boolean, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"
    
    # Primary identification
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # File information
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    
    # Storage information
    s3_bucket: Mapped[str] = mapped_column(String(100), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    s3_version_id: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Document metadata
    title: Mapped[Optional[str]] = mapped_column(String(500))
    authors: Mapped[Optional[str]] = mapped_column(Text)  # JSON array
    journal: Mapped[Optional[str]] = mapped_column(String(200))
    publication_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    doi: Mapped[Optional[str]] = mapped_column(String(100))
    pmid: Mapped[Optional[str]] = mapped_column(String(20))
    abstract: Mapped[Optional[str]] = mapped_column(Text)
    keywords: Mapped[Optional[str]] = mapped_column(Text)  # JSON array
    
    # Processing status
    processing_status: Mapped[str] = mapped_column(String(50), default="uploaded")
    extraction_status: Mapped[str] = mapped_column(String(50), default="pending")
    indexing_status: Mapped[str] = mapped_column(String(50), default="pending")
    
    # Quality metrics
    text_quality_score: Mapped[Optional[float]] = mapped_column(Float)
    page_count: Mapped[Optional[int]] = mapped_column(Integer)
    word_count: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Access control
    uploaded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    access_level: Mapped[str] = mapped_column(String(20), default="private")
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)


class DocumentAccessPermission(Base):
    __tablename__ = "document_access_permissions"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    permission_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'read', 'write', 'admin'
    granted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    s3_version_id: Mapped[Optional[str]] = mapped_column(String(100))
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)