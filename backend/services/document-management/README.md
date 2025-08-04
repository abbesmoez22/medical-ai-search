# 📄 Document Management Service - Complete Learning Guide

Welcome! This guide will teach you everything about handling medical documents in our platform. Think of this service as a **smart filing system** for hospitals that can store, organize, and process medical documents safely.

## 📖 What Is This Service?

Imagine a hospital's medical records room, but **super-powered**:

### Traditional Filing System:
- 📁 Paper files in cabinets
- 🔍 Manual searching through folders  
- 📋 Handwritten labels and notes
- 🚫 Limited access control
- 📉 Easy to lose or damage

### Our Digital System:
- ☁️ **Secure cloud storage** (files stored safely online)
- 🔍 **Instant search** through thousands of documents
- 🤖 **Automatic processing** (extracts text, finds medical terms)
- 🔐 **Smart permissions** (only authorized people can access)
- 📊 **Quality checking** (ensures documents are readable)
- 🔄 **Version control** (keeps track of document changes)

## 🎯 Real-World Problems We Solve

### Hospital Scenario - Before Our Service:
Dr. Smith wants to upload a research paper about heart surgery:
- ❌ Uploads to shared folder (anyone can access)
- ❌ No way to search inside the document
- ❌ File gets corrupted, no backup
- ❌ Can't tell if document is high quality
- ❌ Other doctors can't find it easily

### Hospital Scenario - With Our Service:
Dr. Smith uploads the same research paper:
- ✅ **Secure upload**: Only authorized users can access
- ✅ **Automatic processing**: System reads the document and extracts key information
- ✅ **Safe storage**: Multiple backups, never lost
- ✅ **Quality check**: System verifies document is readable and complete
- ✅ **Smart search**: Other doctors can find it by searching "heart surgery"
- ✅ **Access control**: Only doctors and researchers can view it

## 🏗️ How It Works (Simple Architecture)

```
👤 Doctor → 📄 Upload Document → 🔐 Security Check → ☁️ Safe Storage → 🤖 Processing → 🔍 Searchable
```

### Step-by-Step Process:

#### 1. Document Upload
```
Doctor uploads "Heart Surgery Research.pdf"
↓
System checks: "Is this really a PDF? Is it safe? Is user authorized?"
↓
If OK: Continue to storage
If NOT OK: Reject with helpful error message
```

#### 2. Secure Storage
```
Original file → Amazon S3 (like a super-secure digital vault)
↓
File gets unique ID: "doc_12345_heart_surgery.pdf"
↓
Multiple copies stored in different locations (backup safety)
```

#### 3. Automatic Processing
```
PDF file → Text extraction → "This document discusses cardiac procedures..."
↓
Find medical terms → "heart", "surgery", "cardiac", "procedure"
↓
Quality check → "Document is 95% readable, high quality"
↓
Create searchable index → Now doctors can find it by searching
```

#### 4. Access Control
```
User requests document → Check permissions → "Is user allowed to see this?"
↓
If YES: Provide secure download link
If NO: "Access denied - insufficient permissions"
```

## 🚀 Getting Started (Step by Step)

### What You Need:
1. **Docker** - Container system (like a box that holds our service)
2. **Database** - PostgreSQL to store document information
3. **Storage** - S3 or compatible service for files
4. **Authentication** - Auth service must be running first

### Quick Start (10 Minutes):

#### Step 1: Start the Services
```bash
# Go to backend folder
cd backend

# Start required services (database, storage, etc.)
docker-compose -f docker-compose.dev.yml up -d postgres redis

# Start document service
docker-compose -f docker-compose.dev.yml up -d document-service

# Wait for services to start
sleep 30

# Check if working
curl http://localhost:8011/health
```

#### Step 2: Get Authentication Token
```bash
# First, create a user account (if you haven't)
curl -X POST http://localhost:8010/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "doctor@hospital.com",
    "username": "dr_smith", 
    "password": "SecurePass123!",
    "role": "doctor"
  }'

# Login to get access token
curl -X POST http://localhost:8010/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "doctor@hospital.com",
    "password": "SecurePass123!"
  }'
```

Save the `access_token` from the response - you'll need it!

#### Step 3: Upload Your First Document
```bash
# Replace YOUR_TOKEN with the token from step 2
curl -X POST http://localhost:8011/api/v1/documents/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/your/document.pdf" \
  -F "title=My First Medical Document" \
  -F "authors=Dr. Smith" \
  -F "document_type=research_paper"
```

🎉 **Success!** Your document is now safely stored and being processed!

## 📚 Understanding the API (Learn by Examples)

### 1. Document Upload (The Most Important Feature)

**What it does**: Safely uploads and stores medical documents
**Who can use it**: Authenticated users with upload permissions

```bash
POST /api/v1/documents/upload
```

**Real Example - Uploading a Research Paper**:
```bash
curl -X POST http://localhost:8011/api/v1/documents/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@research_paper.pdf" \
  -F "title=COVID-19 Treatment Effectiveness" \
  -F "authors=Dr. Johnson, Dr. Lee" \
  -F "abstract=This study examines the effectiveness of various COVID-19 treatments..." \
  -F "keywords=COVID-19,treatment,effectiveness,clinical trial" \
  -F "document_type=research_paper" \
  -F "visibility=public"
```

**What happens behind the scenes**:
1. **Security Check**: "Is the user authenticated? Do they have upload permission?"
2. **File Validation**: "Is this really a PDF? Is it under size limit? Is it safe?"
3. **Storage**: "Upload to secure S3 bucket with encryption"
4. **Processing**: "Extract text, find medical terms, check quality"
5. **Database**: "Save document information for future searches"
6. **Events**: "Tell other services a new document is available"

### 2. Viewing Your Documents

**What it does**: Shows list of documents you can access
**Who can use it**: Any authenticated user

```bash
GET /api/v1/documents
```

**Example**:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8011/api/v1/documents?page=1&size=10&type=research_paper"
```

**Response (what you get back)**:
```json
{
  "documents": [
    {
      "id": "doc_12345",
      "title": "COVID-19 Treatment Effectiveness", 
      "authors": "Dr. Johnson, Dr. Lee",
      "document_type": "research_paper",
      "file_size": 2048000,
      "processing_status": "completed",
      "quality_score": 0.95,
      "created_at": "2024-01-01T10:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "pages": 1
}
```

### 3. Getting Document Details

**What it does**: Shows complete information about a specific document
**Who can use it**: Users with read permission for that document

```bash
GET /api/v1/documents/{document_id}
```

**Example**:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8011/api/v1/documents/doc_12345"
```

### 4. Downloading Documents

**What it does**: Provides secure download of the actual file
**Who can use it**: Users with read permission

```bash
GET /api/v1/documents/{document_id}/download
```

**Example**:
```bash
# Download and save to file
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8011/api/v1/documents/doc_12345/download" \
  -o downloaded_document.pdf
```

### 5. Checking Processing Status

**What it does**: Shows how document processing is going
**Why it's useful**: Large documents take time to process

```bash
GET /api/v1/documents/{document_id}/processing-status
```

**Example Response**:
```json
{
  "document_id": "doc_12345",
  "processing_status": "completed",
  "processing_started_at": "2024-01-01T10:00:00Z",
  "processing_completed_at": "2024-01-01T10:02:30Z", 
  "processing_time_seconds": 150,
  "extracted_text_preview": "This document discusses COVID-19 treatment...",
  "page_count": 25,
  "word_count": 8500,
  "quality_score": 0.95,
  "errors": []
}
```

**Status Meanings**:
- `pending`: "Just uploaded, waiting to be processed"
- `processing`: "Currently extracting text and analyzing"
- `completed`: "All done! Document is ready for search"
- `failed`: "Something went wrong, check error message"

## 🔒 Security & Permissions (Who Can Do What)

### Document Visibility Levels

| Level | Who Can Access | Example Use Case |
|-------|---------------|------------------|
| **private** | Only the uploader | Personal research notes |
| **public** | All authenticated users | Published research papers |
| **restricted** | Specific users/roles only | Patient records (doctors only) |

### Role-Based Access

```
👨‍⚕️ Doctor Role:
- ✅ Upload medical documents
- ✅ Access patient records
- ✅ Download research papers
- ✅ Share documents with other doctors

👨‍🎓 Student Role:  
- ❌ Cannot upload documents
- ✅ Access educational materials only
- ❌ Cannot access patient records
- ❌ Cannot download restricted content

👨‍💼 Admin Role:
- ✅ Everything doctors can do
- ✅ Manage document permissions
- ✅ Delete any document
- ✅ View system statistics
```

### Example Permission Scenario:
```
Dr. Smith uploads patient X-ray → Sets visibility to "restricted"
↓
System automatically allows: Other doctors, radiologists
System automatically denies: Students, general users
↓
Dr. Smith can manually grant access to specific medical students for education
```

## 🔄 Document Processing Pipeline (What Happens After Upload)

### Stage 1: Upload Validation
```
File arrives → Check file type → Check file size → Virus scan → Security validation
↓
✅ PASS: Continue to storage
❌ FAIL: Return error to user with explanation
```

### Stage 2: Secure Storage
```
Valid file → Generate unique filename → Encrypt file → Upload to S3 → Create backup copies
↓
File now safely stored with multiple redundancy
```

### Stage 3: Text Extraction
```
PDF file → Try multiple extraction methods:
1. PyPDF2 (fast, works with most PDFs)
2. pdfplumber (better for complex layouts)  
3. PyMuPDF (handles scanned documents)
↓
Pick best result → Clean up text → Extract readable content
```

### Stage 4: Medical Analysis
```
Extracted text → Find medical terms:
- Diseases: "diabetes", "hypertension", "COVID-19"
- Procedures: "surgery", "MRI", "blood test"
- Medications: "aspirin", "insulin", "antibiotics"
- Anatomy: "heart", "lung", "brain"
↓
Create searchable medical index
```

### Stage 5: Quality Assessment
```
Document analysis → Calculate quality score:
- Text extraction success: 30%
- Medical term density: 25%
- Document structure: 20%
- Image/table clarity: 15%
- Completeness: 10%
↓
Overall quality score: 0.0 (poor) to 1.0 (excellent)
```

### Stage 6: Event Publishing
```
Processing complete → Notify other services:
- Search service: "New document ready for indexing"
- Analytics service: "Document processing completed"
- Notification service: "Tell user their document is ready"
```

## 🧪 Testing Your Understanding

### Exercise 1: Upload Different Document Types
Try uploading various files to see how the system handles them:

```bash
# Upload a PDF (should work)
curl -X POST http://localhost:8011/api/v1/documents/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@medical_research.pdf"

# Try uploading an image (should be rejected)
curl -X POST http://localhost:8011/api/v1/documents/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@xray_image.jpg"

# Try uploading a huge file (should be rejected)
curl -X POST http://localhost:8011/api/v1/documents/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@huge_file.pdf"
```

### Exercise 2: Test Permission System
```bash
# Create a student account
curl -X POST http://localhost:8010/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@university.com",
    "role": "student",
    "password": "StudentPass123!"
  }'

# Login as student and try to upload (should fail)
# Login as doctor and try to upload (should succeed)
```

### Exercise 3: Monitor Processing
```bash
# Upload a large document
DOCUMENT_ID=$(curl -X POST http://localhost:8011/api/v1/documents/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@large_document.pdf" | jq -r '.id')

# Check processing status every 10 seconds
while true; do
  curl -H "Authorization: Bearer YOUR_TOKEN" \
    "http://localhost:8011/api/v1/documents/$DOCUMENT_ID/processing-status"
  sleep 10
done
```

## 🐛 Troubleshooting Guide

### Problem: "File upload failed"
**Symptoms**: Upload returns error immediately

**Check these things**:
```bash
# 1. Is the service running?
curl http://localhost:8011/health

# 2. Is your token valid?
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8011/api/v1/documents

# 3. Is the file too large?
ls -lh your_file.pdf

# 4. Is it the right file type?
file --mime-type your_file.pdf
```

**Common solutions**:
- File too large: Reduce size or increase `MAX_FILE_SIZE_MB` setting
- Wrong file type: Only PDF, DOC, DOCX are supported
- Invalid token: Login again to get fresh token
- Service down: Restart with `docker-compose restart document-service`

### Problem: "Document stuck in processing"
**Symptoms**: Status stays "processing" for hours

**Debug steps**:
```bash
# Check processing service logs
docker-compose logs content-processing-service

# Check if document is corrupted
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8011/api/v1/documents/DOC_ID/processing-status"

# Retry processing
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8011/api/v1/documents/DOC_ID/retry-processing"
```

### Problem: "Can't download document"
**Symptoms**: Download link doesn't work

**Solutions**:
```bash
# Check if you have permission
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8011/api/v1/documents/DOC_ID"

# Check S3 connection
docker-compose logs document-service | grep -i s3

# Try direct download
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8011/api/v1/documents/DOC_ID/download" \
  -o test_download.pdf
```

### Problem: "Low quality score"
**Symptoms**: Documents get quality score below 0.5

**Understanding quality issues**:
- **Scanned documents**: May have OCR problems
- **Complex layouts**: Tables and images cause issues
- **Non-English text**: System optimized for English
- **Corrupted PDFs**: File structure problems

**Improving quality**:
1. Use text-based PDFs instead of scanned images
2. Ensure good contrast in scanned documents
3. Avoid password-protected PDFs
4. Use standard fonts and layouts

## 📊 Understanding File Processing

### Supported File Types & Processing

| File Type | Extensions | What We Extract | Processing Time |
|-----------|------------|-----------------|-----------------|
| **PDF** | `.pdf` | Full text, metadata, images | 30-120 seconds |
| **Word** | `.doc`, `.docx` | Text content, basic formatting | 10-30 seconds |
| **Text** | `.txt` | All content | 1-5 seconds |

### Processing Performance
```
Small file (< 1MB):     ~10 seconds
Medium file (1-10MB):   ~30 seconds  
Large file (10-50MB):   ~120 seconds
```

### Quality Metrics Explained
```
Quality Score Breakdown:
0.9-1.0: Excellent (perfect text extraction, rich metadata)
0.7-0.9: Good (minor issues, mostly readable)
0.5-0.7: Fair (some text missing, usable)
0.3-0.5: Poor (significant issues, limited usefulness)
0.0-0.3: Failed (mostly unreadable)
```

## 🔧 Configuration for Different Use Cases

### Hospital Setting (High Security)
```bash
# Strict file validation
MAX_FILE_SIZE_MB=25
ALLOWED_FILE_TYPES=application/pdf
ENABLE_VIRUS_SCANNING=true

# Enhanced security
REQUIRE_MEDICAL_ROLE_FOR_UPLOAD=true
AUTO_ENCRYPT_FILES=true
AUDIT_ALL_ACCESS=true
```

### Research Institution (Flexibility)
```bash
# More file types allowed
MAX_FILE_SIZE_MB=100
ALLOWED_FILE_TYPES=application/pdf,application/msword,text/plain

# Faster processing
ENABLE_PARALLEL_PROCESSING=true
SKIP_QUALITY_CHECK_FOR_TRUSTED_USERS=true
```

### Educational Setting (Student Access)
```bash
# Limited upload permissions
STUDENTS_CAN_UPLOAD=false
PUBLIC_DOCUMENTS_VISIBLE_TO_STUDENTS=true

# Educational features
ENABLE_DOCUMENT_ANNOTATIONS=true
TRACK_STUDENT_ACCESS=true
```

## 🎓 Learning More

### Next Steps in Your Learning Journey:

1. **Master the Basics**: 
   - Practice uploading different document types
   - Understand permission systems
   - Learn to troubleshoot common issues

2. **Explore Advanced Features**:
   - Document versioning (keeping track of changes)
   - Batch uploads (multiple files at once)
   - Custom metadata fields

3. **Integration Learning**:
   - How this connects to the Search service
   - How Authentication controls access
   - How Processing service analyzes content

4. **System Administration**:
   - Monitor storage usage
   - Manage user permissions
   - Backup and recovery procedures

### Hands-On Projects:

#### Project 1: Build a Simple Upload Interface
```html
<!-- Simple HTML form for document upload -->
<form id="uploadForm">
  <input type="file" id="fileInput" accept=".pdf">
  <input type="text" id="titleInput" placeholder="Document Title">
  <button type="submit">Upload Document</button>
</form>

<script>
document.getElementById('uploadForm').onsubmit = async (e) => {
  e.preventDefault();
  
  const formData = new FormData();
  formData.append('file', document.getElementById('fileInput').files[0]);
  formData.append('title', document.getElementById('titleInput').value);
  
  const response = await fetch('http://localhost:8011/api/v1/documents/upload', {
    method: 'POST',
    headers: {
      'Authorization': 'Bearer YOUR_TOKEN'
    },
    body: formData
  });
  
  const result = await response.json();
  console.log('Upload result:', result);
};
</script>
```

#### Project 2: Document Processing Monitor
```python
import requests
import time

def monitor_document_processing(document_id, token):
    """Monitor document processing status"""
    url = f"http://localhost:8011/api/v1/documents/{document_id}/processing-status"
    headers = {"Authorization": f"Bearer {token}"}
    
    while True:
        response = requests.get(url, headers=headers)
        status = response.json()
        
        print(f"Status: {status['processing_status']}")
        
        if status['processing_status'] in ['completed', 'failed']:
            break
            
        time.sleep(5)  # Check every 5 seconds
    
    return status

# Usage
result = monitor_document_processing('doc_12345', 'your_token')
print(f"Final result: {result}")
```

## 🌟 Best Practices

### For Developers:
1. **Always check authentication** before allowing document access
2. **Validate file types** on both client and server side
3. **Handle large files** with proper progress indicators
4. **Implement retry logic** for failed uploads
5. **Cache document metadata** for better performance

### For System Administrators:
1. **Monitor storage usage** regularly
2. **Set up automated backups** of document metadata
3. **Review access logs** for security
4. **Update file size limits** based on usage patterns
5. **Test disaster recovery** procedures

### For End Users:
1. **Use descriptive titles** for better searchability
2. **Add relevant keywords** to help others find documents
3. **Choose appropriate visibility** levels
4. **Check processing status** for large uploads
5. **Keep original files** as backup

---

## 🎉 Congratulations!

You now understand how document management works in our medical AI platform! You've learned:

- ✅ How to safely upload and store medical documents
- ✅ Understanding file processing and quality assessment
- ✅ Permission systems and access control
- ✅ API usage with real examples
- ✅ Troubleshooting common problems
- ✅ Security features and best practices

**Next Challenge**: Try connecting this with the Search service to see how uploaded documents become searchable!

---

**📞 Need Help?**
- Review the troubleshooting section
- Check service logs: `docker-compose logs document-service`
- Test with small files first
- Ask questions in our team chat

**Last Updated**: Agust 2025