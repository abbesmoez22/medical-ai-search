from typing import List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Service Configuration
    DEBUG: bool = Field(default=False)
    SERVICE_NAME: str = Field(default="document-management")
    PORT: int = Field(default=8000)
    
    # Database
    DATABASE_URL: str = Field(...)
    
    # Redis
    REDIS_URL: str = Field(...)
    
    # AWS S3
    AWS_ACCESS_KEY_ID: str = Field(...)
    AWS_SECRET_ACCESS_KEY: str = Field(...)
    AWS_REGION: str = Field(default="us-east-1")
    S3_BUCKET_NAME: str = Field(...)
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = Field(...)
    KAFKA_TOPIC_PREFIX: str = Field(default="medical-ai-platform")
    
    # File Upload Limits
    MAX_FILE_SIZE: int = Field(default=52428800)  # 50MB
    ALLOWED_MIME_TYPES: str = Field(default="application/pdf,text/plain")
    
    # Security
    JWT_SECRET_KEY: str = Field(...)
    JWT_ALGORITHM: str = Field(default="HS256")
    
    # Auth Service
    AUTH_SERVICE_URL: str = Field(default="http://medical-ai-auth-service:8000")
    
    @validator('KAFKA_BOOTSTRAP_SERVERS')
    def validate_kafka_servers(cls, v):
        if isinstance(v, str):
            return [server.strip() for server in v.split(',')]
        return v
    
    @validator('ALLOWED_MIME_TYPES')
    def validate_mime_types(cls, v):
        if isinstance(v, str):
            return [mime.strip() for mime in v.split(',')]
        return v
    
    class Config:
        env_file = ".env"


settings = Settings()