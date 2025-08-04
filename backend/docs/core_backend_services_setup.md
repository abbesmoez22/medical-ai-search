# Core Backend Services Setup Guide
## Phase 2: Medical AI Search Platform Development

## Project Context
You are implementing **Phase 2: Core Backend Services** for the enterprise-grade medical AI search platform (OpenEvidence clone). This phase builds on the AWS infrastructure deployed in Phase 1 and focuses on developing production-ready microservices using modern backend technologies.

## Your Role
Act as a senior backend engineer implementing microservices architecture with event-driven patterns. Focus on enterprise-grade patterns, scalability, and technologies that demonstrate mastery for FAANG-level interviews.

## Phase 2 Goals (Weeks 3-4)
Implement core backend services using FastAPI, Kafka, and microservices patterns that showcase distributed systems expertise and modern backend development practices.

---

## Architecture Overview

### Microservices Design
- **Event-Driven Architecture**: Kafka-based communication between services
- **API Gateway Pattern**: Kong for request routing and rate limiting
- **Database per Service**: Each microservice owns its data
- **CQRS Pattern**: Command Query Responsibility Segregation where applicable
- **Circuit Breaker Pattern**: Resilience and fault tolerance

### Service Communication Flow
```
Frontend → Kong Gateway → Service Mesh → Microservices → Kafka → Event Processing
```

---

## Technology Stack for Phase 2

### Core Backend Technologies
- **Language**: Python 3.11+ with FastAPI
- **Message Queue**: Apache Kafka with Confluent Platform
- **API Gateway**: Kong Gateway with plugins
- **Databases**: 
  - PostgreSQL (already deployed)
  - Redis (already deployed)
- **Authentication**: JWT with OAuth2 flows
- **Documentation**: OpenAPI/Swagger with automatic generation

### Development Tools
- **Container Runtime**: Docker with multi-stage builds
- **Orchestration**: Kubernetes (EKS already deployed)
- **Package Management**: Poetry for Python dependencies
- **Code Quality**: Black, isort, flake8, mypy
- **Testing**: pytest with coverage reporting
- **Local Development**: Docker Compose for service orchestration

---

## Core Services Architecture

### 1. User Authentication Service
**Purpose**: Handle user registration, authentication, and authorization
**Technology**: FastAPI + JWT + PostgreSQL + Redis

**Responsibilities:**
- User registration and email verification
- JWT token generation and validation
- Role-based access control (RBAC)
- Session management with Redis
- Password reset workflows
- OAuth2 integration (Google, GitHub)

**Database Schema:**
```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role VARCHAR(50) DEFAULT 'user',
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- User sessions
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token_jti VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Key Features:**
- JWT with refresh token rotation
- Rate limiting on authentication endpoints
- Audit logging for security events
- Multi-factor authentication support
- Role hierarchy: admin, doctor, researcher, student

### 2. Document Management Service
**Purpose**: Handle medical document upload, processing, and metadata management
**Technology**: FastAPI + PostgreSQL + S3 + Kafka

**Responsibilities:**
- Document upload to S3 with validation
- Metadata extraction and storage
- Document versioning and history
- Access control and permissions
- Document lifecycle management
- Publish events for downstream processing

**Database Schema:**
```sql
-- Documents table
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    authors TEXT[],
    journal VARCHAR(255),
    publication_date DATE,
    doi VARCHAR(255) UNIQUE,
    pmid VARCHAR(50),
    document_type VARCHAR(100), -- research_paper, clinical_trial, review, etc.
    specialty VARCHAR(100),     -- cardiology, neurology, etc.
    s3_key VARCHAR(500) NOT NULL,
    file_size BIGINT,
    mime_type VARCHAR(100),
    processing_status VARCHAR(50) DEFAULT 'pending',
    uploaded_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Document metadata
CREATE TABLE document_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    key VARCHAR(255) NOT NULL,
    value TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Kafka Events:**
- `document.uploaded`: New document ready for processing
- `document.processed`: Document processing completed
- `document.indexed`: Document indexed for search
- `document.failed`: Processing failed with error details

### 3. Content Processing Service
**Purpose**: Extract and process content from medical documents
**Technology**: FastAPI + Kafka + S3 + Background Tasks

**Responsibilities:**
- PDF text extraction using multiple parsers
- Content cleaning and normalization
- Medical entity recognition (NER)
- Citation parsing and linking
- Abstract and summary generation
- Quality scoring and validation

**Processing Pipeline:**
1. **Document Intake**: Receive document from S3
2. **Text Extraction**: Multiple extraction strategies
3. **Content Analysis**: Medical NER, topic classification
4. **Quality Assessment**: Completeness, accuracy scoring
5. **Metadata Enrichment**: Citations, references, keywords
6. **Event Publishing**: Notify downstream services

**Key Libraries:**
- `pdfplumber` and `PyPDF2` for PDF parsing
- `spaCy` with medical models for NER
- `transformers` for content classification
- `celery` for background task processing

### 4. Search Indexing Service
**Purpose**: Index processed documents for full-text and semantic search
**Technology**: FastAPI + Elasticsearch + Kafka + Vector Database

**Responsibilities:**
- Elasticsearch index management
- Document indexing with medical-specific analyzers
- Vector embedding generation
- Search index optimization
- Real-time index updates
- Search analytics and logging

**Elasticsearch Mapping:**
```json
{
  "mappings": {
    "properties": {
      "title": {
        "type": "text",
        "analyzer": "medical_analyzer",
        "fields": {
          "keyword": {"type": "keyword"}
        }
      },
      "abstract": {
        "type": "text",
        "analyzer": "medical_analyzer"
      },
      "content": {
        "type": "text",
        "analyzer": "medical_analyzer"
      },
      "authors": {
        "type": "keyword"
      },
      "journal": {
        "type": "keyword"
      },
      "publication_date": {
        "type": "date"
      },
      "medical_entities": {
        "type": "nested",
        "properties": {
          "entity": {"type": "keyword"},
          "type": {"type": "keyword"},
          "confidence": {"type": "float"}
        }
      },
      "embedding": {
        "type": "dense_vector",
        "dims": 1536
      }
    }
  }
}
```

### 5. Search API Service
**Purpose**: Provide unified search interface with multiple search strategies
**Technology**: FastAPI + Elasticsearch + Vector DB + Redis

**Responsibilities:**
- Multi-modal search (text, semantic, hybrid)
- Search result ranking and scoring
- Faceted search and filtering
- Search suggestions and autocomplete
- Search analytics and personalization
- Result caching and optimization

**Search Types:**
- **Full-text Search**: Traditional keyword-based search
- **Semantic Search**: Vector similarity search
- **Hybrid Search**: Combination of both approaches
- **Faceted Search**: Filter by date, journal, specialty
- **Similar Documents**: Find related papers

### 6. Notification Service
**Purpose**: Handle all system notifications and communications
**Technology**: FastAPI + Kafka + Redis + Email/SMS providers

**Responsibilities:**
- Email notifications (verification, alerts)
- In-app notifications
- Push notifications for mobile
- Notification preferences management
- Template management
- Delivery tracking and analytics

---

## Kafka Event Architecture

### Topic Design Strategy
```
medical-ai-platform/
├── user.events/           # User lifecycle events
├── document.events/       # Document processing events
├── search.events/         # Search analytics events
├── notification.events/   # Notification requests
└── system.events/         # System-wide events
```

### Event Schema Design
```python
# Base event schema
class BaseEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source_service: str
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    
# Document processing event
class DocumentProcessedEvent(BaseEvent):
    event_type: str = "document.processed"
    document_id: str
    processing_status: str
    metadata: Dict[str, Any]
    s3_location: str
```

### Producer/Consumer Patterns
- **Transactional Outbox**: Ensure message delivery
- **Idempotent Consumers**: Handle duplicate messages
- **Dead Letter Queues**: Handle failed message processing
- **Event Sourcing**: Store events as source of truth

---

## API Gateway Configuration

### Kong Gateway Setup
**Purpose**: Centralized API management, authentication, and rate limiting

**Key Plugins:**
- **Rate Limiting**: Protect against abuse
- **JWT Authentication**: Validate tokens
- **CORS**: Cross-origin request handling
- **Request/Response Logging**: Audit trail
- **Circuit Breaker**: Fault tolerance

**Route Configuration:**
```yaml
# Kong declarative configuration
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
      - name: rate-limiting
        config:
          minute: 200

routes:
  - name: auth-routes
    service: auth-service
    paths:
      - /api/v1/auth
  
  - name: document-routes
    service: document-service
    paths:
      - /api/v1/documents
```

---

## Development Environment Setup

### Local Development Stack
```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  # Message Queue
  zookeeper:
    image: confluentinc/cp-zookeeper:7.4.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000

  kafka:
    image: confluentinc/cp-kafka:7.4.0
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1

  # Search Engine
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    ports:
      - "9200:9200"
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"

  # API Gateway
  kong:
    image: kong:3.4
    ports:
      - "8000:8000"
      - "8001:8001"
    environment:
      KONG_DATABASE: "off"
      KONG_DECLARATIVE_CONFIG: /kong/kong.yml
    volumes:
      - ./kong.yml:/kong/kong.yml

  # Services
  auth-service:
    build: ./services/auth
    ports:
      - "8001:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/auth_db
      - REDIS_URL=redis://redis:6379
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092

  document-service:
    build: ./services/document
    ports:
      - "8002:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/document_db
      - S3_BUCKET=medical-documents-dev
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
```

### Project Structure
```
backend/
├── services/
│   ├── auth/                    # Authentication service
│   │   ├── app/
│   │   │   ├── api/            # API routes
│   │   │   ├── core/           # Core business logic
│   │   │   ├── db/             # Database models
│   │   │   ├── schemas/        # Pydantic models
│   │   │   └── main.py         # FastAPI app
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   │
│   ├── document/               # Document management
│   ├── processing/             # Content processing
│   ├── search/                 # Search API
│   └── notification/           # Notifications
│
├── shared/                     # Shared libraries
│   ├── events/                 # Kafka event schemas
│   ├── auth/                   # Authentication utilities
│   ├── database/               # Database utilities
│   └── monitoring/             # Observability
│
├── infrastructure/             # Local infrastructure
│   ├── docker-compose.dev.yml
│   ├── kong.yml
│   └── elasticsearch/
│
├── scripts/                    # Development scripts
│   ├── setup-dev.sh
│   ├── run-tests.sh
│   └── deploy-local.sh
│
└── docs/                       # Documentation
    ├── api/                    # API documentation
    ├── architecture/           # System design docs
    └── deployment/             # Deployment guides
```

---

## Implementation Roadmap

### Week 3: Core Services Foundation

#### Day 1-2: Project Setup & Authentication Service
**Tasks:**
1. Set up project structure and development environment
2. Configure Docker Compose for local development
3. Implement User Authentication Service
   - User registration and login endpoints
   - JWT token generation and validation
   - Password hashing and security
   - Basic RBAC implementation

**Deliverables:**
- Working authentication service with JWT
- User registration/login API endpoints
- Database migrations for user management
- Basic test coverage (>80%)

#### Day 3-4: Document Management Service
**Tasks:**
1. Implement Document Management Service
   - File upload to S3 with validation
   - Document metadata storage
   - Access control and permissions
   - Document versioning
2. Set up Kafka integration
   - Event publishing for document operations
   - Basic producer/consumer setup

**Deliverables:**
- Document upload and management API
- S3 integration with proper error handling
- Kafka event publishing
- Document metadata storage

#### Day 5: API Gateway & Service Integration
**Tasks:**
1. Configure Kong Gateway
   - Route configuration for services
   - Authentication plugin setup
   - Rate limiting configuration
2. Service-to-service communication
   - JWT validation across services
   - Error handling and circuit breakers

**Deliverables:**
- Kong Gateway configuration
- Integrated authentication across services
- API documentation with OpenAPI

### Week 4: Processing & Search Services

#### Day 1-2: Content Processing Service
**Tasks:**
1. Implement Content Processing Service
   - PDF text extraction pipeline
   - Medical entity recognition
   - Content quality assessment
   - Background task processing
2. Advanced Kafka integration
   - Event-driven processing pipeline
   - Error handling and retry logic

**Deliverables:**
- Content extraction and processing pipeline
- Medical NER integration
- Kafka-based event processing
- Background task queue

#### Day 3-4: Search Infrastructure
**Tasks:**
1. Set up Elasticsearch cluster
   - Medical-specific analyzers
   - Index templates and mappings
   - Search optimization
2. Implement Search Indexing Service
   - Document indexing pipeline
   - Real-time index updates
   - Search analytics

**Deliverables:**
- Elasticsearch cluster configuration
- Document indexing pipeline
- Search index management
- Basic search functionality

#### Day 5: Search API & Integration
**Tasks:**
1. Implement Search API Service
   - Multi-modal search endpoints
   - Result ranking and filtering
   - Search suggestions
2. End-to-end integration testing
   - Complete document workflow
   - Search functionality testing
   - Performance optimization

**Deliverables:**
- Complete search API
- End-to-end document processing
- Performance benchmarks
- Integration test suite

---

## Quality Assurance & Testing

### Testing Strategy
- **Unit Tests**: Each service >90% coverage
- **Integration Tests**: Service-to-service communication
- **Contract Tests**: API contract validation
- **Load Tests**: Performance under load
- **Security Tests**: Authentication and authorization

### Code Quality Standards
```python
# pyproject.toml example
[tool.black]
line-length = 88
target-version = ['py311']

[tool.isort]
profile = "black"
multi_line_output = 3

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
minversion = "6.0"
addopts = "-ra -q --cov=app --cov-report=html"
testpaths = ["tests"]
```

### Performance Benchmarks
- **API Response Time**: <100ms for 95% of requests
- **Document Processing**: <30 seconds per document
- **Search Latency**: <200ms for complex queries
- **Throughput**: Handle 1000+ concurrent requests
- **Memory Usage**: <512MB per service container

---

## Security Implementation

### Authentication & Authorization
- **JWT Tokens**: Short-lived access tokens with refresh rotation
- **Role-Based Access Control**: Granular permissions
- **API Key Management**: Service-to-service authentication
- **Rate Limiting**: Prevent abuse and DoS attacks
- **Input Validation**: Comprehensive request validation

### Data Protection
- **Encryption in Transit**: TLS for all communications
- **Encryption at Rest**: Database and S3 encryption
- **PII Protection**: Medical data handling compliance
- **Audit Logging**: Complete audit trail
- **Secret Management**: Kubernetes secrets integration

---

## Monitoring & Observability

### Logging Strategy
```python
# Structured logging example
import structlog

logger = structlog.get_logger()

# Service logs
logger.info(
    "Document processed",
    document_id=doc_id,
    processing_time=elapsed,
    user_id=user_id,
    service="document-processing"
)
```

### Metrics Collection
- **Application Metrics**: Custom business metrics
- **Infrastructure Metrics**: CPU, memory, network
- **API Metrics**: Request rate, latency, errors
- **Database Metrics**: Query performance, connections
- **Kafka Metrics**: Message throughput, lag

### Health Checks
```python
# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": app.version,
        "dependencies": {
            "database": await check_database(),
            "kafka": await check_kafka(),
            "redis": await check_redis()
        }
    }
```

---

## Deployment Strategy

### Kubernetes Deployment
```yaml
# Example deployment manifest
apiVersion: apps/v1
kind: Deployment
metadata:
  name: auth-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: auth-service
  template:
    metadata:
      labels:
        app: auth-service
    spec:
      containers:
      - name: auth-service
        image: medical-ai/auth-service:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: auth-db-secret
              key: url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
```

### CI/CD Integration
- **GitHub Actions**: Automated testing and deployment
- **Container Registry**: ECR for container images
- **ArgoCD**: GitOps deployment to Kubernetes
- **Environment Promotion**: Dev → Staging → Production

---

## Success Criteria

### Technical Validation
- [ ] All services deploy successfully to Kubernetes
- [ ] Authentication works across all services
- [ ] Document upload and processing pipeline functional
- [ ] Search API returns relevant results
- [ ] Kafka events flow correctly between services
- [ ] API Gateway routes requests properly
- [ ] All services have >90% test coverage
- [ ] Performance benchmarks met

### Interview Readiness Demonstration
- [ ] Microservices architecture with proper separation
- [ ] Event-driven communication with Kafka
- [ ] API Gateway pattern implementation
- [ ] Database per service pattern
- [ ] Circuit breaker and resilience patterns
- [ ] Comprehensive testing strategy
- [ ] Security best practices
- [ ] Monitoring and observability

### Business Value
- [ ] Users can register and authenticate
- [ ] Documents can be uploaded and processed
- [ ] Basic search functionality works
- [ ] System handles concurrent users
- [ ] Error handling and recovery works
- [ ] Audit logging captures all actions

---

## Next Steps (Phase 3 Preview)

After completing Phase 2, you'll be ready for **Phase 3: AI/ML Integration** which includes:
- RAG (Retrieval-Augmented Generation) implementation
- Vector database integration
- LLM API integration
- Model serving infrastructure
- ML pipeline automation

This phase builds the solid backend foundation needed for the advanced AI features that will make your platform truly competitive and interview-worthy.

---

## Enterprise Patterns Demonstrated

### Distributed Systems
- Event-driven architecture with Kafka
- Microservices with proper boundaries
- API Gateway pattern
- Circuit breaker implementation
- Distributed logging and tracing

### Backend Engineering
- RESTful API design with OpenAPI
- Database optimization and indexing
- Caching strategies with Redis
- Background job processing
- Security and authentication

### DevOps & Infrastructure
- Containerized microservices
- Kubernetes orchestration
- Infrastructure as Code
- CI/CD pipeline automation
- Monitoring and alerting

This comprehensive backend implementation will demonstrate production-ready engineering skills and provide concrete examples for system design interviews at top-tier companies.