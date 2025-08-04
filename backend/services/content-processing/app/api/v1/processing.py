from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any, Optional
import uuid
from app.core.database import get_db
from app.db.models import ProcessingJob, ExtractedEntity, ProcessingMetrics
from app.schemas.processing import (
    ProcessingJobResponse,
    ProcessingJobCreate,
    ProcessingJobUpdate,
    ExtractedEntityResponse,
    ProcessingMetricsResponse
)
from app.services.document_processor import DocumentProcessorService
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/processing", tags=["processing"])


@router.get("/jobs", response_model=List[ProcessingJobResponse])
async def list_processing_jobs(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List processing jobs with optional filtering"""
    try:
        query = select(ProcessingJob)
        
        if status_filter:
            query = query.where(ProcessingJob.status == status_filter)
        
        query = query.offset(skip).limit(limit).order_by(ProcessingJob.created_at.desc())
        
        result = await db.execute(query)
        jobs = result.scalars().all()
        
        return [ProcessingJobResponse.model_validate(job) for job in jobs]
        
    except Exception as e:
        logger.error("Failed to list processing jobs", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve processing jobs"
        )


@router.get("/jobs/{job_id}", response_model=ProcessingJobResponse)
async def get_processing_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get specific processing job details"""
    try:
        result = await db.execute(
            select(ProcessingJob).where(ProcessingJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Processing job not found"
            )
        
        return ProcessingJobResponse.model_validate(job)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get processing job", job_id=str(job_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve processing job"
        )


@router.get("/jobs/{job_id}/entities", response_model=List[ExtractedEntityResponse])
async def get_job_entities(
    job_id: uuid.UUID,
    entity_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get extracted entities for a processing job"""
    try:
        # Verify job exists
        job_result = await db.execute(
            select(ProcessingJob).where(ProcessingJob.id == job_id)
        )
        job = job_result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Processing job not found"
            )
        
        # Get entities
        query = select(ExtractedEntity).where(ExtractedEntity.processing_job_id == job_id)
        
        if entity_type:
            query = query.where(ExtractedEntity.entity_type == entity_type)
        
        query = query.order_by(ExtractedEntity.confidence_score.desc())
        
        result = await db.execute(query)
        entities = result.scalars().all()
        
        return [ExtractedEntityResponse.model_validate(entity) for entity in entities]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get job entities", job_id=str(job_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve entities"
        )


@router.get("/jobs/{job_id}/metrics", response_model=ProcessingMetricsResponse)
async def get_job_metrics(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get processing metrics for a job"""
    try:
        # Verify job exists
        job_result = await db.execute(
            select(ProcessingJob).where(ProcessingJob.id == job_id)
        )
        job = job_result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Processing job not found"
            )
        
        # Get metrics
        metrics_result = await db.execute(
            select(ProcessingMetrics).where(ProcessingMetrics.processing_job_id == job_id)
        )
        metrics = metrics_result.scalar_one_or_none()
        
        if not metrics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Processing metrics not found"
            )
        
        return ProcessingMetricsResponse.model_validate(metrics)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get job metrics", job_id=str(job_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metrics"
        )


@router.post("/jobs/{job_id}/retry")
async def retry_processing_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    processor: DocumentProcessorService = Depends()
):
    """Retry a failed processing job"""
    try:
        result = await db.execute(
            select(ProcessingJob).where(ProcessingJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Processing job not found"
            )
        
        if job.status not in ["failed", "completed"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job can only be retried if it has failed or completed"
            )
        
        # Reset job status
        job.status = "pending"
        job.progress = 0
        job.error_message = None
        job.started_at = None
        job.completed_at = None
        
        await db.commit()
        
        # Trigger reprocessing
        await processor._process_document_job(job_id)
        
        return {"message": "Processing job retry initiated", "job_id": str(job_id)}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retry processing job", job_id=str(job_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retry processing job"
        )


@router.get("/stats")
async def get_processing_stats(db: AsyncSession = Depends(get_db)):
    """Get overall processing statistics"""
    try:
        # Count jobs by status
        status_counts = {}
        for status_val in ["pending", "processing", "completed", "failed"]:
            result = await db.execute(
                select(ProcessingJob).where(ProcessingJob.status == status_val)
            )
            status_counts[status_val] = len(result.scalars().all())
        
        # Get average processing time
        completed_jobs = await db.execute(
            select(ProcessingJob).where(
                ProcessingJob.status == "completed",
                ProcessingJob.processing_time_seconds.isnot(None)
            )
        )
        completed_jobs_list = completed_jobs.scalars().all()
        
        avg_processing_time = 0
        if completed_jobs_list:
            avg_processing_time = sum(job.processing_time_seconds for job in completed_jobs_list) / len(completed_jobs_list)
        
        # Get total entities extracted
        total_entities_result = await db.execute(select(ExtractedEntity))
        total_entities = len(total_entities_result.scalars().all())
        
        return {
            "status_counts": status_counts,
            "average_processing_time_seconds": avg_processing_time,
            "total_entities_extracted": total_entities,
            "total_jobs": sum(status_counts.values())
        }
        
    except Exception as e:
        logger.error("Failed to get processing stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve processing statistics"
        )