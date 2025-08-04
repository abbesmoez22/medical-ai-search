from elasticsearch import AsyncElasticsearch
from app.core.config import settings
import structlog

logger = structlog.get_logger()

# Create Elasticsearch client
es_client = AsyncElasticsearch(
    [settings.ELASTICSEARCH_URL],
    request_timeout=30,
    max_retries=3,
    retry_on_timeout=True
)


async def get_elasticsearch():
    """Dependency to get Elasticsearch client"""
    return es_client


async def create_indices():
    """Create Elasticsearch indices with proper mappings"""
    
    # Document index mapping
    document_mapping = {
        "mappings": {
            "properties": {
                "document_id": {"type": "keyword"},
                "title": {
                    "type": "text",
                    "analyzer": "standard",
                    "fields": {
                        "keyword": {"type": "keyword"}
                    }
                },
                "content": {
                    "type": "text",
                    "analyzer": "standard"
                },
                "authors": {
                    "type": "text",
                    "analyzer": "standard"
                },
                "abstract": {
                    "type": "text",
                    "analyzer": "standard"
                },
                "keywords": {"type": "keyword"},
                "medical_entities": {
                    "type": "nested",
                    "properties": {
                        "entity_type": {"type": "keyword"},
                        "entity_text": {"type": "text"},
                        "entity_label": {"type": "keyword"},
                        "confidence_score": {"type": "float"},
                        "start_position": {"type": "integer"},
                        "end_position": {"type": "integer"}
                    }
                },
                "document_type": {"type": "keyword"},
                "publication_date": {"type": "date"},
                "language": {"type": "keyword"},
                "file_size": {"type": "long"},
                "page_count": {"type": "integer"},
                "quality_score": {"type": "float"},
                "medical_relevance_score": {"type": "float"},
                "created_at": {"type": "date"},
                "updated_at": {"type": "date"},
                "indexed_at": {"type": "date"}
            }
        },
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "analysis": {
                "analyzer": {
                    "medical_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": [
                            "lowercase",
                            "stop",
                            "snowball"
                        ]
                    }
                }
            }
        }
    }
    
    index_name = f"{settings.ELASTICSEARCH_INDEX_PREFIX}-documents"
    
    try:
        # Check if index exists
        if not await es_client.indices.exists(index=index_name):
            # Create index
            await es_client.indices.create(
                index=index_name,
                body=document_mapping
            )
            logger.info("Created Elasticsearch index", index=index_name)
        else:
            logger.info("Elasticsearch index already exists", index=index_name)
            
    except Exception as e:
        logger.error("Failed to create Elasticsearch index", 
                    index=index_name, error=str(e))
        raise