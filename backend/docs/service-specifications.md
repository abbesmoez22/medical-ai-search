# Service Specifications - Phase 2 Backend Services
## Detailed Technical Specifications for Each Microservice

---

## 🏗️ Service Architecture Overview

```mermaid
graph TB
    subgraph "API Gateway Layer"
        Kong[Kong Gateway :8100]
    end
    
    subgraph "Application Services"
        Auth[Auth Service :8010]
        Doc[Document Service :8011]
        Proc[Processing Service :8013]
        Search[Search API :8012]
        Index[Search Indexing :8014]
    end
    
    subgraph "Data Layer"
        PG[(PostgreSQL :5433)]
        Redis[(Redis :6380)]
        ES[(Elasticsearch :9201)]
        S3[(AWS S3)]
    end
    
    subgraph "Message Layer"
        Kafka[Kafka :9095]
    end
    
    Kong --> Auth
    Kong --> Doc
    Kong --> Search
    
    Doc --> PG
    Doc --> Redis
    Doc --> S3
    Doc --> Kafka
    
    Proc --> Kafka
    Proc --> PG
    
    Index --> Kafka
    Index --> ES
    
    Search --> ES
    Search --> PG
```

---

## 📦 Service 1: Document Management Service

### Service Overview
- **Port**: 8011
- **Database**: document_db
- **Purpose**: Handle document uploads, metadata management, and file storage
- **Dependencies**: PostgreSQL, Redis, S3, Kafka

### API Endpoints

#### Document Upload
```http
POST /api/v1/documents/upload
Content-Type: multipart/form-data
Authorization: Bearer <jwt_token>

Form Data:
- file: PDF file (max 50MB)
- title: string (optional)
- authors: string (optional)
- journal: string (optional)
- keywords: string (optional)
- is_public: boolean (default: false)

Response:
{
  "document_id": "uuid",
  "status": "uploaded",
  "file_size": 1024000,
  "processing_status": "queued"
}
```

#### Get Document Metadata
```http
GET /api/v1/documents/{document_id}
Authorization: Bearer <jwt_token>

Response:
{
  "id": "uuid",
  "filename": "research_paper.pdf",
  "title": "Medical Research Study",
  "authors": ["Dr. Smith", "Dr. Johnson"],
  "journal": "Nature Medicine",
  "file_size": 1024000,
  "upload_date": "2024-01-15T10:30:00Z",
  "processing_status": "completed",
  "quality_score": 0.85,
  "word_count": 5000,
  "page_count": 12
}
```

#### List User Documents
```http
GET /api/v1/documents?page=1&limit=20&status=completed
Authorization: Bearer <jwt_token>

Response:
{
  "documents": [...],
  "total": 150,
  "page": 1,
  "limit": 20,
  "has_next": true
}
```

#### Download Document
```http
GET /api/v1/documents/{document_id}/download
Authorization: Bearer <jwt_token>

Response: Presigned S3 URL or file stream
```

#### Delete Document
```http
DELETE /api/v1/documents/{document_id}
Authorization: Bearer <jwt_token>

Response:
{
  "message": "Document deleted successfully",
  "document_id": "uuid"
}
```

### Database Schema

```sql
-- Document Management Database Schema
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- File Information
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_size INTEGER NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    file_hash VARCHAR(64) NOT NULL UNIQUE,
    
    -- Storage Information
    s3_bucket VARCHAR(100) NOT NULL,
    s3_key VARCHAR(500) NOT NULL,
    s3_version_id VARCHAR(100),
    
    -- Document Metadata
    title VARCHAR(500),
    authors JSONB,  -- Array of author names
    journal VARCHAR(200),
    publication_date DATE,
    doi VARCHAR(100),
    pmid VARCHAR(20),
    abstract TEXT,
    keywords JSONB,  -- Array of keywords
    
    -- Processing Status
    processing_status VARCHAR(50) DEFAULT 'uploaded',
    extraction_status VARCHAR(50) DEFAULT 'pending',
    indexing_status VARCHAR(50) DEFAULT 'pending',
    
    -- Quality Metrics
    text_quality_score DECIMAL(3,2),
    page_count INTEGER,
    word_count INTEGER,
    
    -- Access Control
    uploaded_by UUID NOT NULL,
    is_public BOOLEAN DEFAULT false,
    access_level VARCHAR(20) DEFAULT 'private',
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

CREATE TABLE document_access_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    permission_type VARCHAR(20) NOT NULL, -- 'read', 'write', 'admin'
    granted_by UUID NOT NULL,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE document_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    s3_key VARCHAR(500) NOT NULL,
    s3_version_id VARCHAR(100),
    file_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID NOT NULL
);

-- Indexes
CREATE INDEX idx_documents_uploaded_by ON documents(uploaded_by);
CREATE INDEX idx_documents_created_at ON documents(created_at);
CREATE INDEX idx_documents_processing_status ON documents(processing_status);
CREATE INDEX idx_documents_file_hash ON documents(file_hash);
```

### Environment Variables
```bash
# Service Configuration
DEBUG=true
SERVICE_NAME=document-management
PORT=8000

# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/document_db

# Redis
REDIS_URL=redis://redis:6379/1

# AWS S3
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=medical-ai-documents

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_TOPIC_PREFIX=medical-ai-platform

# File Upload Limits
MAX_FILE_SIZE=52428800  # 50MB
ALLOWED_MIME_TYPES=application/pdf,text/plain

# Security
JWT_SECRET_KEY=your-jwt-secret
JWT_ALGORITHM=HS256
```

---

## 📦 Service 2: Content Processing Service

### Service Overview
- **Port**: 8013
- **Database**: processing_db
- **Purpose**: Extract text, perform medical NER, and prepare content for indexing
- **Dependencies**: PostgreSQL, Kafka, S3 (read access)

### Processing Pipeline

#### 1. PDF Text Extraction
```python
# Text extraction capabilities
- Extract text from PDF files
- Handle OCR for scanned documents
- Preserve document structure
- Extract metadata (author, title, etc.)
- Calculate quality scores
- Detect language and encoding
```

#### 2. Medical Entity Recognition
```python
# Medical NER capabilities
- Disease and condition identification
- Drug and medication extraction
- Medical procedure recognition
- Anatomical structure identification
- Dosage and measurement extraction
- Clinical abbreviation expansion
```

#### 3. Content Enhancement
```python
# Content processing features
- Text cleaning and normalization
- Citation parsing and linking
- Reference extraction
- Abstract identification
- Section segmentation
- Quality assessment
```

### API Endpoints

#### Trigger Processing
```http
POST /api/v1/processing/process-document
Content-Type: application/json
Authorization: Bearer <jwt_token>

Body:
{
  "document_id": "uuid",
  "s3_bucket": "medical-ai-documents",
  "s3_key": "documents/user/file.pdf",
  "processing_options": {
    "extract_entities": true,
    "extract_citations": true,
    "calculate_quality": true
  }
}

Response:
{
  "processing_id": "uuid",
  "status": "started",
  "estimated_completion": "2024-01-15T10:35:00Z"
}
```

#### Get Processing Status
```http
GET /api/v1/processing/{processing_id}/status
Authorization: Bearer <jwt_token>

Response:
{
  "processing_id": "uuid",
  "document_id": "uuid",
  "status": "completed",
  "progress": 100,
  "steps_completed": [
    "text_extraction",
    "entity_recognition",
    "quality_assessment"
  ],
  "results": {
    "text_extracted": true,
    "entities_found": 45,
    "quality_score": 0.87,
    "word_count": 5000
  }
}
```

#### Get Extracted Content
```http
GET /api/v1/processing/{processing_id}/content
Authorization: Bearer <jwt_token>

Response:
{
  "document_id": "uuid",
  "extracted_text": "Full document text...",
  "medical_entities": {
    "diseases": [
      {"text": "diabetes", "confidence": 0.95, "position": [100, 108]},
      {"text": "hypertension", "confidence": 0.89, "position": [250, 262]}
    ],
    "drugs": [
      {"text": "metformin", "confidence": 0.92, "position": [300, 309]}
    ],
    "procedures": [...]
  },
  "document_structure": {
    "abstract": {"start": 0, "end": 500},
    "introduction": {"start": 501, "end": 1200},
    "methods": {"start": 1201, "end": 2500}
  },
  "quality_metrics": {
    "overall_score": 0.87,
    "text_clarity": 0.90,
    "structure_score": 0.85,
    "medical_relevance": 0.86
  }
}
```

### Database Schema

```sql
-- Content Processing Database Schema
CREATE TABLE processing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    
    -- Processing Configuration
    processing_options JSONB,
    
    -- Results
    extracted_text TEXT,
    medical_entities JSONB,
    document_structure JSONB,
    quality_metrics JSONB,
    
    -- Error Handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Processing Details
    processing_time_seconds INTEGER,
    text_length INTEGER,
    entity_count INTEGER
);

CREATE TABLE extracted_entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    processing_job_id UUID REFERENCES processing_jobs(id) ON DELETE CASCADE,
    entity_type VARCHAR(50) NOT NULL,
    entity_text VARCHAR(500) NOT NULL,
    confidence_score DECIMAL(4,3),
    start_position INTEGER,
    end_position INTEGER,
    context TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_processing_jobs_document_id ON processing_jobs(document_id);
CREATE INDEX idx_processing_jobs_status ON processing_jobs(status);
CREATE INDEX idx_extracted_entities_job_id ON extracted_entities(processing_job_id);
CREATE INDEX idx_extracted_entities_type ON extracted_entities(entity_type);
```

---

## 📦 Service 3: Search Indexing Service

### Service Overview
- **Port**: 8014
- **Database**: None (Elasticsearch only)
- **Purpose**: Index processed documents in Elasticsearch with medical-specific configurations
- **Dependencies**: Elasticsearch, Kafka

### Elasticsearch Index Configuration

#### Medical Documents Index
```json
{
  "settings": {
    "number_of_shards": 3,
    "number_of_replicas": 1,
    "analysis": {
      "analyzer": {
        "medical_analyzer": {
          "type": "custom",
          "tokenizer": "standard",
          "filter": [
            "lowercase",
            "medical_synonyms",
            "medical_stemmer",
            "stop_words_medical"
          ]
        },
        "medical_search_analyzer": {
          "type": "custom",
          "tokenizer": "standard",
          "filter": [
            "lowercase",
            "medical_synonyms",
            "medical_stemmer"
          ]
        }
      },
      "filter": {
        "medical_synonyms": {
          "type": "synonym",
          "synonyms_path": "medical_synonyms.txt"
        },
        "medical_stemmer": {
          "type": "stemmer",
          "language": "english"
        },
        "stop_words_medical": {
          "type": "stop",
          "stopwords": ["patient", "study", "clinical", "treatment"]
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "document_id": {"type": "keyword"},
      "title": {
        "type": "text",
        "analyzer": "medical_analyzer",
        "search_analyzer": "medical_search_analyzer",
        "fields": {
          "keyword": {"type": "keyword"},
          "suggest": {
            "type": "completion",
            "analyzer": "simple"
          }
        }
      },
      "content": {
        "type": "text",
        "analyzer": "medical_analyzer",
        "search_analyzer": "medical_search_analyzer"
      },
      "abstract": {
        "type": "text",
        "analyzer": "medical_analyzer",
        "search_analyzer": "medical_search_analyzer"
      },
      "authors": {
        "type": "keyword",
        "fields": {
          "suggest": {
            "type": "completion"
          }
        }
      },
      "journal": {
        "type": "keyword",
        "fields": {
          "suggest": {
            "type": "completion"
          }
        }
      },
      "publication_date": {"type": "date"},
      "doi": {"type": "keyword"},
      "pmid": {"type": "keyword"},
      "keywords": {"type": "keyword"},
      "medical_entities": {
        "type": "nested",
        "properties": {
          "type": {"type": "keyword"},
          "text": {"type": "keyword"},
          "confidence": {"type": "float"},
          "position": {"type": "integer"}
        }
      },
      "document_structure": {
        "type": "object",
        "properties": {
          "abstract": {"type": "object"},
          "introduction": {"type": "object"},
          "methods": {"type": "object"},
          "results": {"type": "object"},
          "conclusion": {"type": "object"}
        }
      },
      "quality_score": {"type": "float"},
      "text_length": {"type": "integer"},
      "page_count": {"type": "integer"},
      "word_count": {"type": "integer"},
      "created_at": {"type": "date"},
      "indexed_at": {"type": "date"},
      "access_level": {"type": "keyword"},
      "uploaded_by": {"type": "keyword"}
    }
  }
}
```

### API Endpoints

#### Index Document
```http
POST /api/v1/indexing/index-document
Content-Type: application/json

Body:
{
  "document_id": "uuid",
  "document_data": {
    "title": "Medical Research Paper",
    "content": "Full extracted text...",
    "abstract": "Research abstract...",
    "authors": ["Dr. Smith", "Dr. Johnson"],
    "medical_entities": [...],
    "quality_score": 0.87
  }
}

Response:
{
  "indexing_id": "uuid",
  "status": "indexed",
  "index_name": "medical_documents",
  "document_id": "uuid"
}
```

#### Reindex Document
```http
PUT /api/v1/indexing/reindex/{document_id}
Content-Type: application/json

Response:
{
  "status": "reindexed",
  "document_id": "uuid",
  "previous_version": "1",
  "current_version": "2"
}
```

#### Delete from Index
```http
DELETE /api/v1/indexing/{document_id}

Response:
{
  "status": "deleted",
  "document_id": "uuid"
}
```

---

## 📦 Service 4: Search API Service

### Service Overview
- **Port**: 8012
- **Database**: search_db (for analytics and caching)
- **Purpose**: Provide comprehensive search functionality with medical-specific features
- **Dependencies**: Elasticsearch, PostgreSQL, Redis

### Search Features

#### 1. Multi-Modal Search
- **Text Search**: Full-text search with medical synonyms
- **Semantic Search**: Ready for vector embeddings (Phase 3)
- **Hybrid Search**: Combination of text and semantic
- **Faceted Search**: Filter by journal, date, authors, etc.
- **Fuzzy Search**: Handle typos and variations

#### 2. Medical-Specific Features
- **Medical Entity Search**: Search by diseases, drugs, procedures
- **Citation Search**: Find papers by citations
- **Similar Documents**: Find related papers
- **Trending Topics**: Popular medical topics
- **Expert Search**: Find papers by specific authors

### API Endpoints

#### Basic Search
```http
GET /api/v1/search?q=diabetes treatment&limit=20&offset=0
Authorization: Bearer <jwt_token>

Response:
{
  "query": "diabetes treatment",
  "total_hits": 1250,
  "max_score": 15.67,
  "took": 45,
  "results": [
    {
      "document_id": "uuid",
      "title": "Diabetes Treatment Protocols",
      "authors": ["Dr. Smith"],
      "journal": "Diabetes Care",
      "publication_date": "2024-01-15",
      "abstract": "Study on diabetes treatment...",
      "score": 15.67,
      "highlights": {
        "title": ["<em>Diabetes</em> <em>Treatment</em> Protocols"],
        "content": ["...effective <em>diabetes</em> <em>treatment</em>..."]
      },
      "medical_entities": [
        {"type": "disease", "text": "diabetes", "confidence": 0.95}
      ]
    }
  ],
  "facets": {
    "journals": [
      {"name": "Diabetes Care", "count": 45},
      {"name": "NEJM", "count": 32}
    ],
    "publication_years": [
      {"year": "2024", "count": 120},
      {"year": "2023", "count": 890}
    ],
    "medical_entities": [
      {"entity": "diabetes", "type": "disease", "count": 450},
      {"entity": "insulin", "type": "drug", "count": 320}
    ]
  }
}
```

#### Advanced Search
```http
POST /api/v1/search/advanced
Content-Type: application/json
Authorization: Bearer <jwt_token>

Body:
{
  "query": {
    "text": "diabetes treatment",
    "filters": {
      "journals": ["Diabetes Care", "NEJM"],
      "date_range": {
        "from": "2020-01-01",
        "to": "2024-12-31"
      },
      "authors": ["Dr. Smith"],
      "medical_entities": {
        "diseases": ["diabetes", "hypertension"],
        "drugs": ["insulin", "metformin"]
      }
    },
    "sort": [
      {"field": "relevance", "order": "desc"},
      {"field": "publication_date", "order": "desc"}
    ]
  },
  "limit": 50,
  "include_highlights": true,
  "include_facets": true
}
```

#### Search Suggestions
```http
GET /api/v1/search/suggest?q=diab&type=all
Authorization: Bearer <jwt_token>

Response:
{
  "suggestions": {
    "terms": [
      {"text": "diabetes", "score": 0.95, "type": "disease"},
      {"text": "diabetic", "score": 0.89, "type": "condition"}
    ],
    "authors": [
      {"text": "Dr. Diabetes", "score": 0.92, "papers": 45}
    ],
    "journals": [
      {"text": "Diabetes Care", "score": 0.98, "papers": 1250}
    ]
  }
}
```

#### Similar Documents
```http
GET /api/v1/search/similar/{document_id}?limit=10
Authorization: Bearer <jwt_token>

Response:
{
  "document_id": "uuid",
  "similar_documents": [
    {
      "document_id": "uuid2",
      "title": "Related Paper",
      "similarity_score": 0.85,
      "similarity_reasons": [
        "Common medical entities",
        "Similar authors",
        "Related journal"
      ]
    }
  ]
}
```

### Database Schema

```sql
-- Search Analytics Database Schema
CREATE TABLE search_queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    query_text TEXT NOT NULL,
    query_type VARCHAR(50) DEFAULT 'basic',
    filters_applied JSONB,
    results_count INTEGER,
    clicked_results JSONB,
    search_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE search_results_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_hash VARCHAR(64) NOT NULL UNIQUE,
    query_text TEXT NOT NULL,
    filters JSONB,
    results JSONB NOT NULL,
    total_hits INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

CREATE TABLE popular_searches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_text TEXT NOT NULL UNIQUE,
    search_count INTEGER DEFAULT 1,
    last_searched TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    trending_score DECIMAL(5,2) DEFAULT 0
);

-- Indexes
CREATE INDEX idx_search_queries_user_id ON search_queries(user_id);
CREATE INDEX idx_search_queries_created_at ON search_queries(created_at);
CREATE INDEX idx_search_cache_expires ON search_results_cache(expires_at);
CREATE INDEX idx_popular_searches_score ON popular_searches(trending_score DESC);
```

---

## 📦 Service 5: Kong Gateway Configuration

### Service Overview
- **Port**: 8100 (proxy), 8102 (admin)
- **Purpose**: Unified API gateway with authentication, rate limiting, and routing
- **Dependencies**: All backend services

### Gateway Configuration

#### Kong Services and Routes
```yaml
# kong.yml
_format_version: "3.0"

services:
  - name: auth-service
    url: http://medical-ai-auth-service:8000
    connect_timeout: 60000
    write_timeout: 60000
    read_timeout: 60000

  - name: document-service
    url: http://medical-ai-document-service:8000
    connect_timeout: 60000
    write_timeout: 300000  # Extended for file uploads
    read_timeout: 300000

  - name: search-service
    url: http://medical-ai-search-api:8000
    connect_timeout: 60000
    write_timeout: 60000
    read_timeout: 60000

routes:
  - name: auth-routes
    service: auth-service
    paths:
      - /api/v1/auth
      - /api/v1/users
    strip_path: false

  - name: document-routes
    service: document-service
    paths:
      - /api/v1/documents
    strip_path: false
    plugins:
      - name: jwt
        config:
          secret_is_base64: false
          key_claim_name: sub
      - name: request-size-limiting
        config:
          allowed_payload_size: 52428800  # 50MB

  - name: search-routes
    service: search-service
    paths:
      - /api/v1/search
    strip_path: false
    plugins:
      - name: jwt
        config:
          secret_is_base64: false
          key_claim_name: sub

plugins:
  - name: rate-limiting
    config:
      minute: 1000
      hour: 10000
      policy: redis
      redis_host: medical-ai-redis
      redis_port: 6379
      redis_database: 2

  - name: cors
    config:
      origins:
        - "http://localhost:3000"
        - "https://medical-ai-platform.com"
      methods:
        - GET
        - POST
        - PUT
        - DELETE
        - OPTIONS
      headers:
        - Accept
        - Accept-Version
        - Content-Length
        - Content-MD5
        - Content-Type
        - Date
        - Authorization
      exposed_headers:
        - X-Auth-Token
      credentials: true
      max_age: 3600

  - name: prometheus
    config:
      per_consumer: true
      status_code_metrics: true
      latency_metrics: true
      bandwidth_metrics: true
```

### Gateway Features

#### 1. Authentication
- JWT token validation across all services
- Token refresh handling
- User context propagation

#### 2. Rate Limiting
- Per-user rate limits
- Service-specific limits
- Redis-based distributed limiting

#### 3. Security
- CORS configuration
- Request size limiting
- IP whitelisting/blacklisting

#### 4. Monitoring
- Request/response logging
- Performance metrics
- Health check aggregation

---

## 🔄 Event-Driven Architecture

### Kafka Topic Structure
```
medical-ai-platform.document.events
├── document.uploaded
├── document.processing_started
├── document.text_extracted
├── document.entities_extracted
├── document.indexed
└── document.failed

medical-ai-platform.search.events
├── search.performed
├── search.clicked
└── search.trending_updated

medical-ai-platform.system.events
├── service.health_check
├── service.error
└── service.performance_alert
```

### Event Schemas
```json
// Document Event Schema
{
  "event_id": "uuid",
  "event_type": "document.uploaded",
  "timestamp": "2024-01-15T10:30:00Z",
  "source_service": "document-management",
  "correlation_id": "uuid",
  "user_id": "uuid",
  "data": {
    "document_id": "uuid",
    "filename": "research.pdf",
    "file_size": 1024000,
    "s3_bucket": "medical-ai-documents",
    "s3_key": "documents/user/file.pdf",
    "mime_type": "application/pdf"
  }
}
```

---

## 🧪 Testing Strategy

### Unit Tests
- Service-level business logic
- Database operations
- API endpoint validation
- Error handling scenarios

### Integration Tests
- Service-to-service communication
- Database transactions
- File upload/download workflows
- Search functionality

### End-to-End Tests
- Complete document processing pipeline
- User authentication flows
- Search and retrieval workflows
- Error recovery scenarios

### Performance Tests
- Concurrent user simulation
- Large file upload testing
- Search query performance
- Database query optimization

---

## 📊 Monitoring and Observability

### Health Check Endpoints
Each service provides comprehensive health checks:

```http
GET /health
Response:
{
  "service": "document-management",
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "dependencies": {
    "database": "healthy",
    "redis": "healthy",
    "s3": "healthy",
    "kafka": "healthy"
  },
  "metrics": {
    "uptime_seconds": 3600,
    "memory_usage_mb": 256,
    "cpu_usage_percent": 15,
    "active_connections": 25
  }
}
```

### Logging Standards
- Structured JSON logging
- Correlation ID tracking
- Performance metrics
- Error tracking with stack traces
- Security event logging

### Metrics Collection
- Request/response times
- Error rates
- Throughput metrics
- Resource utilization
- Business metrics (documents processed, searches performed)

This comprehensive specification provides all the technical details needed to implement each service correctly and ensure they work together seamlessly.