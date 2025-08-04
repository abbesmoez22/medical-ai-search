import uuid
import magic
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.core.database import get_db
from app.db.models import Document
from app.schemas.document import (
    DocumentResponse, DocumentListResponse, DocumentUploadResponse, 
    DocumentDeleteResponse, PresignedUrlResponse, DocumentUpdate
)
from app.api.dependencies import get_current_active_user, CurrentUser
from app.services.storage import get_storage_service, S3StorageService
from app.events.publisher import publish_document_uploaded, publish_document_updated, publish_document_deleted
from app.core.config import settings
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    authors: Optional[str] = Form(None),
    journal: Optional[str] = Form(None),
    keywords: Optional[str] = Form(None),
    is_public: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user),
    storage: S3StorageService = Depends(get_storage_service)
):
    """Upload a medical document"""
    
    # Validate file type
    if file.content_type not in settings.ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file.content_type} not allowed. Allowed types: {', '.join(settings.ALLOWED_MIME_TYPES)}"
        )
    
    # Validate file size
    if file.size and file.size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE / (1024*1024):.1f}MB"
        )
    
    # Validate file content using python-magic
    file_content = await file.read()
    await file.seek(0)
    
    detected_mime = magic.from_buffer(file_content, mime=True)
    if detected_mime not in settings.ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content does not match allowed file types"
        )
    
    try:
        # Generate S3 key
        s3_key = f"documents/{current_user.id}/{uuid.uuid4()}/{file.filename}"
        
        # Upload to S3
        upload_result = await storage.upload_file(file.file, s3_key, file.content_type)
        
        # Create database record
        document = Document(
            filename=file.filename,
            original_filename=file.filename,
            file_size=len(file_content),
            mime_type=file.content_type,
            file_hash=upload_result['file_hash'],
            s3_bucket=upload_result['bucket'],
            s3_key=upload_result['key'],
            s3_version_id=upload_result.get('version_id'),
            title=title,
            authors=authors,
            journal=journal,
            keywords=keywords,
            is_public=is_public,
            uploaded_by=current_user.id
        )
        
        db.add(document)
        await db.commit()
        await db.refresh(document)
        
        # Publish event for processing
        await publish_document_uploaded(
            document_id=str(document.id),
            s3_bucket=document.s3_bucket,
            s3_key=document.s3_key,
            mime_type=document.mime_type,
            uploaded_by=str(current_user.id)
        )
        
        logger.info(
            "Document uploaded successfully",
            document_id=str(document.id),
            filename=file.filename,
            user_id=str(current_user.id)
        )
        
        return DocumentUploadResponse(
            document_id=document.id,
            status="uploaded",
            file_size=document.file_size,
            processing_status=document.processing_status
        )
        
    except Exception as e:
        logger.error("Document upload failed", error=str(e), filename=file.filename)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload document"
        )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """Get document metadata"""
    
    # Query document with access control
    query = select(Document).where(
        and_(
            Document.id == document_id,
            (Document.uploaded_by == current_user.id) | (Document.is_public == True)
        )
    )
    
    result = await db.execute(query)
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return DocumentResponse.from_orm(document)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """List user documents with pagination"""
    
    # Base query with access control
    base_query = select(Document).where(
        (Document.uploaded_by == current_user.id) | (Document.is_public == True)
    )
    
    # Apply filters
    if status:
        base_query = base_query.where(Document.processing_status == status)
    
    if search:
        search_term = f"%{search}%"
        base_query = base_query.where(
            (Document.title.ilike(search_term)) |
            (Document.filename.ilike(search_term)) |
            (Document.authors.ilike(search_term)) |
            (Document.journal.ilike(search_term))
        )
    
    # Get total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination and ordering
    query = base_query.order_by(Document.created_at.desc()).offset((page - 1) * limit).limit(limit)
    
    result = await db.execute(query)
    documents = result.scalars().all()
    
    return DocumentListResponse(
        documents=[DocumentResponse.from_orm(doc) for doc in documents],
        total=total,
        page=page,
        limit=limit,
        has_next=(page * limit) < total
    )


@router.get("/{document_id}/download", response_model=PresignedUrlResponse)
async def download_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user),
    storage: S3StorageService = Depends(get_storage_service)
):
    """Get presigned URL for document download"""
    
    # Check document access
    query = select(Document).where(
        and_(
            Document.id == document_id,
            (Document.uploaded_by == current_user.id) | (Document.is_public == True)
        )
    )
    
    result = await db.execute(query)
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    try:
        # Generate presigned URL
        presigned_url = await storage.get_presigned_url(document.s3_key, expiration=3600)
        
        return PresignedUrlResponse(
            url=presigned_url,
            expires_in=3600
        )
        
    except Exception as e:
        logger.error("Failed to generate presigned URL", error=str(e), document_id=str(document_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate download URL"
        )


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: uuid.UUID,
    document_update: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """Update document metadata"""
    
    # Check document ownership
    query = select(Document).where(
        and_(
            Document.id == document_id,
            Document.uploaded_by == current_user.id
        )
    )
    
    result = await db.execute(query)
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied"
        )
    
    try:
        # Update fields
        update_data = document_update.dict(exclude_unset=True)
        updated_fields = {}
        
        for field, value in update_data.items():
            if hasattr(document, field):
                setattr(document, field, value)
                updated_fields[field] = value
        
        document.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(document)
        
        # Publish update event
        await publish_document_updated(
            document_id=str(document.id),
            updated_fields=updated_fields,
            updated_by=str(current_user.id)
        )
        
        logger.info(
            "Document updated successfully",
            document_id=str(document.id),
            updated_fields=list(updated_fields.keys()),
            user_id=str(current_user.id)
        )
        
        return DocumentResponse.from_orm(document)
        
    except Exception as e:
        logger.error("Document update failed", error=str(e), document_id=str(document_id))
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update document"
        )


@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user),
    storage: S3StorageService = Depends(get_storage_service)
):
    """Delete document"""
    
    # Check document ownership
    query = select(Document).where(
        and_(
            Document.id == document_id,
            Document.uploaded_by == current_user.id
        )
    )
    
    result = await db.execute(query)
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied"
        )
    
    try:
        # Delete from S3
        await storage.delete_file(document.s3_key)
        
        # Delete from database
        await db.delete(document)
        await db.commit()
        
        # Publish delete event
        await publish_document_deleted(
            document_id=str(document.id),
            deleted_by=str(current_user.id)
        )
        
        logger.info(
            "Document deleted successfully",
            document_id=str(document.id),
            user_id=str(current_user.id)
        )
        
        return DocumentDeleteResponse(
            message="Document deleted successfully",
            document_id=document.id
        )
        
    except Exception as e:
        logger.error("Document deletion failed", error=str(e), document_id=str(document_id))
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )