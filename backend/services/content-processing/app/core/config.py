from typing import List
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Service Configuration
    DEBUG: bool = Field(default=False)
    SERVICE_NAME: str = Field(default="content-processing")
    PORT: int = Field(default=8000)
    
    # Database
    DATABASE_URL: str = Field(...)
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = Field(...)
    KAFKA_TOPIC_PREFIX: str = Field(default="medical-ai-platform")
    
    # AWS S3 (for reading documents)
    AWS_ACCESS_KEY_ID: str = Field(...)
    AWS_SECRET_ACCESS_KEY: str = Field(...)
    AWS_REGION: str = Field(default="us-east-1")
    
    # Security
    JWT_SECRET_KEY: str = Field(...)
    JWT_ALGORITHM: str = Field(default="HS256")
    
    # Auth Service
    AUTH_SERVICE_URL: str = Field(default="http://medical-ai-auth-service:8000")
    
    # Processing Configuration
    MAX_TEXT_LENGTH: int = Field(default=1000000)  # 1MB text limit
    PROCESSING_TIMEOUT: int = Field(default=300)   # 5 minutes
    
    @validator('KAFKA_BOOTSTRAP_SERVERS')
    def validate_kafka_servers(cls, v):
        if isinstance(v, str):
            return [server.strip() for server in v.split(',')]
        return v
    
    class Config:
        env_file = ".env"


settings = Settings()