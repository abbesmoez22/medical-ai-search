from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid


class ProcessingJobBase(BaseModel):
    document_id: uuid.UUID
    status: str = "pending"
    progress: int = 0
    processing_options: Optional[Dict[str, Any]] = None


class ProcessingJobCreate(ProcessingJobBase):
    s3_bucket: str
    s3_key: str
    mime_type: str
    original_filename: Optional[str] = None
    file_size: Optional[int] = None


class ProcessingJobUpdate(BaseModel):
    status: Optional[str] = None
    progress: Optional[int] = None
    error_message: Optional[str] = None


class ProcessingJobResponse(ProcessingJobBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    extracted_text: Optional[str] = None
    medical_entities: Optional[Dict[str, Any]] = None
    document_structure: Optional[Dict[str, Any]] = None
    quality_metrics: Optional[Dict[str, Any]] = None
    extraction_method: Optional[str] = None
    processing_time_seconds: Optional[int] = None
    text_length: Optional[int] = None
    entity_count: Optional[int] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    s3_bucket: Optional[str] = None
    s3_key: Optional[str] = None
    original_filename: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None


class ExtractedEntityBase(BaseModel):
    entity_type: str
    entity_text: str
    entity_label: Optional[str] = None
    confidence_score: Optional[float] = None
    start_position: Optional[int] = None
    end_position: Optional[int] = None
    context: Optional[str] = None
    extraction_method: Optional[str] = None


class ExtractedEntityResponse(ExtractedEntityBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    processing_job_id: uuid.UUID
    created_at: datetime


class ProcessingMetricsBase(BaseModel):
    total_processing_time: Optional[float] = None
    pdf_extraction_time: Optional[float] = None
    ner_processing_time: Optional[float] = None
    text_analysis_time: Optional[float] = None
    text_quality_score: Optional[float] = None
    medical_relevance_score: Optional[float] = None
    structure_completeness: Optional[float] = None
    entity_confidence_avg: Optional[float] = None
    word_count: Optional[int] = None
    sentence_count: Optional[int] = None
    paragraph_count: Optional[int] = None
    page_count: Optional[int] = None
    disease_count: Optional[int] = None
    drug_count: Optional[int] = None
    procedure_count: Optional[int] = None
    anatomy_count: Optional[int] = None


class ProcessingMetricsResponse(ProcessingMetricsBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    processing_job_id: uuid.UUID
    created_at: datetime


class ProcessingStatsResponse(BaseModel):
    status_counts: Dict[str, int]
    average_processing_time_seconds: float
    total_entities_extracted: int
    total_jobs: int