from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any, Optional
import uuid
from app.core.database import get_db
from app.db.models import IndexingJob, IndexedDocument, IndexingMetrics
from app.services.indexing_service import DocumentIndexingService
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/indexing", tags=["indexing"])


@router.get("/jobs", response_model=List[Dict[str, Any]])
async def list_indexing_jobs(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    job_type_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List indexing jobs with optional filtering"""
    try:
        query = select(IndexingJob)
        
        if status_filter:
            query = query.where(IndexingJob.status == status_filter)
        
        if job_type_filter:
            query = query.where(IndexingJob.job_type == job_type_filter)
        
        query = query.offset(skip).limit(limit).order_by(IndexingJob.created_at.desc())
        
        result = await db.execute(query)
        jobs = result.scalars().all()
        
        return [
            {
                "id": str(job.id),
                "document_id": str(job.document_id),
                "job_type": job.job_type,
                "status": job.status,
                "elasticsearch_index": job.elasticsearch_index,
                "processing_time_seconds": job.processing_time_seconds,
                "error_message": job.error_message,
                "retry_count": job.retry_count,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None
            }
            for job in jobs
        ]
        
    except Exception as e:
        logger.error("Failed to list indexing jobs", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve indexing jobs"
        )


@router.get("/jobs/{job_id}")
async def get_indexing_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get specific indexing job details"""
    try:
        result = await db.execute(
            select(IndexingJob).where(IndexingJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Indexing job not found"
            )
        
        return {
            "id": str(job.id),
            "document_id": str(job.document_id),
            "job_type": job.job_type,
            "status": job.status,
            "elasticsearch_index": job.elasticsearch_index,
            "document_data": job.document_data,
            "processing_time_seconds": job.processing_time_seconds,
            "error_message": job.error_message,
            "retry_count": job.retry_count,
            "max_retries": job.max_retries,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "created_by": job.created_by,
            "notes": job.notes
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get indexing job", job_id=str(job_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve indexing job"
        )


@router.post("/jobs/{job_id}/retry")
async def retry_indexing_job(
    job_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Retry a failed indexing job"""
    try:
        result = await db.execute(
            select(IndexingJob).where(IndexingJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Indexing job not found"
            )
        
        if job.status not in ["failed"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job can only be retried if it has failed"
            )
        
        # Reset job status
        job.status = "pending"
        job.error_message = None
        job.started_at = None
        job.completed_at = None
        
        await db.commit()
        
        # Add background task to process the job
        indexing_service = DocumentIndexingService()
        background_tasks.add_task(indexing_service._process_indexing_job, job_id)
        
        return {"message": "Indexing job retry initiated", "job_id": str(job_id)}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retry indexing job", job_id=str(job_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retry indexing job"
        )


@router.get("/documents")
async def list_indexed_documents(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List indexed documents"""
    try:
        query = select(IndexedDocument).offset(skip).limit(limit).order_by(
            IndexedDocument.last_indexed_at.desc()
        )
        
        result = await db.execute(query)
        documents = result.scalars().all()
        
        return [
            {
                "id": str(doc.id),
                "document_id": str(doc.document_id),
                "elasticsearch_index": doc.elasticsearch_index,
                "elasticsearch_id": doc.elasticsearch_id,
                "title": doc.title,
                "content_length": doc.content_length,
                "entity_count": doc.entity_count,
                "quality_score": doc.quality_score,
                "medical_relevance_score": doc.medical_relevance_score,
                "indexing_version": doc.indexing_version,
                "last_indexed_at": doc.last_indexed_at.isoformat() if doc.last_indexed_at else None,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "updated_at": doc.updated_at.isoformat() if doc.updated_at else None
            }
            for doc in documents
        ]
        
    except Exception as e:
        logger.error("Failed to list indexed documents", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve indexed documents"
        )


@router.get("/stats")
async def get_indexing_stats():
    """Get indexing statistics"""
    try:
        indexing_service = DocumentIndexingService()
        stats = await indexing_service.get_indexing_stats()
        
        return stats
        
    except Exception as e:
        logger.error("Failed to get indexing stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve indexing statistics"
        )


@router.delete("/documents/{document_id}")
async def delete_indexed_document(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Delete a document from the search index"""
    try:
        # Check if document is indexed
        result = await db.execute(
            select(IndexedDocument).where(IndexedDocument.document_id == document_id)
        )
        indexed_doc = result.scalar_one_or_none()
        
        if not indexed_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found in index"
            )
        
        # Create deletion job
        indexing_service = DocumentIndexingService()
        job_id = await indexing_service._create_indexing_job(
            document_id=str(document_id),
            job_type='delete'
        )
        
        # Add background task to process the deletion
        background_tasks.add_task(indexing_service._process_indexing_job, job_id)
        
        return {
            "message": "Document deletion initiated",
            "document_id": str(document_id),
            "job_id": str(job_id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete indexed document", 
                    document_id=str(document_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete indexed document"
        )