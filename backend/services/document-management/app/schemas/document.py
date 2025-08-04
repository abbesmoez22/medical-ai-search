from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
import uuid


class DocumentBase(BaseModel):
    title: Optional[str] = None
    authors: Optional[str] = None  # JSON string of author list
    journal: Optional[str] = None
    publication_date: Optional[datetime] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    abstract: Optional[str] = None
    keywords: Optional[str] = None  # JSON string of keyword list
    is_public: bool = False


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(DocumentBase):
    processing_status: Optional[str] = None
    extraction_status: Optional[str] = None
    indexing_status: Optional[str] = None
    text_quality_score: Optional[float] = None
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    processed_at: Optional[datetime] = None


class DocumentResponse(DocumentBase):
    id: uuid.UUID
    filename: str
    original_filename: str
    file_size: int
    mime_type: str
    file_hash: str
    s3_bucket: str
    s3_key: str
    s3_version_id: Optional[str]
    processing_status: str
    extraction_status: str
    indexing_status: str
    text_quality_score: Optional[float]
    page_count: Optional[int]
    word_count: Optional[int]
    uploaded_by: uuid.UUID
    access_level: str
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime]

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int
    page: int
    limit: int
    has_next: bool


class DocumentUploadResponse(BaseModel):
    document_id: uuid.UUID
    status: str
    file_size: int
    processing_status: str


class DocumentDeleteResponse(BaseModel):
    message: str
    document_id: uuid.UUID


class PresignedUrlResponse(BaseModel):
    url: str
    expires_in: int