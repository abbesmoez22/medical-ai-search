import pytest
import uuid
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestDocumentEndpoints:
    """Test document management endpoints"""
    
    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "document-management"
        assert data["version"] == "1.0.0"
        assert data["status"] == "running"
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        with patch('app.api.health.get_db') as mock_db, \
             patch('app.api.health.get_redis') as mock_redis, \
             patch('app.api.health.get_storage_service') as mock_storage, \
             patch('app.api.health.get_event_publisher') as mock_publisher:
            
            # Mock dependencies
            mock_db.return_value.execute = AsyncMock()
            mock_redis.return_value.ping = AsyncMock()
            mock_storage.return_value.s3_client.list_objects_v2 = Mock()
            mock_publisher.return_value.producer = Mock()
            
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "document-management"
            assert "dependencies" in data
    
    def test_upload_document_unauthorized(self):
        """Test document upload without authentication"""
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.pdf", b"fake pdf content", "application/pdf")}
        )
        assert response.status_code == 403  # No Authorization header
    
    def test_get_document_unauthorized(self):
        """Test get document without authentication"""
        document_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/documents/{document_id}")
        assert response.status_code == 403  # No Authorization header
    
    def test_list_documents_unauthorized(self):
        """Test list documents without authentication"""
        response = client.get("/api/v1/documents")
        assert response.status_code == 403  # No Authorization header


class TestDocumentValidation:
    """Test document validation logic"""
    
    def test_validate_file_size(self):
        """Test file size validation"""
        from app.core.config import settings
        
        # Test that MAX_FILE_SIZE is properly set
        assert settings.MAX_FILE_SIZE == 52428800  # 50MB
    
    def test_validate_mime_types(self):
        """Test MIME type validation"""
        from app.core.config import settings
        
        # Test that allowed MIME types are properly set
        assert "application/pdf" in settings.ALLOWED_MIME_TYPES
        assert "text/plain" in settings.ALLOWED_MIME_TYPES


class TestS3StorageService:
    """Test S3 storage service"""
    
    @pytest.mark.asyncio
    async def test_s3_service_initialization(self):
        """Test S3 service initialization"""
        from app.services.storage import S3StorageService
        
        with patch('boto3.client') as mock_boto3:
            service = S3StorageService()
            assert service.bucket_name is not None
            assert service.s3_client is not None
            mock_boto3.assert_called_once()


class TestEventPublisher:
    """Test Kafka event publisher"""
    
    @pytest.mark.asyncio
    async def test_event_publisher_initialization(self):
        """Test event publisher initialization"""
        from app.events.publisher import DocumentEventPublisher
        
        with patch('kafka.KafkaProducer') as mock_producer:
            publisher = DocumentEventPublisher()
            await publisher.initialize()
            mock_producer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_publish_document_uploaded_event(self):
        """Test publishing document uploaded event"""
        from app.events.publisher import publish_document_uploaded
        
        with patch('app.events.publisher.document_event_publisher.publish_document_event') as mock_publish:
            mock_publish.return_value = True
            
            await publish_document_uploaded(
                document_id="test-id",
                s3_bucket="test-bucket",
                s3_key="test-key",
                mime_type="application/pdf",
                uploaded_by="user-id"
            )
            
            mock_publish.assert_called_once()
            args, kwargs = mock_publish.call_args
            assert args[0] == "document.uploaded"
            assert args[1]["document_id"] == "test-id"


if __name__ == "__main__":
    pytest.main([__file__])