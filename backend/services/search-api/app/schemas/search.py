from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class SearchRequest(BaseModel):
    """Search request schema"""
    query: str = Field(..., description="Search query")
    filters: Optional[Dict[str, Any]] = Field(None, description="Search filters")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Number of results per page")
    sort_by: str = Field("_score", description="Sort field")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order")


class DocumentResult(BaseModel):
    """Document search result schema"""
    id: str
    document_id: str
    title: Optional[str] = None
    content: Optional[str] = None
    authors: Optional[str] = None
    abstract: Optional[str] = None
    keywords: Optional[List[str]] = None
    medical_entities: Optional[Dict[str, Any]] = None
    document_type: Optional[str] = None
    publication_date: Optional[datetime] = None
    language: Optional[str] = None
    file_size: Optional[int] = None
    page_count: Optional[int] = None
    quality_score: Optional[float] = None
    medical_relevance_score: Optional[float] = None
    score: float
    highlights: Optional[Dict[str, List[str]]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    indexed_at: Optional[datetime] = None


class SearchResponse(BaseModel):
    """Search response schema"""
    documents: List[DocumentResult]
    total_hits: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool
    query: str
    filters: Optional[Dict[str, Any]] = None
    search_time_ms: Optional[float] = None


class FacetValue(BaseModel):
    """Facet value schema"""
    value: str
    count: int


class SearchFacets(BaseModel):
    """Search facets schema"""
    document_types: Optional[List[FacetValue]] = None
    languages: Optional[List[FacetValue]] = None
    publication_years: Optional[List[FacetValue]] = None
    quality_ranges: Optional[List[FacetValue]] = None
    medical_entities: Optional[List[FacetValue]] = None


class SuggestionResponse(BaseModel):
    """Search suggestion response schema"""
    suggestions: List[str]
    query: str