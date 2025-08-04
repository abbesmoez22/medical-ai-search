import json
import hashlib
from typing import Dict, Any, List, Optional
from elasticsearch import AsyncElasticsearch
import redis.asyncio as redis
from app.core.config import settings
import structlog

logger = structlog.get_logger()


class SearchService:
    """Service for searching medical documents"""
    
    def __init__(self):
        self.es_client = AsyncElasticsearch(
            [settings.ELASTICSEARCH_URL],
            request_timeout=settings.SEARCH_TIMEOUT,
            max_retries=3,
            retry_on_timeout=True
        )
        
        self.redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True
        )
        
        self.index_name = f"{settings.ELASTICSEARCH_INDEX_PREFIX}-documents"
    
    async def search_documents(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        page_size: int = None,
        sort_by: str = "_score",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """Search for medical documents"""
        
        if page_size is None:
            page_size = settings.DEFAULT_PAGE_SIZE
        
        page_size = min(page_size, settings.MAX_PAGE_SIZE)
        
        # Generate cache key
        cache_key = self._generate_cache_key(
            query, filters, page, page_size, sort_by, sort_order
        )
        
        # Try to get from cache first
        cached_result = await self._get_from_cache(cache_key)
        if cached_result:
            logger.info("Search result served from cache", cache_key=cache_key)
            return cached_result
        
        # Build Elasticsearch query
        es_query = self._build_elasticsearch_query(
            query, filters, page, page_size, sort_by, sort_order
        )
        
        try:
            # Execute search
            response = await self.es_client.search(
                index=self.index_name,
                body=es_query
            )
            
            # Process results
            result = self._process_search_results(response, page, page_size)
            
            # Cache the result
            await self._cache_result(cache_key, result)
            
            logger.info("Search completed", 
                       query=query, total_hits=result["total_hits"], 
                       page=page, page_size=page_size)
            
            return result
            
        except Exception as e:
            logger.error("Search failed", query=query, error=str(e))
            raise
    
    async def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific document by ID"""
        cache_key = f"doc:{document_id}"
        
        # Try cache first
        cached_doc = await self._get_from_cache(cache_key)
        if cached_doc:
            return cached_doc
        
        try:
            response = await self.es_client.get(
                index=self.index_name,
                id=document_id
            )
            
            if response.get('found'):
                doc = response['_source']
                doc['id'] = response['_id']
                doc['score'] = 1.0
                
                # Cache the document
                await self._cache_result(cache_key, doc)
                
                return doc
            
            return None
            
        except Exception as e:
            logger.error("Failed to get document", document_id=document_id, error=str(e))
            return None
    
    async def suggest_completions(self, query: str, size: int = 10) -> List[str]:
        """Get search suggestions/completions"""
        cache_key = f"suggest:{hashlib.md5(query.encode()).hexdigest()}"
        
        # Try cache first
        cached_suggestions = await self._get_from_cache(cache_key)
        if cached_suggestions:
            return cached_suggestions
        
        # Build suggestion query
        suggest_query = {
            "suggest": {
                "title_suggest": {
                    "prefix": query,
                    "completion": {
                        "field": "title.suggest",
                        "size": size
                    }
                },
                "content_suggest": {
                    "prefix": query,
                    "completion": {
                        "field": "content.suggest",
                        "size": size
                    }
                }
            }
        }
        
        try:
            response = await self.es_client.search(
                index=self.index_name,
                body=suggest_query
            )
            
            suggestions = []
            
            # Extract suggestions from response
            for suggest_type in ["title_suggest", "content_suggest"]:
                if suggest_type in response.get("suggest", {}):
                    for suggestion in response["suggest"][suggest_type]:
                        for option in suggestion.get("options", []):
                            text = option.get("text", "")
                            if text and text not in suggestions:
                                suggestions.append(text)
            
            # Cache suggestions
            await self._cache_result(cache_key, suggestions, ttl=3600)  # 1 hour
            
            return suggestions[:size]
            
        except Exception as e:
            logger.error("Failed to get suggestions", query=query, error=str(e))
            return []
    
    async def get_search_facets(self, query: str = "*") -> Dict[str, Any]:
        """Get search facets for filtering"""
        cache_key = f"facets:{hashlib.md5(query.encode()).hexdigest()}"
        
        # Try cache first
        cached_facets = await self._get_from_cache(cache_key)
        if cached_facets:
            return cached_facets
        
        # Build facets query
        facets_query = {
            "size": 0,
            "query": {
                "query_string": {
                    "query": query,
                    "default_field": "content"
                }
            },
            "aggs": {
                "document_types": {
                    "terms": {"field": "document_type", "size": 10}
                },
                "languages": {
                    "terms": {"field": "language", "size": 10}
                },
                "publication_years": {
                    "date_histogram": {
                        "field": "publication_date",
                        "calendar_interval": "year",
                        "format": "yyyy"
                    }
                },
                "quality_ranges": {
                    "range": {
                        "field": "quality_score",
                        "ranges": [
                            {"from": 0.0, "to": 0.3, "key": "low"},
                            {"from": 0.3, "to": 0.7, "key": "medium"},
                            {"from": 0.7, "to": 1.0, "key": "high"}
                        ]
                    }
                },
                "medical_entities": {
                    "nested": {
                        "path": "medical_entities"
                    },
                    "aggs": {
                        "entity_types": {
                            "terms": {"field": "medical_entities.entity_type", "size": 20}
                        }
                    }
                }
            }
        }
        
        try:
            response = await self.es_client.search(
                index=self.index_name,
                body=facets_query
            )
            
            facets = self._process_facets(response.get("aggregations", {}))
            
            # Cache facets
            await self._cache_result(cache_key, facets, ttl=1800)  # 30 minutes
            
            return facets
            
        except Exception as e:
            logger.error("Failed to get facets", query=query, error=str(e))
            return {}
    
    def _build_elasticsearch_query(
        self,
        query: str,
        filters: Optional[Dict[str, Any]],
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str
    ) -> Dict[str, Any]:
        """Build Elasticsearch query"""
        
        # Base query
        if query and query.strip() != "*":
            base_query = {
                "bool": {
                    "should": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": [
                                    "title^3",
                                    "abstract^2",
                                    "content",
                                    "authors",
                                    "keywords^2"
                                ],
                                "type": "best_fields",
                                "fuzziness": "AUTO"
                            }
                        },
                        {
                            "nested": {
                                "path": "medical_entities",
                                "query": {
                                    "match": {
                                        "medical_entities.entity_text": query
                                    }
                                },
                                "score_mode": "max"
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            }
        else:
            base_query = {"match_all": {}}
        
        # Apply filters
        filter_clauses = []
        if filters:
            if "document_type" in filters:
                filter_clauses.append({
                    "term": {"document_type": filters["document_type"]}
                })
            
            if "language" in filters:
                filter_clauses.append({
                    "term": {"language": filters["language"]}
                })
            
            if "date_range" in filters:
                date_filter = {"range": {"publication_date": {}}}
                if "from" in filters["date_range"]:
                    date_filter["range"]["publication_date"]["gte"] = filters["date_range"]["from"]
                if "to" in filters["date_range"]:
                    date_filter["range"]["publication_date"]["lte"] = filters["date_range"]["to"]
                filter_clauses.append(date_filter)
            
            if "quality_score" in filters:
                filter_clauses.append({
                    "range": {
                        "quality_score": {
                            "gte": filters["quality_score"].get("min", 0),
                            "lte": filters["quality_score"].get("max", 1)
                        }
                    }
                })
            
            if "medical_entities" in filters:
                filter_clauses.append({
                    "nested": {
                        "path": "medical_entities",
                        "query": {
                            "terms": {
                                "medical_entities.entity_type": filters["medical_entities"]
                            }
                        }
                    }
                })
        
        # Combine query and filters
        if filter_clauses:
            if isinstance(base_query, dict) and "bool" in base_query:
                base_query["bool"]["filter"] = filter_clauses
            else:
                base_query = {
                    "bool": {
                        "must": [base_query],
                        "filter": filter_clauses
                    }
                }
        
        # Build full query
        es_query = {
            "query": base_query,
            "from": (page - 1) * page_size,
            "size": page_size,
            "highlight": {
                "fields": {
                    "title": {},
                    "content": {"fragment_size": 150, "number_of_fragments": 3},
                    "abstract": {}
                }
            }
        }
        
        # Add sorting
        if sort_by == "_score":
            es_query["sort"] = [{"_score": {"order": sort_order}}]
        elif sort_by == "publication_date":
            es_query["sort"] = [{"publication_date": {"order": sort_order}}]
        elif sort_by == "quality_score":
            es_query["sort"] = [{"quality_score": {"order": sort_order}}]
        elif sort_by == "medical_relevance_score":
            es_query["sort"] = [{"medical_relevance_score": {"order": sort_order}}]
        
        return es_query
    
    def _process_search_results(
        self, 
        response: Dict[str, Any], 
        page: int, 
        page_size: int
    ) -> Dict[str, Any]:
        """Process Elasticsearch search results"""
        
        hits = response.get("hits", {})
        total_hits = hits.get("total", {}).get("value", 0)
        documents = []
        
        for hit in hits.get("hits", []):
            doc = hit["_source"]
            doc["id"] = hit["_id"]
            doc["score"] = hit["_score"]
            
            # Add highlights
            if "highlight" in hit:
                doc["highlights"] = hit["highlight"]
            
            documents.append(doc)
        
        return {
            "documents": documents,
            "total_hits": total_hits,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_hits + page_size - 1) // page_size,
            "has_next": page * page_size < total_hits,
            "has_previous": page > 1
        }
    
    def _process_facets(self, aggregations: Dict[str, Any]) -> Dict[str, Any]:
        """Process Elasticsearch aggregations into facets"""
        facets = {}
        
        # Document types
        if "document_types" in aggregations:
            facets["document_types"] = [
                {"value": bucket["key"], "count": bucket["doc_count"]}
                for bucket in aggregations["document_types"]["buckets"]
            ]
        
        # Languages
        if "languages" in aggregations:
            facets["languages"] = [
                {"value": bucket["key"], "count": bucket["doc_count"]}
                for bucket in aggregations["languages"]["buckets"]
            ]
        
        # Publication years
        if "publication_years" in aggregations:
            facets["publication_years"] = [
                {"value": int(bucket["key_as_string"]), "count": bucket["doc_count"]}
                for bucket in aggregations["publication_years"]["buckets"]
                if bucket["doc_count"] > 0
            ]
        
        # Quality ranges
        if "quality_ranges" in aggregations:
            facets["quality_ranges"] = [
                {"value": bucket["key"], "count": bucket["doc_count"]}
                for bucket in aggregations["quality_ranges"]["buckets"]
                if bucket["doc_count"] > 0
            ]
        
        # Medical entities
        if "medical_entities" in aggregations:
            entity_agg = aggregations["medical_entities"].get("entity_types", {})
            facets["medical_entities"] = [
                {"value": bucket["key"], "count": bucket["doc_count"]}
                for bucket in entity_agg.get("buckets", [])
            ]
        
        return facets
    
    def _generate_cache_key(
        self,
        query: str,
        filters: Optional[Dict[str, Any]],
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str
    ) -> str:
        """Generate cache key for search results"""
        cache_data = {
            "query": query,
            "filters": filters or {},
            "page": page,
            "page_size": page_size,
            "sort_by": sort_by,
            "sort_order": sort_order
        }
        
        cache_string = json.dumps(cache_data, sort_keys=True)
        return f"search:{hashlib.md5(cache_string.encode()).hexdigest()}"
    
    async def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get result from cache"""
        try:
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            logger.warning("Failed to get from cache", cache_key=cache_key, error=str(e))
        
        return None
    
    async def _cache_result(
        self, 
        cache_key: str, 
        result: Any, 
        ttl: int = None
    ):
        """Cache search result"""
        try:
            if ttl is None:
                ttl = settings.CACHE_TTL_SECONDS
            
            await self.redis_client.setex(
                cache_key,
                ttl,
                json.dumps(result, default=str)
            )
        except Exception as e:
            logger.warning("Failed to cache result", cache_key=cache_key, error=str(e))