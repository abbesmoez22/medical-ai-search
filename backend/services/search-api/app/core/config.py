from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Service Configuration
    DEBUG: bool = Field(default=False)
    SERVICE_NAME: str = Field(default="search-api")
    PORT: int = Field(default=8000)
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/4")
    
    # Elasticsearch
    ELASTICSEARCH_URL: str = Field(default="http://localhost:9200")
    ELASTICSEARCH_INDEX_PREFIX: str = Field(default="medical-ai")
    
    # Security
    JWT_SECRET_KEY: str = Field(...)
    JWT_ALGORITHM: str = Field(default="HS256")
    
    # Auth Service
    AUTH_SERVICE_URL: str = Field(default="http://medical-ai-auth-service:8000")
    
    # Search Configuration
    DEFAULT_PAGE_SIZE: int = Field(default=20)
    MAX_PAGE_SIZE: int = Field(default=100)
    SEARCH_TIMEOUT: int = Field(default=30)
    CACHE_TTL_SECONDS: int = Field(default=300)  # 5 minutes
    
    class Config:
        extra = "ignore"


settings = Settings()