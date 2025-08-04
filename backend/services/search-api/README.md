# 🔎 Search API Service - Complete Learning Guide

Welcome! This guide will teach you how our **Search API Service** works. Think of this service as the **smart search engine** that helps doctors and researchers find exactly the medical information they need in seconds.

## 📖 What Is This Service?

Imagine you're a doctor treating a patient with a rare condition. You need to find the latest research, treatment options, and clinical studies quickly. Our Search API Service makes this possible!

### Real-World Scenario:
```
👩‍⚕️ Emergency Room Doctor: "I have a patient with chest pain and diabetes. 
                            I need to find treatment protocols that consider both conditions."

🔎 Our Search API: "Found 234 relevant documents in 0.2 seconds:
                   - Emergency cardiac protocols for diabetic patients
                   - Drug interaction warnings for diabetics with heart conditions  
                   - Recent studies on diabetes-related cardiac events
                   - Treatment guidelines from top medical institutions"

👩‍⚕️ Doctor: "Perfect! I can make an informed decision immediately."
```

## 🎯 What Problems Does This Solve?

### The Medical Information Challenge:
- 📚 **Information overload**: Millions of medical documents exist
- ⏰ **Time pressure**: Doctors need answers in seconds, not hours
- 🎯 **Precision needed**: Wrong information can be life-threatening
- 🔗 **Context matters**: Need to find related information across different documents
- 👥 **Different expertise levels**: Students vs. specialists need different results

### Our Solution:
- ⚡ **Lightning-fast search**: Results in milliseconds
- 🧠 **Medical intelligence**: Understands medical terminology and relationships
- 🎯 **Relevance ranking**: Most important results first
- 🔒 **Access control**: Right information for the right people
- 📊 **Rich filtering**: Search by document type, date, quality, etc.
- 💡 **Smart suggestions**: Helps users find what they're looking for

## 🏗️ How It Works (Simple Architecture)

```
👤 User Query → 🔎 Search API → 📊 Elasticsearch → 🔍 Smart Results → 👤 User
```

### The Search Process:

#### Step 1: User Makes Search Request
```
Doctor searches: "diabetes insulin treatment guidelines"
↓
Search API receives: "Let me understand what you're looking for..."
```

#### Step 2: Query Intelligence
```
Search API analyzes query:
- "diabetes" → Include: "diabetic", "DM", "glucose disorder"
- "insulin" → Include: "insulin therapy", "insulin resistance" 
- "treatment" → Include: "therapy", "management", "intervention"
- "guidelines" → Include: "protocols", "recommendations", "standards"
```

#### Step 3: Elasticsearch Search
```
Enhanced query sent to Elasticsearch:
- Search across: title, content, medical entities, authors
- Apply filters: document type, quality score, user permissions
- Boost relevance: medical terms, recent documents, high-quality sources
```

#### Step 4: Results Processing
```
Raw Elasticsearch results → Smart processing:
- Remove duplicates
- Apply user permissions (students can't see restricted content)
- Highlight matching terms in results
- Calculate final relevance scores
- Add related suggestions
```

#### Step 5: Return Rich Results
```
Formatted response with:
- Ranked document list
- Highlighted search terms
- Document previews
- Related search suggestions
- Filtering options
- Performance metrics
```

## 🚀 Getting Started (Step by Step)

### Prerequisites:
1. **Search Indexing Service** running (creates searchable index)
2. **Elasticsearch** with indexed documents
3. **Authentication Service** (for user permissions)
4. **Redis** (for caching search results)

### Quick Start:

#### Step 1: Start the Service
```bash
# Go to backend directory
cd backend

# Start all required services
docker-compose -f docker-compose.dev.yml up -d postgres redis elasticsearch search-indexing-service

# Start search API service
docker-compose -f docker-compose.dev.yml up -d search-api-service

# Check if working
curl http://localhost:8015/health
```

#### Step 2: Get Authentication Token
```bash
# Login to get access token
TOKEN=$(curl -X POST http://localhost:8010/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "doctor@hospital.com", "password": "SecurePass123!"}' \
  | jq -r '.access_token')

echo "Your token: $TOKEN"
```

#### Step 3: Make Your First Search
```bash
# Search for diabetes-related documents
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8015/api/v1/search/?q=diabetes&size=5" | jq .
```

#### Step 4: Try Advanced Searches
```bash
# Search with filters
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8015/api/v1/search/?q=heart%20surgery&size=10&sort_by=publication_date&sort_order=desc" | jq .

# Get search suggestions
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8015/api/v1/search/suggest?q=diabet&size=5" | jq .

# Get search facets (filtering options)
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8015/api/v1/search/facets?q=cardiology" | jq .
```

## 📚 API Reference (Learn by Examples)

### 1. Basic Document Search

**What it does**: Searches for documents matching your query
**Who can use**: Any authenticated user (results filtered by permissions)

```bash
GET /api/v1/search/?q={query}&size={number}&page={page}
```

**Simple Example**:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8015/api/v1/search/?q=diabetes&size=10&page=1"
```

**Advanced Example with Filters**:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8015/api/v1/search/" \
  -G \
  --data-urlencode "q=heart surgery" \
  --data-urlencode "filters={\"document_type\":\"research_paper\",\"date_range\":{\"from\":\"2023-01-01\",\"to\":\"2024-12-31\"}}" \
  --data-urlencode "size=20" \
  --data-urlencode "sort_by=quality_score" \
  --data-urlencode "sort_order=desc"
```

**Response Structure**:
```json
{
  "documents": [
    {
      "id": "doc_12345",
      "document_id": "doc_12345",
      "title": "Diabetes Management Guidelines 2024",
      "content": "This comprehensive guide covers...",
      "authors": "Dr. Smith, Dr. Johnson",
      "document_type": "clinical_guideline",
      "publication_date": "2024-01-15",
      "quality_score": 0.94,
      "medical_relevance_score": 0.89,
      "score": 8.2,
      "highlights": {
        "title": ["<em>Diabetes</em> Management Guidelines"],
        "content": ["...treatment of <em>diabetes</em> mellitus..."]
      }
    }
  ],
  "total_hits": 247,
  "page": 1,
  "page_size": 10,
  "total_pages": 25,
  "has_next": true,
  "has_previous": false,
  "query": "diabetes",
  "search_time_ms": 23.5
}
```

### 2. POST Search (For Complex Queries)

**What it does**: Allows complex search requests with detailed filtering
**When to use**: When you need advanced filtering or large query parameters

```bash
POST /api/v1/search/
```

**Example**:
```bash
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  "http://localhost:8015/api/v1/search/" \
  -d '{
    "query": "cardiovascular disease prevention",
    "filters": {
      "document_type": "research_paper",
      "date_range": {
        "from": "2020-01-01",
        "to": "2024-12-31"
      },
      "quality_score": {
        "min": 0.8,
        "max": 1.0
      },
      "medical_entities": ["cardiovascular", "prevention", "cardiology"]
    },
    "page": 1,
    "page_size": 20,
    "sort_by": "medical_relevance_score",
    "sort_order": "desc"
  }'
```

### 3. Get Specific Document

**What it does**: Retrieves detailed information about a specific document
**Who can use**: Users with read permission for that document

```bash
GET /api/v1/search/documents/{document_id}
```

**Example**:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8015/api/v1/search/documents/doc_12345"
```

**Response**:
```json
{
  "id": "doc_12345",
  "document_id": "doc_12345",
  "title": "Comprehensive Diabetes Treatment Protocol",
  "content": "Full document content here...",
  "authors": "Dr. Smith, Dr. Johnson, Dr. Williams",
  "abstract": "This study presents a comprehensive approach...",
  "keywords": ["diabetes", "treatment", "insulin", "glucose"],
  "medical_entities": {
    "diseases": [
      {"text": "Type 2 diabetes", "confidence": 0.98},
      {"text": "diabetic neuropathy", "confidence": 0.87}
    ],
    "medications": [
      {"text": "metformin", "confidence": 0.95},
      {"text": "insulin", "confidence": 0.99}
    ]
  },
  "document_type": "clinical_guideline",
  "publication_date": "2024-01-15",
  "language": "en",
  "quality_score": 0.94,
  "medical_relevance_score": 0.89,
  "created_at": "2024-01-15T10:00:00Z",
  "indexed_at": "2024-01-15T10:05:00Z"
}
```

### 4. Search Suggestions/Autocomplete

**What it does**: Provides search term suggestions as user types
**Great for**: Improving user experience with helpful suggestions

```bash
GET /api/v1/search/suggest?q={partial_query}&size={number}
```

**Example**:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8015/api/v1/search/suggest?q=diabet&size=10"
```

**Response**:
```json
{
  "suggestions": [
    "diabetes",
    "diabetic neuropathy", 
    "diabetes mellitus",
    "diabetic retinopathy",
    "diabetes treatment",
    "diabetic ketoacidosis",
    "diabetes management",
    "diabetic complications"
  ],
  "query": "diabet"
}
```

### 5. Search Facets (Filter Options)

**What it does**: Shows available filtering options for search results
**Useful for**: Building advanced search interfaces

```bash
GET /api/v1/search/facets?q={query}
```

**Example**:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8015/api/v1/search/facets?q=cardiology"
```

**Response**:
```json
{
  "document_types": [
    {"value": "research_paper", "count": 156},
    {"value": "clinical_guideline", "count": 89},
    {"value": "case_study", "count": 45}
  ],
  "languages": [
    {"value": "en", "count": 267},
    {"value": "es", "count": 23}
  ],
  "publication_years": [
    {"value": 2024, "count": 89},
    {"value": 2023, "count": 124},
    {"value": 2022, "count": 76}
  ],
  "quality_ranges": [
    {"value": "high", "count": 201},
    {"value": "medium", "count": 67},
    {"value": "low", "count": 22}
  ],
  "medical_entities": [
    {"value": "cardiology", "count": 189},
    {"value": "cardiac surgery", "count": 78},
    {"value": "heart disease", "count": 134}
  ]
}
```

### 6. Search Statistics

**What it does**: Provides search system performance metrics
**Who can use**: Authenticated users (useful for monitoring)

```bash
GET /api/v1/search/stats
```

**Example**:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8015/api/v1/search/stats"
```

**Response**:
```json
{
  "index_name": "medical-ai-documents",
  "document_count": 12847,
  "index_size_bytes": 2847392847,
  "cache_enabled": true,
  "cache_ttl_seconds": 300
}
```

## 🔍 Understanding Search Intelligence

### Medical Term Recognition

Our search engine understands medical terminology and relationships:

#### Synonym Recognition:
```
User searches: "heart attack"
System also searches for:
- "myocardial infarction"
- "MI" 
- "cardiac event"
- "acute coronary syndrome"
- "coronary thrombosis"
```

#### Abbreviation Expansion:
```
User searches: "MI"
System understands:
- "myocardial infarction"
- "heart attack"
- "cardiac event"

User searches: "DM"
System understands:
- "diabetes mellitus"
- "diabetes"
- "diabetic condition"
```

#### Related Term Discovery:
```
User searches: "diabetes"
System also considers:
- Related conditions: "diabetic neuropathy", "diabetic retinopathy"
- Related treatments: "insulin", "metformin", "glucose monitoring"
- Related specialties: "endocrinology", "diabetes care"
```

### Search Ranking Algorithm

How we determine which results are most relevant:

#### 1. Text Relevance (40% of score)
```
Query: "diabetes treatment"

Document A: Title contains "Diabetes Treatment Guidelines"
- High term frequency in important field (title)
- Score contribution: 8.5/10

Document B: Brief mention of diabetes treatment in conclusion
- Low term frequency in less important field
- Score contribution: 3.2/10
```

#### 2. Medical Entity Matching (25% of score)
```
Query: "heart surgery"

Document A: Contains medical entities: "cardiac surgery", "coronary bypass"
- Strong medical entity alignment
- Score contribution: 9.1/10

Document B: Contains: "surgery" but no cardiac-specific terms
- Weak medical entity alignment  
- Score contribution: 4.5/10
```

#### 3. Document Quality (20% of score)
```
Document A: Quality score 0.94 (excellent text extraction, high medical relevance)
- Score contribution: 9.4/10

Document B: Quality score 0.65 (fair text extraction, medium relevance)
- Score contribution: 6.5/10
```

#### 4. Recency Boost (10% of score)
```
Document A: Published 2024 (recent)
- Score contribution: 8.0/10

Document B: Published 2018 (older)
- Score contribution: 6.0/10
```

#### 5. User Role Relevance (5% of score)
```
Doctor searching for "diabetes":
- Clinical guidelines get boost: +15%
- Research papers get boost: +10%
- Patient education materials: no boost

Student searching for "diabetes":
- Educational materials get boost: +20%
- Basic explanations get boost: +15%
- Advanced research: no boost
```

## 🔒 Access Control & Permissions

### Role-Based Search Results

Different users see different results for the same query:

#### Example Search: "patient confidential diabetes case"

**Doctor (High Permissions)**:
```json
{
  "total_hits": 156,
  "documents": [
    {
      "title": "Confidential: Complex Diabetes Case Study",
      "access_level": "restricted",
      "visible_to": "doctors"
    },
    {
      "title": "Diabetes Treatment Protocol - Internal",
      "access_level": "internal",
      "visible_to": "medical_staff"
    }
  ]
}
```

**Student (Limited Permissions)**:
```json
{
  "total_hits": 23,
  "documents": [
    {
      "title": "Diabetes Educational Materials",
      "access_level": "public",
      "visible_to": "all"
    },
    {
      "title": "Basic Diabetes Management Guide",
      "access_level": "educational",
      "visible_to": "students"
    }
  ]
}
```

### Document Visibility Levels:
- **public**: All authenticated users
- **educational**: Students and above
- **internal**: Medical staff only
- **restricted**: Doctors and specialists only
- **confidential**: Specific users only

## 🚀 Performance & Caching

### Search Performance Metrics:
```
Simple query (1-2 terms):        ~10-50ms
Complex query (multiple filters): ~50-200ms
Faceted search:                  ~100-300ms
Suggestion lookup:               ~5-20ms
```

### Intelligent Caching:

#### Cache Strategy:
```
Popular searches → Cache for 5 minutes
User-specific searches → Cache for 2 minutes  
Facet data → Cache for 10 minutes
Document details → Cache for 30 minutes
```

#### Cache Example:
```
First search for "diabetes treatment":
- Query Elasticsearch: 150ms
- Process results: 25ms
- Cache results: 5ms
- Total time: 180ms

Second search for "diabetes treatment" (same user):
- Get from cache: 8ms
- Total time: 8ms (22x faster!)
```

## 🧪 Testing Your Understanding

### Exercise 1: Search Quality Testing
```bash
# Test different search approaches for the same medical concept
TOKEN="your_token_here"

echo "=== Testing Medical Synonym Recognition ==="

# Search using formal medical term
echo "1. Searching for 'myocardial infarction':"
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8015/api/v1/search/?q=myocardial%20infarction&size=3" | \
  jq '.total_hits'

# Search using common term
echo "2. Searching for 'heart attack':"
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8015/api/v1/search/?q=heart%20attack&size=3" | \
  jq '.total_hits'

# Search using abbreviation
echo "3. Searching for 'MI':"
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8015/api/v1/search/?q=MI&size=3" | \
  jq '.total_hits'

echo "All three searches should return similar results!"
```

### Exercise 2: Filter Effectiveness
```python
import requests

def test_search_filters(token):
    """Test how filters affect search results"""
    base_url = "http://localhost:8015/api/v1/search/"
    headers = {"Authorization": f"Bearer {token}"}
    
    # Search without filters
    response1 = requests.get(base_url, headers=headers, params={
        "q": "diabetes",
        "size": 100
    })
    total_without_filters = response1.json()["total_hits"]
    
    # Search with document type filter
    response2 = requests.get(base_url, headers=headers, params={
        "q": "diabetes",
        "size": 100,
        "filters": '{"document_type": "research_paper"}'
    })
    total_research_papers = response2.json()["total_hits"]
    
    # Search with quality filter
    response3 = requests.get(base_url, headers=headers, params={
        "q": "diabetes", 
        "size": 100,
        "filters": '{"quality_score": {"min": 0.8}}'
    })
    total_high_quality = response3.json()["total_hits"]
    
    print(f"Search Results Analysis:")
    print(f"Total diabetes documents: {total_without_filters}")
    print(f"Research papers only: {total_research_papers}")
    print(f"High quality only: {total_high_quality}")
    print(f"Filter effectiveness: {(total_without_filters - total_high_quality) / total_without_filters * 100:.1f}% filtered out")

# Usage
test_search_filters('your_token_here')
```

### Exercise 3: Search Performance Analysis
```bash
# Test search performance with different query complexities
TOKEN="your_token_here"

echo "=== Search Performance Testing ==="

# Simple search
echo "1. Simple search performance:"
time curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8015/api/v1/search/?q=diabetes" > /dev/null

# Complex search with filters
echo "2. Complex filtered search performance:"
time curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8015/api/v1/search/?q=diabetes%20treatment&filters=%7B%22document_type%22%3A%22research_paper%22%2C%22quality_score%22%3A%7B%22min%22%3A0.8%7D%7D" > /dev/null

# Faceted search
echo "3. Faceted search performance:"
time curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8015/api/v1/search/facets?q=cardiology" > /dev/null

echo "Compare the times - simple searches should be fastest!"
```

## 🐛 Troubleshooting Guide

### Problem: "No search results found"
**Symptoms**: All searches return 0 results

**Debug steps**:
```bash
# 1. Check if documents are indexed
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8014/api/v1/indexing/stats"

# 2. Check Elasticsearch directly
curl "http://localhost:9201/medical-ai-documents/_search?q=*&size=1"

# 3. Test service health
curl http://localhost:8015/health

# 4. Check user permissions
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8010/api/v1/users/me"
```

### Problem: "Search results not relevant"
**Symptoms**: Search returns documents that don't match the query

**Solutions**:
```bash
# Check if medical synonyms are working
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8015/api/v1/search/?q=heart%20attack" | \
  jq '.documents[0].highlights'

# Test with exact medical terms
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8015/api/v1/search/?q=myocardial%20infarction"

# Check document quality scores
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8015/api/v1/search/?q=diabetes&filters=%7B%22quality_score%22%3A%7B%22min%22%3A0.8%7D%7D"
```

### Problem: "Search is too slow"
**Symptoms**: Search requests take more than 1 second

**Performance optimization**:
```bash
# Check Elasticsearch performance
curl "http://localhost:9201/_cluster/health"

# Monitor search times
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8015/api/v1/search/?q=diabetes" | \
  jq '.search_time_ms'

# Check if caching is working (second request should be faster)
time curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8015/api/v1/search/?q=diabetes" > /dev/null

time curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8015/api/v1/search/?q=diabetes" > /dev/null
```

### Problem: "Search suggestions not working"
**Symptoms**: Suggestion endpoint returns empty results

**Debug steps**:
```bash
# Test suggestion endpoint directly
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8015/api/v1/search/suggest?q=diab"

# Check if Elasticsearch has suggestion data
curl "http://localhost:9201/medical-ai-documents/_search" \
  -H "Content-Type: application/json" \
  -d '{"suggest": {"title_suggest": {"prefix": "diab", "completion": {"field": "title.suggest"}}}}'

# Verify documents have proper suggestion fields
curl "http://localhost:9201/medical-ai-documents/_mapping"
```

## 📈 Advanced Features

### Building Custom Search Interfaces

#### Example: Medical Search Dashboard
```html
<!DOCTYPE html>
<html>
<head>
    <title>Medical Search Dashboard</title>
    <style>
        .search-container { max-width: 800px; margin: 0 auto; padding: 20px; }
        .search-box { width: 100%; padding: 15px; font-size: 16px; border: 2px solid #ddd; }
        .filters { margin: 20px 0; }
        .results { margin-top: 20px; }
        .result-item { border: 1px solid #eee; padding: 15px; margin: 10px 0; }
        .highlight { background-color: yellow; }
    </style>
</head>
<body>
    <div class="search-container">
        <h1>Medical Document Search</h1>
        
        <input type="text" id="searchBox" class="search-box" 
               placeholder="Search medical documents..." 
               onkeyup="performSearch()">
        
        <div class="filters">
            <select id="documentType" onchange="performSearch()">
                <option value="">All Document Types</option>
                <option value="research_paper">Research Papers</option>
                <option value="clinical_guideline">Clinical Guidelines</option>
                <option value="case_study">Case Studies</option>
            </select>
            
            <select id="qualityFilter" onchange="performSearch()">
                <option value="">All Quality Levels</option>
                <option value="high">High Quality Only</option>
                <option value="medium">Medium+ Quality</option>
            </select>
        </div>
        
        <div id="results" class="results"></div>
    </div>

    <script>
        const TOKEN = 'your_jwt_token_here';
        
        async function performSearch() {
            const query = document.getElementById('searchBox').value;
            if (!query) return;
            
            const documentType = document.getElementById('documentType').value;
            const qualityFilter = document.getElementById('qualityFilter').value;
            
            // Build filters
            const filters = {};
            if (documentType) filters.document_type = documentType;
            if (qualityFilter === 'high') filters.quality_score = {min: 0.8};
            if (qualityFilter === 'medium') filters.quality_score = {min: 0.6};
            
            try {
                const response = await fetch('http://localhost:8015/api/v1/search/', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${TOKEN}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        query: query,
                        filters: Object.keys(filters).length > 0 ? filters : null,
                        page: 1,
                        page_size: 10
                    })
                });
                
                const data = await response.json();
                displayResults(data);
            } catch (error) {
                console.error('Search failed:', error);
            }
        }
        
        function displayResults(data) {
            const resultsDiv = document.getElementById('results');
            
            if (data.total_hits === 0) {
                resultsDiv.innerHTML = '<p>No results found.</p>';
                return;
            }
            
            let html = `<h3>Found ${data.total_hits} results (${data.search_time_ms}ms)</h3>`;
            
            data.documents.forEach(doc => {
                html += `
                    <div class="result-item">
                        <h4>${highlightText(doc.title, doc.highlights?.title)}</h4>
                        <p><strong>Authors:</strong> ${doc.authors || 'Unknown'}</p>
                        <p><strong>Type:</strong> ${doc.document_type}</p>
                        <p><strong>Quality Score:</strong> ${(doc.quality_score * 100).toFixed(1)}%</p>
                        <p>${highlightText(doc.content?.substring(0, 300) + '...', doc.highlights?.content)}</p>
                    </div>
                `;
            });
            
            resultsDiv.innerHTML = html;
        }
        
        function highlightText(text, highlights) {
            if (!highlights || !text) return text;
            
            highlights.forEach(highlight => {
                const highlightedText = highlight.replace(/<em>/g, '<span class="highlight">').replace(/<\/em>/g, '</span>');
                text = text.replace(highlight.replace(/<\/?em>/g, ''), highlightedText);
            });
            
            return text;
        }
    </script>
</body>
</html>
```

### Search Analytics Implementation

```python
import requests
from datetime import datetime, timedelta
from collections import Counter

class SearchAnalytics:
    def __init__(self, token, base_url="http://localhost:8015"):
        self.token = token
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}
    
    def analyze_search_patterns(self, days=7):
        """Analyze search patterns over the last N days"""
        
        # Get search statistics
        stats_response = requests.get(
            f"{self.base_url}/api/v1/search/stats",
            headers=self.headers
        )
        
        stats = stats_response.json()
        
        print(f"Search System Analytics ({days} days)")
        print("=" * 40)
        print(f"Total documents indexed: {stats['document_count']:,}")
        print(f"Index size: {stats['index_size_bytes'] / (1024*1024):.1f} MB")
        
        # Test popular medical terms
        popular_terms = [
            "diabetes", "hypertension", "covid", "cancer", 
            "heart disease", "surgery", "treatment", "diagnosis"
        ]
        
        term_results = {}
        for term in popular_terms:
            response = requests.get(
                f"{self.base_url}/api/v1/search/",
                headers=self.headers,
                params={"q": term, "size": 1}
            )
            
            if response.status_code == 200:
                data = response.json()
                term_results[term] = {
                    "total_hits": data["total_hits"],
                    "search_time_ms": data["search_time_ms"]
                }
        
        print("\nPopular Medical Terms Analysis:")
        print("-" * 30)
        for term, results in sorted(term_results.items(), 
                                  key=lambda x: x[1]["total_hits"], 
                                  reverse=True):
            print(f"{term:15} | {results['total_hits']:6,} docs | {results['search_time_ms']:5.1f}ms")
    
    def test_search_relevance(self):
        """Test search relevance with known medical queries"""
        
        test_queries = [
            {
                "query": "diabetes treatment",
                "expected_terms": ["diabetes", "diabetic", "treatment", "therapy"]
            },
            {
                "query": "heart attack",
                "expected_terms": ["heart", "cardiac", "myocardial", "infarction"]
            },
            {
                "query": "blood pressure medication",
                "expected_terms": ["hypertension", "blood pressure", "medication", "antihypertensive"]
            }
        ]
        
        print("\n\nSearch Relevance Testing:")
        print("=" * 30)
        
        for test in test_queries:
            response = requests.get(
                f"{self.base_url}/api/v1/search/",
                headers=self.headers,
                params={"q": test["query"], "size": 5}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                print(f"\nQuery: '{test['query']}'")
                print(f"Results: {data['total_hits']} documents")
                print(f"Search time: {data['search_time_ms']:.1f}ms")
                
                # Check if expected terms appear in results
                found_terms = set()
                for doc in data["documents"][:3]:
                    content = (doc.get("title", "") + " " + doc.get("content", "")).lower()
                    for term in test["expected_terms"]:
                        if term.lower() in content:
                            found_terms.add(term)
                
                relevance_score = len(found_terms) / len(test["expected_terms"]) * 100
                print(f"Relevance score: {relevance_score:.1f}%")
                print(f"Found terms: {', '.join(found_terms)}")

# Usage
analytics = SearchAnalytics('your_token_here')
analytics.analyze_search_patterns(7)
analytics.test_search_relevance()
```

## 🌟 Best Practices

### For Search Implementation:
1. **Use appropriate page sizes** (10-50 results per page for UI)
2. **Implement search suggestions** for better user experience
3. **Cache frequent searches** to improve performance
4. **Handle empty results gracefully** with helpful suggestions
5. **Provide filtering options** for complex medical searches

### For Medical Search UX:
1. **Support medical abbreviations** (MI, DM, HTN, etc.)
2. **Provide synonym suggestions** when searches fail
3. **Show search result highlights** to explain relevance
4. **Filter by document quality** for critical medical decisions
5. **Implement role-based result filtering** automatically

### For Performance:
1. **Monitor search performance** and optimize slow queries
2. **Use Redis caching** for frequently accessed data
3. **Implement pagination** for large result sets
4. **Optimize Elasticsearch** mapping and analysis
5. **Track and analyze** user search patterns

---

## 🎉 Congratulations!

You now understand how to build and use a sophisticated medical search API! You've learned:

- ✅ How to perform simple and complex medical document searches
- ✅ Understanding search intelligence and medical terminology
- ✅ Implementing access control and role-based filtering
- ✅ Building custom search interfaces and analytics
- ✅ Performance optimization and caching strategies
- ✅ Troubleshooting common search issues

**Next Challenge**: Integrate all services together to build a complete medical AI search platform!

---

**📞 Need Help?**
- Test search functionality: `curl -H "Authorization: Bearer $TOKEN" "http://localhost:8015/api/v1/search/?q=test"`
- Check service health: `curl http://localhost:8015/health`
- Monitor search performance through the API
- Join our developer community for advanced search techniques

**Last Updated**: August 2025