import boto3
import hashlib
from datetime import datetime
from typing import BinaryIO, Optional, Dict
from botocore.exceptions import ClientError
import structlog
from app.core.config import settings

logger = structlog.get_logger()


class S3StorageService:
    def __init__(self):
        self.bucket_name = settings.S3_BUCKET_NAME
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
    
    async def upload_file(self, file_obj: BinaryIO, key: str, content_type: str) -> Dict[str, str]:
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
            
            logger.info("File uploaded to S3", bucket=self.bucket_name, key=key, hash=file_hash)
            
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
            logger.info("File deleted from S3", bucket=self.bucket_name, key=key)
            return True
        except ClientError as e:
            logger.error("S3 delete failed", error=str(e), key=key)
            return False
    
    async def get_presigned_url(self, key: str, expiration: int = 3600) -> str:
        """Generate presigned URL for file access"""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expiration
            )
            logger.info("Presigned URL generated", key=key, expiration=expiration)
            return url
        except ClientError as e:
            logger.error("Presigned URL generation failed", error=str(e), key=key)
            raise
    
    async def file_exists(self, key: str) -> bool:
        """Check if file exists in S3"""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise
    
    async def get_file_metadata(self, key: str) -> Optional[Dict]:
        """Get file metadata from S3"""
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return {
                'size': response['ContentLength'],
                'last_modified': response['LastModified'],
                'content_type': response.get('ContentType'),
                'metadata': response.get('Metadata', {}),
                'version_id': response.get('VersionId')
            }
        except ClientError as e:
            logger.error("Failed to get file metadata", error=str(e), key=key)
            return None


# Global instance
storage_service = S3StorageService()


async def get_storage_service() -> S3StorageService:
    """Dependency to get storage service"""
    return storage_service