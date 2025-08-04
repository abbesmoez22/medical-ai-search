import time
from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import Optional, Dict, Any, List
from app.services.search_service import SearchService
from app.schemas.search import (
    SearchRequest, SearchResponse, DocumentResult, 
    SearchFacets, SuggestionResponse
)
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/search", tags=["search"])

# Create search service instance
search_service = SearchService()


@router.post("/", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """Search for medical documents"""
    start_time = time.time()
    
    try:
        result = await search_service.search_documents(
            query=request.query,
            filters=request.filters,
            page=request.page,
            page_size=request.page_size,
            sort_by=request.sort_by,
            sort_order=request.sort_order
        )
        
        search_time_ms = (time.time() - start_time) * 1000
        
        # Convert to response model
        documents = [DocumentResult(**doc) for doc in result["documents"]]
        
        response = SearchResponse(
            documents=documents,
            total_hits=result["total_hits"],
            page=result["page"],
            page_size=result["page_size"],
            total_pages=result["total_pages"],
            has_next=result["has_next"],
            has_previous=result["has_previous"],
            query=request.query,
            filters=request.filters,
            search_time_ms=search_time_ms
        )
        
        logger.info("Search request completed",
                   query=request.query, total_hits=result["total_hits"],
                   search_time_ms=search_time_ms)
        
        return response
        
    except Exception as e:
        logger.error("Search request failed", query=request.query, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search request failed"
        )


@router.get("/", response_model=SearchResponse)
async def search_documents_get(
    q: str = Query(..., description="Search query"),
    filters: Optional[str] = Query(None, description="JSON string of filters"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    sort_by: str = Query("_score", description="Sort field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order")
):
    """Search for medical documents (GET method)"""
    
    # Parse filters if provided
    parsed_filters = None
    if filters:
        try:
            import json
            parsed_filters = json.loads(filters)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid filters JSON format"
            )
    
    # Create request object
    request = SearchRequest(
        query=q,
        filters=parsed_filters,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    return await search_documents(request)


@router.get("/documents/{document_id}", response_model=DocumentResult)
async def get_document(document_id: str):
    """Get a specific document by ID"""
    try:
        document = await search_service.get_document_by_id(document_id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        return DocumentResult(**document)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get document", document_id=document_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document"
        )


@router.get("/suggest", response_model=SuggestionResponse)
async def get_suggestions(
    q: str = Query(..., description="Query for suggestions"),
    size: int = Query(10, ge=1, le=50, description="Number of suggestions")
):
    """Get search suggestions/completions"""
    try:
        suggestions = await search_service.suggest_completions(q, size)
        
        return SuggestionResponse(
            suggestions=suggestions,
            query=q
        )
        
    except Exception as e:
        logger.error("Failed to get suggestions", query=q, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get suggestions"
        )


@router.get("/facets", response_model=SearchFacets)
async def get_search_facets(
    q: str = Query("*", description="Query for facet filtering")
):
    """Get search facets for filtering"""
    try:
        facets = await search_service.get_search_facets(q)
        
        return SearchFacets(**facets)
        
    except Exception as e:
        logger.error("Failed to get facets", query=q, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get search facets"
        )


@router.get("/stats")
async def get_search_stats():
    """Get search statistics"""
    try:
        # Get basic index stats
        stats = await search_service.es_client.indices.stats(
            index=search_service.index_name
        )
        
        index_stats = stats.get("indices", {}).get(search_service.index_name, {})
        
        return {
            "index_name": search_service.index_name,
            "document_count": index_stats.get("total", {}).get("docs", {}).get("count", 0),
            "index_size_bytes": index_stats.get("total", {}).get("store", {}).get("size_in_bytes", 0),
            "cache_enabled": True,
            "cache_ttl_seconds": search_service.redis_client.connection_pool.connection_kwargs.get("socket_timeout", 300)
        }
        
    except Exception as e:
        logger.error("Failed to get search stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get search statistics"
        )