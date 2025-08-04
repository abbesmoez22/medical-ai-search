# Phase 2 Deployment Checklist
## Complete Validation and Testing Guide

---

## 🎯 Pre-Implementation Checklist

### Infrastructure Requirements
- [ ] **Docker Desktop** running with at least 8GB RAM allocated
- [ ] **Ports Available**: 8010-8014, 5433, 6380, 9095, 9201, 8100-8102
- [ ] **AWS Account** with S3 access (for document storage)
- [ ] **Development Tools**: Python 3.11+, Git, curl/Postman

### Current Status Verification
- [x] **Authentication Service** running on port 8010
- [x] **PostgreSQL** running on port 5433
- [x] **Redis** running on port 6380
- [x] **Kafka** running on port 9095
- [x] **Elasticsearch** running on port 9201
- [x] **Kong Gateway** infrastructure ready

---

## 📋 Implementation Validation Checklist

### Phase 2A: Document Management Service
#### Service Setup
- [ ] **Project Structure** created correctly
- [ ] **Dependencies** installed (requirements.txt)
- [ ] **Database Models** implemented and migrated
- [ ] **S3 Integration** configured and tested
- [ ] **Environment Variables** properly set

#### API Endpoints Testing
```bash
# Test document upload
curl -X POST "http://localhost:8011/api/v1/documents/upload" \
     -H "Authorization: Bearer $ACCESS_TOKEN" \
     -F "file=@test_document.pdf" \
     -F "title=Test Document"

# Expected: 200 OK with document_id
```

- [ ] **Document Upload** works (PDF files up to 50MB)
- [ ] **Document Metadata** stored correctly in database
- [ ] **S3 Storage** functioning (files uploaded to bucket)
- [ ] **File Validation** working (type, size limits)
- [ ] **Access Control** enforced (user can only see own documents)

#### Database Validation
```sql
-- Check document was created
SELECT id, filename, title, processing_status, uploaded_by 
FROM documents 
ORDER BY created_at DESC 
LIMIT 5;

-- Expected: New document record with correct metadata
```

- [ ] **Document Records** created in PostgreSQL
- [ ] **File Metadata** stored correctly
- [ ] **User Association** working
- [ ] **Timestamps** populated

#### Event Publishing
- [ ] **Kafka Events** published on document upload
- [ ] **Event Schema** matches specification
- [ ] **Correlation IDs** included in events

### Phase 2B: Content Processing Service
#### Service Setup
- [ ] **Project Structure** created
- [ ] **PDF Processing** libraries installed
- [ ] **Medical NER** model downloaded and configured
- [ ] **Database Models** for processing jobs

#### Processing Pipeline Testing
```bash
# Trigger document processing
curl -X POST "http://localhost:8013/api/v1/processing/process-document" \
     -H "Authorization: Bearer $ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "document_id": "your-document-id",
       "s3_bucket": "medical-ai-documents",
       "s3_key": "documents/user/file.pdf"
     }'

# Expected: 200 OK with processing_id
```

- [ ] **PDF Text Extraction** working correctly
- [ ] **Medical Entity Recognition** identifying medical terms
- [ ] **Quality Scoring** calculating reasonable scores
- [ ] **Processing Status** updating correctly
- [ ] **Error Handling** for corrupted/invalid files

#### Processing Results Validation
```bash
# Check processing results
curl -X GET "http://localhost:8013/api/v1/processing/$PROCESSING_ID/content" \
     -H "Authorization: Bearer $ACCESS_TOKEN"

# Expected: Extracted text, medical entities, quality scores
```

- [ ] **Extracted Text** readable and complete
- [ ] **Medical Entities** properly categorized
- [ ] **Document Structure** identified (abstract, sections)
- [ ] **Quality Metrics** calculated

### Phase 2C: Search Infrastructure
#### Elasticsearch Setup
- [ ] **Index Created** with medical analyzers
- [ ] **Medical Synonyms** configured
- [ ] **Index Mappings** match specification
- [ ] **Index Health** showing green status

#### Search Indexing Service
```bash
# Test document indexing
curl -X POST "http://localhost:8014/api/v1/indexing/index-document" \
     -H "Content-Type: application/json" \
     -d '{
       "document_id": "your-document-id",
       "document_data": {
         "title": "Test Document",
         "content": "Medical research content...",
         "medical_entities": [...]
       }
     }'

# Expected: 200 OK with indexing confirmation
```

- [ ] **Document Indexing** working
- [ ] **Medical Entities** indexed as nested objects
- [ ] **Text Analysis** using medical analyzers
- [ ] **Index Updates** working for document changes

#### Search API Service
```bash
# Test basic search
curl -X GET "http://localhost:8012/api/v1/search?q=diabetes treatment&limit=10" \
     -H "Authorization: Bearer $ACCESS_TOKEN"

# Expected: Relevant search results with highlights
```

- [ ] **Basic Text Search** returning results
- [ ] **Medical Synonym** expansion working
- [ ] **Search Highlights** showing matched terms
- [ ] **Faceted Search** providing filter options
- [ ] **Search Suggestions** working for autocomplete

### Phase 2D: API Gateway Integration
#### Kong Configuration
- [ ] **Services Registered** in Kong
- [ ] **Routes Configured** for all endpoints
- [ ] **JWT Authentication** working across services
- [ ] **Rate Limiting** configured and enforced

#### Gateway Testing
```bash
# Test through gateway
curl -X GET "http://localhost:8100/api/v1/search?q=test" \
     -H "Authorization: Bearer $ACCESS_TOKEN"

# Expected: Same results as direct service call
```

- [ ] **Request Routing** working correctly
- [ ] **Authentication Propagation** between services
- [ ] **Rate Limiting** enforced
- [ ] **CORS Headers** configured
- [ ] **Error Handling** consistent across services

---

## 🔄 End-to-End Workflow Testing

### Complete Document Pipeline Test
```bash
#!/bin/bash
# Complete workflow test script

echo "1. User Registration and Login"
USER_RESPONSE=$(curl -s -X POST "http://localhost:8100/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "TestPass123!",
    "role": "user"
  }')

LOGIN_RESPONSE=$(curl -s -X POST "http://localhost:8100/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!"
  }')

ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')

echo "2. Document Upload"
UPLOAD_RESPONSE=$(curl -s -X POST "http://localhost:8100/api/v1/documents/upload" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@test_medical_paper.pdf" \
  -F "title=Test Medical Research")

DOCUMENT_ID=$(echo $UPLOAD_RESPONSE | jq -r '.document_id')

echo "3. Wait for Processing (30 seconds)"
sleep 30

echo "4. Check Processing Status"
curl -s -X GET "http://localhost:8100/api/v1/documents/$DOCUMENT_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.processing_status'

echo "5. Search for Document"
SEARCH_RESPONSE=$(curl -s -X GET "http://localhost:8100/api/v1/search?q=medical research" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

echo "Search Results Count:" $(echo $SEARCH_RESPONSE | jq '.total_hits')

echo "6. Workflow Complete"
```

### Workflow Validation Checklist
- [ ] **User Registration** successful
- [ ] **User Login** returns valid JWT token
- [ ] **Document Upload** through gateway successful
- [ ] **Processing Pipeline** completes within 60 seconds
- [ ] **Document Status** updates to "completed"
- [ ] **Search Indexing** completes automatically
- [ ] **Search Results** include uploaded document
- [ ] **Document Download** works through gateway

---

## 🧪 Performance Testing

### Load Testing Setup
```bash
# Install Apache Bench (ab) for load testing
# macOS: brew install httpd
# Ubuntu: sudo apt-get install apache2-utils

# Test concurrent uploads (adjust -n and -c based on your system)
ab -n 10 -c 2 -T 'multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW' \
   -H "Authorization: Bearer $ACCESS_TOKEN" \
   -p upload_data.txt \
   http://localhost:8100/api/v1/documents/upload

# Test search performance
ab -n 100 -c 10 -H "Authorization: Bearer $ACCESS_TOKEN" \
   "http://localhost:8100/api/v1/search?q=diabetes"
```

### Performance Benchmarks
- [ ] **Document Upload**: < 5 seconds for 10MB files
- [ ] **Text Extraction**: < 30 seconds for 100-page PDFs
- [ ] **Medical NER**: < 10 seconds for 5000-word documents
- [ ] **Search Response**: < 200ms for simple queries
- [ ] **Indexing**: < 15 seconds for processed documents
- [ ] **Concurrent Users**: 10+ simultaneous without errors

### Resource Monitoring
```bash
# Monitor Docker container resources
docker stats

# Check service health
curl http://localhost:8010/health
curl http://localhost:8011/health
curl http://localhost:8012/health
curl http://localhost:8013/health
curl http://localhost:8014/health
```

- [ ] **Memory Usage**: < 4GB total for all services
- [ ] **CPU Usage**: < 80% during normal operations
- [ ] **Disk Usage**: Reasonable growth with document storage
- [ ] **Network**: No connection timeouts or errors

---

## 🔍 Error Handling Validation

### Error Scenarios Testing
```bash
# Test file size limit
curl -X POST "http://localhost:8100/api/v1/documents/upload" \
     -H "Authorization: Bearer $ACCESS_TOKEN" \
     -F "file=@large_file_over_50mb.pdf"
# Expected: 400 Bad Request - File too large

# Test invalid file type
curl -X POST "http://localhost:8100/api/v1/documents/upload" \
     -H "Authorization: Bearer $ACCESS_TOKEN" \
     -F "file=@test_image.jpg"
# Expected: 400 Bad Request - Invalid file type

# Test unauthorized access
curl -X GET "http://localhost:8100/api/v1/documents/123"
# Expected: 401 Unauthorized

# Test invalid search query
curl -X GET "http://localhost:8100/api/v1/search?q=" \
     -H "Authorization: Bearer $ACCESS_TOKEN"
# Expected: 400 Bad Request - Empty query
```

### Error Handling Checklist
- [ ] **File Size Limits** enforced with proper error messages
- [ ] **File Type Validation** working correctly
- [ ] **Authentication Errors** return 401 with clear messages
- [ ] **Authorization Errors** return 403 for forbidden resources
- [ ] **Validation Errors** return 400 with field-specific messages
- [ ] **Service Unavailable** returns 503 when dependencies down
- [ ] **Rate Limiting** returns 429 when limits exceeded

---

## 📊 Data Validation

### Database Consistency Checks
```sql
-- Check document processing pipeline integrity
SELECT 
    d.id,
    d.processing_status,
    d.extraction_status,
    d.indexing_status,
    pj.status as processing_job_status
FROM documents d
LEFT JOIN processing_jobs pj ON d.id = pj.document_id
WHERE d.created_at > NOW() - INTERVAL '1 hour';

-- Check event publishing
SELECT event_type, COUNT(*) 
FROM kafka_events 
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY event_type;
```

### Data Integrity Checklist
- [ ] **Document Records** consistent across services
- [ ] **Processing Status** accurately reflects pipeline state
- [ ] **Search Index** contains all processed documents
- [ ] **Event Publishing** working for all major operations
- [ ] **User Permissions** properly enforced
- [ ] **File Storage** S3 objects match database records

---

## 🚀 Production Readiness Checklist

### Security Validation
- [ ] **JWT Tokens** properly validated across services
- [ ] **Password Hashing** using bcrypt with proper salt
- [ ] **Input Sanitization** preventing injection attacks
- [ ] **File Upload Security** preventing malicious files
- [ ] **API Rate Limiting** protecting against abuse
- [ ] **CORS Configuration** properly restricting origins

### Monitoring Setup
- [ ] **Health Check Endpoints** responding correctly
- [ ] **Structured Logging** enabled for all services
- [ ] **Error Tracking** capturing and logging exceptions
- [ ] **Performance Metrics** being collected
- [ ] **Business Metrics** tracking document processing

### Documentation
- [ ] **API Documentation** auto-generated and accessible
- [ ] **Service Dependencies** clearly documented
- [ ] **Environment Variables** documented with examples
- [ ] **Deployment Instructions** complete and tested
- [ ] **Troubleshooting Guide** available

---

## ✅ Phase 2 Completion Criteria

### Technical Requirements
- [ ] **All 5 Services** running and healthy
- [ ] **Complete Pipeline** from upload to search working
- [ ] **Authentication** working across all services
- [ ] **Event-Driven Communication** functioning
- [ ] **Search Results** relevant and fast
- [ ] **Performance Targets** met
- [ ] **Error Handling** comprehensive
- [ ] **Integration Tests** passing

### Business Requirements
- [ ] **Users** can register and authenticate
- [ ] **Documents** can be uploaded and processed
- [ ] **Search** returns relevant medical content
- [ ] **System** handles multiple concurrent users
- [ ] **Data** is properly secured and isolated
- [ ] **Errors** are handled gracefully

### Phase 3 Readiness
- [ ] **Document Content** available for AI processing
- [ ] **Search Infrastructure** ready for vector embeddings
- [ ] **Event System** ready for AI workflow triggers
- [ ] **API Endpoints** ready for AI enhancement
- [ ] **Performance** baseline established

---

## 🔧 Troubleshooting Guide

### Common Issues and Solutions

#### Service Won't Start
```bash
# Check logs
docker-compose -f docker-compose.dev.yml logs service-name

# Check port conflicts
lsof -i :8011

# Restart service
docker-compose -f docker-compose.dev.yml restart service-name
```

#### Database Connection Issues
```bash
# Test database connectivity
docker-compose -f docker-compose.dev.yml exec postgres psql -U postgres -d document_db -c "SELECT 1;"

# Check database exists
docker-compose -f docker-compose.dev.yml exec postgres psql -U postgres -l
```

#### S3 Upload Failures
```bash
# Test AWS credentials
aws s3 ls s3://your-bucket-name

# Check bucket permissions
aws s3api get-bucket-policy --bucket your-bucket-name
```

#### Elasticsearch Issues
```bash
# Check cluster health
curl http://localhost:9201/_cluster/health

# Check indices
curl http://localhost:9201/_cat/indices

# Recreate index
curl -X DELETE http://localhost:9201/medical_documents
curl -X PUT http://localhost:9201/medical_documents -d @index_mapping.json
```

#### Kafka Connection Problems
```bash
# List topics
docker-compose -f docker-compose.dev.yml exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Check consumer groups
docker-compose -f docker-compose.dev.yml exec kafka kafka-consumer-groups --list --bootstrap-server localhost:9092
```

### Performance Issues
- **Slow Uploads**: Check S3 connection and file size limits
- **Slow Processing**: Monitor CPU/memory usage, consider async processing
- **Slow Search**: Check Elasticsearch performance, consider index optimization
- **High Memory Usage**: Monitor for memory leaks, restart services if needed

This comprehensive checklist ensures that Phase 2 is implemented correctly and ready for Phase 3 AI/ML integration.