from typing import List
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Service Configuration
    DEBUG: bool = Field(default=False)
    SERVICE_NAME: str = Field(default="search-indexing")
    PORT: int = Field(default=8000)
    
    # Database
    DATABASE_URL: str = Field(...)
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/3")
    
    # Elasticsearch
    ELASTICSEARCH_URL: str = Field(default="http://localhost:9200")
    ELASTICSEARCH_INDEX_PREFIX: str = Field(default="medical-ai")
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = Field(...)
    KAFKA_TOPIC_PREFIX: str = Field(default="medical-ai-platform")
    
    # Security
    JWT_SECRET_KEY: str = Field(...)
    JWT_ALGORITHM: str = Field(default="HS256")
    
    # Auth Service
    AUTH_SERVICE_URL: str = Field(default="http://medical-ai-auth-service:8000")
    
    # Indexing Configuration
    BATCH_SIZE: int = Field(default=100)
    INDEX_TIMEOUT: int = Field(default=30)
    
    @validator('KAFKA_BOOTSTRAP_SERVERS')
    def validate_kafka_servers(cls, v):
        if isinstance(v, str):
            return [server.strip() for server in v.split(',')]
        return v
    
    class Config:
        extra = "ignore"


settings = Settings()