# Phase 2 Backend Implementation Guide
## Complete Document Processing & Search Pipeline

### Overview
This guide covers the remaining 80% of Phase 2 implementation, building upon the completed Authentication Service to create a complete document processing and search pipeline ready for AI/ML integration.

## 🎯 Implementation Timeline (8-10 Days)

### Week 1: Core Document Pipeline
- **Days 1-2**: Document Management Service
- **Days 3-4**: Content Processing Service  
- **Day 5**: Kafka Event Integration

### Week 2: Search & Integration
- **Days 6-7**: Search Infrastructure & API
- **Days 8-9**: API Gateway & Service Integration
- **Day 10**: Testing & Performance Optimization

---

## 📋 Prerequisites Checklist

### ✅ Completed Infrastructure
- [x] Authentication Service running on port 8010
- [x] PostgreSQL running on port 5433
- [x] Redis running on port 6380
- [x] Kafka running on port 9095
- [x] Elasticsearch running on port 9201
- [x] Kong Gateway infrastructure ready

### 🔧 Required Additions
- [ ] AWS S3 bucket for document storage
- [ ] Additional Python dependencies
- [ ] Service-specific databases
- [ ] Kafka topic configuration

---

## 🏗️ Service Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Kong Gateway  │    │  Auth Service   │    │ Document Mgmt   │
│     :8100       │◄──►│     :8010       │◄──►│    Service      │
└─────────────────┘    └─────────────────┘    │     :8011       │
                                               └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Search API     │    │Content Process  │    │     Kafka       │
│   Service       │◄──►│   Service       │◄──►│   :9095        │
│    :8012        │    │     :8013       │    └─────────────────┘
└─────────────────┘    └─────────────────┘             │
         │                       │                      ▼
         ▼                       ▼              ┌─────────────────┐
┌─────────────────┐    ┌─────────────────┐    │Search Indexing  │
│ Elasticsearch   │    │  PostgreSQL     │    │   Service       │
│    :9201        │    │    :5433        │    │    :8014        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## 📦 Service 1: Document Management Service

### Purpose
Handle document uploads, metadata storage, and file management with S3 integration.

### Implementation Steps

#### Step 1: Project Structure
```bash
mkdir -p backend/services/document-management/{app/{api/v1,core,db,schemas,services},tests}
```

#### Step 2: Dependencies (requirements.txt)
```txt
# Core FastAPI dependencies
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic[email]==2.5.0

# Database
sqlalchemy==2.0.23
alembic==1.13.0
asyncpg==0.29.0
redis==5.0.1

# File handling
boto3==1.34.0
python-multipart==0.0.6
python-magic==0.4.27
PyPDF2==3.0.1

# Event handling
kafka-python==2.0.2

# Security & Auth
python-jose[cryptography]==3.3.0
httpx==0.25.2

# Utilities
structlog==23.2.0
pydantic-settings==2.1.0
```

#### Step 3: Database Models
```python
# app/db/models.py
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Integer, DateTime, Boolean, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class Document(Base):
    __tablename__ = "documents"
    
    # Primary identification
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # File information
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    
    # Storage information
    s3_bucket: Mapped[str] = mapped_column(String(100), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    s3_version_id: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Document metadata
    title: Mapped[Optional[str]] = mapped_column(String(500))
    authors: Mapped[Optional[str]] = mapped_column(Text)  # JSON array
    journal: Mapped[Optional[str]] = mapped_column(String(200))
    publication_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    doi: Mapped[Optional[str]] = mapped_column(String(100))
    pmid: Mapped[Optional[str]] = mapped_column(String(20))
    abstract: Mapped[Optional[str]] = mapped_column(Text)
    keywords: Mapped[Optional[str]] = mapped_column(Text)  # JSON array
    
    # Processing status
    processing_status: Mapped[str] = mapped_column(String(50), default="uploaded")
    extraction_status: Mapped[str] = mapped_column(String(50), default="pending")
    indexing_status: Mapped[str] = mapped_column(String(50), default="pending")
    
    # Quality metrics
    text_quality_score: Mapped[Optional[float]] = mapped_column(Float)
    page_count: Mapped[Optional[int]] = mapped_column(Integer)
    word_count: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Access control
    uploaded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    access_level: Mapped[str] = mapped_column(String(20), default="private")
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
```

#### Step 4: S3 Integration Service
```python
# app/services/storage.py
import boto3
import hashlib
from typing import BinaryIO, Optional
from botocore.exceptions import ClientError
import structlog

logger = structlog.get_logger()

class S3StorageService:
    def __init__(self, bucket_name: str, aws_access_key: str, aws_secret_key: str, region: str = "us-east-1"):
        self.bucket_name = bucket_name
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=region
        )
    
    async def upload_file(self, file_obj: BinaryIO, key: str, content_type: str) -> dict:
        """Upload file to S3 and return metadata"""
        try:
            # Calculate file hash
            file_obj.seek(0)
            file_hash = hashlib.sha256(file_obj.read()).hexdigest()
            file_obj.seek(0)
            
            # Upload to S3
            response = self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                key,
                ExtraArgs={
                    'ContentType': content_type,
                    'Metadata': {
                        'file_hash': file_hash,
                        'uploaded_at': datetime.utcnow().isoformat()
                    }
                }
            )
            
            return {
                'bucket': self.bucket_name,
                'key': key,
                'file_hash': file_hash,
                'version_id': response.get('VersionId')
            }
            
        except ClientError as e:
            logger.error("S3 upload failed", error=str(e), key=key)
            raise
    
    async def delete_file(self, key: str) -> bool:
        """Delete file from S3"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            logger.error("S3 delete failed", error=str(e), key=key)
            return False
    
    async def get_presigned_url(self, key: str, expiration: int = 3600) -> str:
        """Generate presigned URL for file access"""
        try:
            return self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expiration
            )
        except ClientError as e:
            logger.error("Presigned URL generation failed", error=str(e), key=key)
            raise
```

#### Step 5: Document API Endpoints
```python
# app/api/v1/documents.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.storage import S3StorageService
from app.services.events import publish_document_event

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(None),
    authors: str = Form(None),
    journal: str = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    storage: S3StorageService = Depends(get_storage_service)
):
    """Upload a medical document"""
    
    # Validate file type
    allowed_types = ['application/pdf', 'text/plain']
    if file.content_type not in allowed_types:
        raise HTTPException(400, "Only PDF and text files are allowed")
    
    # Validate file size (max 50MB)
    if file.size > 50 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 50MB)")
    
    # Generate S3 key
    s3_key = f"documents/{current_user.id}/{uuid.uuid4()}/{file.filename}"
    
    # Upload to S3
    upload_result = await storage.upload_file(file.file, s3_key, file.content_type)
    
    # Create database record
    document = Document(
        filename=file.filename,
        original_filename=file.filename,
        file_size=file.size,
        mime_type=file.content_type,
        file_hash=upload_result['file_hash'],
        s3_bucket=upload_result['bucket'],
        s3_key=upload_result['key'],
        s3_version_id=upload_result.get('version_id'),
        title=title,
        authors=authors,
        journal=journal,
        uploaded_by=current_user.id
    )
    
    db.add(document)
    await db.commit()
    await db.refresh(document)
    
    # Publish event for processing
    await publish_document_event("document.uploaded", {
        "document_id": str(document.id),
        "s3_bucket": document.s3_bucket,
        "s3_key": document.s3_key,
        "mime_type": document.mime_type,
        "uploaded_by": str(current_user.id)
    })
    
    return {"document_id": document.id, "status": "uploaded"}
```

---

## 📦 Service 2: Content Processing Service

### Purpose
Extract text from documents, perform medical NER, and prepare content for indexing.

### Key Components

#### Step 1: PDF Processing Pipeline
```python
# app/services/pdf_processor.py
import PyPDF2
import re
from typing import Dict, List, Optional
import structlog

logger = structlog.get_logger()

class PDFProcessor:
    def __init__(self):
        self.medical_patterns = {
            'doi': r'10\.\d{4,}/[^\s]+',
            'pmid': r'PMID:\s*(\d+)',
            'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            'drug_names': r'\b[A-Z][a-z]+(?:mab|nib|tib|cept|pril|sartan|statin)\b'
        }
    
    async def extract_text(self, file_path: str) -> Dict[str, any]:
        """Extract text and metadata from PDF"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Extract metadata
                metadata = pdf_reader.metadata or {}
                
                # Extract text from all pages
                text_content = ""
                for page in pdf_reader.pages:
                    text_content += page.extract_text() + "\n"
                
                # Clean and process text
                cleaned_text = self._clean_text(text_content)
                
                # Extract structured information
                extracted_info = self._extract_medical_info(cleaned_text)
                
                return {
                    'text': cleaned_text,
                    'page_count': len(pdf_reader.pages),
                    'word_count': len(cleaned_text.split()),
                    'metadata': dict(metadata),
                    'extracted_info': extracted_info,
                    'quality_score': self._calculate_quality_score(cleaned_text)
                }
                
        except Exception as e:
            logger.error("PDF processing failed", error=str(e), file_path=file_path)
            raise
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page headers/footers patterns
        text = re.sub(r'Page \d+ of \d+', '', text)
        
        # Fix common OCR errors
        text = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', text)
        
        return text.strip()
    
    def _extract_medical_info(self, text: str) -> Dict[str, List[str]]:
        """Extract medical entities and patterns"""
        extracted = {}
        
        for pattern_name, pattern in self.medical_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            extracted[pattern_name] = list(set(matches))  # Remove duplicates
        
        return extracted
    
    def _calculate_quality_score(self, text: str) -> float:
        """Calculate text quality score (0-1)"""
        if not text:
            return 0.0
        
        # Factors for quality assessment
        word_count = len(text.split())
        char_count = len(text)
        
        # Check for reasonable word/character ratio
        avg_word_length = char_count / word_count if word_count > 0 else 0
        
        # Check for presence of medical terms
        medical_indicators = ['patient', 'treatment', 'diagnosis', 'study', 'clinical']
        medical_score = sum(1 for term in medical_indicators if term.lower() in text.lower())
        
        # Calculate composite score
        length_score = min(word_count / 1000, 1.0)  # Normalize to 1000 words
        medical_score = min(medical_score / len(medical_indicators), 1.0)
        format_score = 1.0 if 3 <= avg_word_length <= 8 else 0.5
        
        return (length_score + medical_score + format_score) / 3
```

#### Step 2: Medical NER Integration
```python
# app/services/medical_ner.py
import spacy
from typing import List, Dict
import structlog

logger = structlog.get_logger()

class MedicalNERService:
    def __init__(self):
        # Load medical NER model (install: pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.1/en_core_sci_md-0.5.1.tar.gz)
        try:
            self.nlp = spacy.load("en_core_sci_md")
        except OSError:
            logger.warning("Medical NER model not found, using basic model")
            self.nlp = spacy.load("en_core_web_sm")
    
    async def extract_entities(self, text: str) -> Dict[str, List[Dict]]:
        """Extract medical entities from text"""
        try:
            doc = self.nlp(text[:1000000])  # Limit text length
            
            entities = {
                'diseases': [],
                'drugs': [],
                'procedures': [],
                'anatomy': [],
                'general': []
            }
            
            for ent in doc.ents:
                entity_info = {
                    'text': ent.text,
                    'label': ent.label_,
                    'start': ent.start_char,
                    'end': ent.end_char,
                    'confidence': getattr(ent, 'prob', 0.0)
                }
                
                # Categorize entities
                if ent.label_ in ['DISEASE', 'SYMPTOM']:
                    entities['diseases'].append(entity_info)
                elif ent.label_ in ['DRUG', 'MEDICATION']:
                    entities['drugs'].append(entity_info)
                elif ent.label_ in ['PROCEDURE', 'TREATMENT']:
                    entities['procedures'].append(entity_info)
                elif ent.label_ in ['ANATOMY', 'ORGAN']:
                    entities['anatomy'].append(entity_info)
                else:
                    entities['general'].append(entity_info)
            
            return entities
            
        except Exception as e:
            logger.error("Medical NER failed", error=str(e))
            return {'diseases': [], 'drugs': [], 'procedures': [], 'anatomy': [], 'general': []}
```

---

## 📦 Service 3: Search Infrastructure

### Purpose
Index documents in Elasticsearch with medical-specific analyzers and provide search capabilities.

### Key Components

#### Step 1: Elasticsearch Configuration
```python
# app/services/elasticsearch_client.py
from elasticsearch import AsyncElasticsearch
from typing import Dict, List, Optional
import structlog

logger = structlog.get_logger()

class ElasticsearchService:
    def __init__(self, hosts: List[str]):
        self.client = AsyncElasticsearch(hosts=hosts)
        self.index_name = "medical_documents"
    
    async def create_index(self):
        """Create index with medical-specific mappings"""
        mapping = {
            "settings": {
                "analysis": {
                    "analyzer": {
                        "medical_analyzer": {
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
                            "synonyms": [
                                "heart,cardiac,cardio",
                                "lung,pulmonary,respiratory",
                                "brain,neural,cerebral"
                            ]
                        },
                        "medical_stemmer": {
                            "type": "stemmer",
                            "language": "english"
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
                        "fields": {"keyword": {"type": "keyword"}}
                    },
                    "content": {
                        "type": "text",
                        "analyzer": "medical_analyzer"
                    },
                    "abstract": {
                        "type": "text",
                        "analyzer": "medical_analyzer"
                    },
                    "authors": {"type": "keyword"},
                    "journal": {"type": "keyword"},
                    "publication_date": {"type": "date"},
                    "doi": {"type": "keyword"},
                    "pmid": {"type": "keyword"},
                    "keywords": {"type": "keyword"},
                    "medical_entities": {
                        "type": "nested",
                        "properties": {
                            "type": {"type": "keyword"},
                            "text": {"type": "keyword"},
                            "confidence": {"type": "float"}
                        }
                    },
                    "quality_score": {"type": "float"},
                    "created_at": {"type": "date"},
                    "access_level": {"type": "keyword"}
                }
            }
        }
        
        try:
            await self.client.indices.create(index=self.index_name, body=mapping, ignore=400)
            logger.info("Elasticsearch index created", index=self.index_name)
        except Exception as e:
            logger.error("Failed to create index", error=str(e))
            raise
    
    async def index_document(self, document_data: Dict) -> bool:
        """Index a document"""
        try:
            await self.client.index(
                index=self.index_name,
                id=document_data['document_id'],
                body=document_data
            )
            return True
        except Exception as e:
            logger.error("Document indexing failed", error=str(e), doc_id=document_data.get('document_id'))
            return False
    
    async def search_documents(self, query: str, filters: Dict = None, size: int = 20) -> Dict:
        """Search documents with medical-specific scoring"""
        search_body = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": [
                                    "title^3",
                                    "abstract^2",
                                    "content",
                                    "keywords^2"
                                ],
                                "type": "best_fields",
                                "analyzer": "medical_analyzer"
                            }
                        }
                    ],
                    "filter": []
                }
            },
            "highlight": {
                "fields": {
                    "title": {},
                    "abstract": {},
                    "content": {"fragment_size": 200}
                }
            },
            "size": size,
            "sort": [
                {"_score": {"order": "desc"}},
                {"quality_score": {"order": "desc"}},
                {"publication_date": {"order": "desc"}}
            ]
        }
        
        # Apply filters
        if filters:
            if filters.get('journal'):
                search_body["query"]["bool"]["filter"].append(
                    {"term": {"journal": filters['journal']}}
                )
            if filters.get('date_range'):
                search_body["query"]["bool"]["filter"].append(
                    {"range": {"publication_date": filters['date_range']}}
                )
        
        try:
            response = await self.client.search(index=self.index_name, body=search_body)
            return response
        except Exception as e:
            logger.error("Search failed", error=str(e), query=query)
            raise
```

---

## 📦 Service 4: API Gateway Integration

### Purpose
Unify all services under Kong Gateway with authentication, rate limiting, and routing.

### Kong Configuration

#### Step 1: Kong Services Configuration
```yaml
# kong/kong.yml
_format_version: "3.0"

services:
  - name: auth-service
    url: http://auth-service:8000
    plugins:
      - name: rate-limiting
        config:
          minute: 100
          hour: 1000

  - name: document-service
    url: http://document-service:8000
    plugins:
      - name: jwt
        config:
          secret_is_base64: false
      - name: rate-limiting
        config:
          minute: 50
          hour: 500

  - name: search-service
    url: http://search-service:8000
    plugins:
      - name: jwt
        config:
          secret_is_base64: false
      - name: rate-limiting
        config:
          minute: 200
          hour: 2000

routes:
  - name: auth-routes
    service: auth-service
    paths:
      - /api/v1/auth
      - /api/v1/users

  - name: document-routes
    service: document-service
    paths:
      - /api/v1/documents
    plugins:
      - name: request-size-limiting
        config:
          allowed_payload_size: 52428800  # 50MB

  - name: search-routes
    service: search-service
    paths:
      - /api/v1/search
```

#### Step 2: Docker Compose Updates
```yaml
# Add to docker-compose.dev.yml
  document-service:
    build:
      context: ./services/document-management
      dockerfile: Dockerfile
    container_name: medical-ai-document-service
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      kafka:
        condition: service_healthy
    environment:
      - DEBUG=true
      - DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/document_db
      - REDIS_URL=redis://redis:6379/1
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - S3_BUCKET_NAME=medical-ai-documents
    ports:
      - "8011:8000"
    networks:
      - medical-ai-network

  processing-service:
    build:
      context: ./services/content-processing
      dockerfile: Dockerfile
    container_name: medical-ai-processing-service
    depends_on:
      postgres:
        condition: service_healthy
      kafka:
        condition: service_healthy
    environment:
      - DEBUG=true
      - DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/processing_db
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
    ports:
      - "8013:8000"
    networks:
      - medical-ai-network

  search-indexing-service:
    build:
      context: ./services/search-indexing
      dockerfile: Dockerfile
    container_name: medical-ai-search-indexing
    depends_on:
      elasticsearch:
        condition: service_healthy
      kafka:
        condition: service_healthy
    environment:
      - DEBUG=true
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
    ports:
      - "8014:8000"
    networks:
      - medical-ai-network

  search-api-service:
    build:
      context: ./services/search-api
      dockerfile: Dockerfile
    container_name: medical-ai-search-api
    depends_on:
      elasticsearch:
        condition: service_healthy
      postgres:
        condition: service_healthy
    environment:
      - DEBUG=true
      - DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/search_db
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    ports:
      - "8012:8000"
    networks:
      - medical-ai-network
```

---

## 🔄 Event-Driven Workflow

### Kafka Topics Configuration
```python
# shared/events/topics.py
KAFKA_TOPICS = {
    'document_events': 'medical-ai-platform.document.events',
    'processing_events': 'medical-ai-platform.processing.events',
    'search_events': 'medical-ai-platform.search.events',
    'notification_events': 'medical-ai-platform.notification.events'
}

# Event flow:
# 1. Document uploaded → document.uploaded
# 2. Processing started → document.processing_started
# 3. Text extracted → document.text_extracted
# 4. NER completed → document.entities_extracted
# 5. Indexing started → document.indexing_started
# 6. Indexing completed → document.indexed
```

### Complete Event Workflow
```python
# Document Upload Flow
async def handle_document_upload(document_id: str):
    """Complete document processing pipeline"""
    
    # 1. Download from S3
    document_content = await s3_service.download_file(s3_key)
    
    # 2. Extract text
    extracted_data = await pdf_processor.extract_text(document_content)
    
    # 3. Perform medical NER
    entities = await medical_ner.extract_entities(extracted_data['text'])
    
    # 4. Update document record
    await update_document_processing_status(document_id, 'processed', extracted_data, entities)
    
    # 5. Index in Elasticsearch
    await elasticsearch_service.index_document({
        'document_id': document_id,
        'content': extracted_data['text'],
        'medical_entities': entities,
        'quality_score': extracted_data['quality_score']
    })
    
    # 6. Publish completion event
    await publish_event('document.indexed', {'document_id': document_id})
```

---

## 🧪 Testing Strategy

### Integration Tests
```python
# tests/test_integration.py
import pytest
import asyncio
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_complete_document_workflow():
    """Test end-to-end document processing"""
    
    # 1. Register user
    user_response = await client.post("/api/v1/auth/register", json=user_data)
    assert user_response.status_code == 201
    
    # 2. Login
    login_response = await client.post("/api/v1/auth/login", json=login_data)
    token = login_response.json()['access_token']
    
    # 3. Upload document
    with open("test_document.pdf", "rb") as f:
        upload_response = await client.post(
            "/api/v1/documents/upload",
            files={"file": f},
            headers={"Authorization": f"Bearer {token}"}
        )
    assert upload_response.status_code == 200
    document_id = upload_response.json()['document_id']
    
    # 4. Wait for processing (or use event listener)
    await asyncio.sleep(10)
    
    # 5. Search for document
    search_response = await client.get(
        f"/api/v1/search?q=test query",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert search_response.status_code == 200
    assert len(search_response.json()['results']) > 0
```

### Performance Tests
```python
# tests/test_performance.py
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

async def test_concurrent_uploads():
    """Test system under load"""
    
    async def upload_document(client, token, file_path):
        with open(file_path, "rb") as f:
            response = await client.post(
                "/api/v1/documents/upload",
                files={"file": f},
                headers={"Authorization": f"Bearer {token}"}
            )
        return response.status_code == 200
    
    # Test 10 concurrent uploads
    tasks = [upload_document(client, token, f"test_doc_{i}.pdf") for i in range(10)]
    
    start_time = time.time()
    results = await asyncio.gather(*tasks)
    end_time = time.time()
    
    assert all(results), "All uploads should succeed"
    assert end_time - start_time < 30, "Should complete within 30 seconds"
```

---

## 📊 Monitoring & Health Checks

### Service Health Endpoints
```python
# app/api/health.py
from fastapi import APIRouter
from app.services.storage import S3StorageService
from app.services.elasticsearch_client import ElasticsearchService

router = APIRouter()

@router.get("/health")
async def comprehensive_health_check():
    """Comprehensive health check for all dependencies"""
    
    health_status = {
        "service": "document-management",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "dependencies": {}
    }
    
    # Check database
    try:
        await db.execute("SELECT 1")
        health_status["dependencies"]["database"] = "healthy"
    except Exception:
        health_status["dependencies"]["database"] = "unhealthy"
        health_status["status"] = "unhealthy"
    
    # Check S3
    try:
        await s3_service.list_objects(limit=1)
        health_status["dependencies"]["s3"] = "healthy"
    except Exception:
        health_status["dependencies"]["s3"] = "unhealthy"
        health_status["status"] = "unhealthy"
    
    # Check Kafka
    try:
        await kafka_producer.ping()
        health_status["dependencies"]["kafka"] = "healthy"
    except Exception:
        health_status["dependencies"]["kafka"] = "unhealthy"
        health_status["status"] = "unhealthy"
    
    # Check Elasticsearch
    try:
        await elasticsearch_service.cluster_health()
        health_status["dependencies"]["elasticsearch"] = "healthy"
    except Exception:
        health_status["dependencies"]["elasticsearch"] = "unhealthy"
        health_status["status"] = "unhealthy"
    
    return health_status
```

---

## 🚀 Deployment Checklist

### Pre-deployment Validation
- [ ] All services start successfully
- [ ] Database migrations complete
- [ ] S3 bucket created and accessible
- [ ] Kafka topics created
- [ ] Elasticsearch indices created
- [ ] Kong Gateway routes configured
- [ ] Environment variables set
- [ ] SSL certificates configured (production)

### Service Dependencies
```
Auth Service (✅ Complete)
    ↓
Document Management Service
    ↓ (Kafka Events)
Content Processing Service
    ↓ (Kafka Events)
Search Indexing Service
    ↓
Search API Service
    ↓
Kong Gateway Integration
```

### Performance Targets
- **Document Upload**: < 5 seconds for 10MB files
- **Text Extraction**: < 30 seconds for 100-page PDFs
- **Search Response**: < 200ms for simple queries
- **Concurrent Users**: 100+ simultaneous users
- **Throughput**: 1000+ documents/hour processing

---

## 🎯 Success Criteria

### Technical Validation
- [ ] All 5 services running and healthy
- [ ] Complete document upload → processing → indexing → search workflow
- [ ] Authentication working across all services
- [ ] Event-driven communication functioning
- [ ] Search returning relevant results
- [ ] Performance targets met
- [ ] Integration tests passing
- [ ] Load tests passing

### Ready for Phase 3 (AI/ML Integration)
- [ ] Document content available for AI processing
- [ ] Search infrastructure ready for vector embeddings
- [ ] Event system ready for AI workflow triggers
- [ ] API endpoints ready for AI enhancement
- [ ] Monitoring and logging in place

---

## 📝 Implementation Order

### Week 1 (Days 1-5)
1. **Day 1**: Document Management Service setup and S3 integration
2. **Day 2**: Document upload API and database models
3. **Day 3**: Content Processing Service and PDF extraction
4. **Day 4**: Medical NER integration and text processing
5. **Day 5**: Kafka event integration between services

### Week 2 (Days 6-10)
6. **Day 6**: Search Indexing Service and Elasticsearch setup
7. **Day 7**: Search API Service and query processing
8. **Day 8**: Kong Gateway configuration and service routing
9. **Day 9**: Integration testing and bug fixes
10. **Day 10**: Performance optimization and monitoring setup

This implementation guide provides everything needed to complete Phase 2 and create a solid foundation for AI/ML integration in Phase 3.