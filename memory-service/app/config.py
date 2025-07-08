"""
Configuration management for Memory Service
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseSettings, Field
from functools import lru_cache


class RedisSettings(BaseSettings):
    """Redis configuration"""
    host: str = Field(default="localhost", env="REDIS_HOST")
    port: int = Field(default=6379, env="REDIS_PORT")
    password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    db: int = Field(default=1, env="REDIS_DB")  # Use different DB from main app
    
    @property
    def url(self) -> str:
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"


class VectorDBSettings(BaseSettings):
    """Vector database configuration"""
    provider: str = Field(default="redis", env="VECTOR_DB_PROVIDER")  # redis, qdrant, chroma, weaviate
    
    # Qdrant settings
    qdrant_host: str = Field(default="localhost", env="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, env="QDRANT_PORT")
    qdrant_api_key: Optional[str] = Field(default=None, env="QDRANT_API_KEY")
    
    # Chroma settings
    chroma_host: str = Field(default="localhost", env="CHROMA_HOST")
    chroma_port: int = Field(default=8000, env="CHROMA_PORT")
    
    # Weaviate settings
    weaviate_url: str = Field(default="http://localhost:8080", env="WEAVIATE_URL")
    weaviate_api_key: Optional[str] = Field(default=None, env="WEAVIATE_API_KEY")


class EmbeddingSettings(BaseSettings):
    """Embedding model configuration"""
    provider: str = Field(default="sentence-transformers", env="EMBEDDING_PROVIDER")
    model_name: str = Field(default="all-MiniLM-L6-v2", env="EMBEDDING_MODEL")
    
    # OpenAI settings (if using OpenAI embeddings)
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="text-embedding-ada-002", env="OPENAI_EMBEDDING_MODEL")
    
    # Model parameters
    max_sequence_length: int = Field(default=512, env="EMBEDDING_MAX_LENGTH")
    batch_size: int = Field(default=32, env="EMBEDDING_BATCH_SIZE")


class MemorySettings(BaseSettings):
    """Memory service specific settings"""
    # Memory retention
    default_retention_days: int = Field(default=365, env="MEMORY_RETENTION_DAYS")
    max_memories_per_user: int = Field(default=10000, env="MAX_MEMORIES_PER_USER")
    
    # Search parameters
    default_search_limit: int = Field(default=10, env="DEFAULT_SEARCH_LIMIT")
    max_search_limit: int = Field(default=100, env="MAX_SEARCH_LIMIT")
    similarity_threshold: float = Field(default=0.7, env="SIMILARITY_THRESHOLD")
    
    # Memory processing
    enable_auto_categorization: bool = Field(default=True, env="ENABLE_AUTO_CATEGORIZATION")
    enable_importance_scoring: bool = Field(default=True, env="ENABLE_IMPORTANCE_SCORING")
    enable_memory_consolidation: bool = Field(default=True, env="ENABLE_MEMORY_CONSOLIDATION")
    
    # Background tasks
    cleanup_interval_hours: int = Field(default=24, env="CLEANUP_INTERVAL_HOURS")
    consolidation_interval_hours: int = Field(default=168, env="CONSOLIDATION_INTERVAL_HOURS")  # Weekly


class Settings(BaseSettings):
    """Main application settings"""
    # Application info
    app_name: str = Field(default="Lyss Memory Service", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # Server settings
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8001, env="PORT")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Security
    secret_key: str = Field(env="SECRET_KEY")
    
    # Component settings
    redis: RedisSettings = Field(default_factory=RedisSettings)
    vector_db: VectorDBSettings = Field(default_factory=VectorDBSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    
    # External services
    api_gateway_url: str = Field(default="http://localhost:8000", env="API_GATEWAY_URL")
    
    # Monitoring
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    jaeger_endpoint: str = Field(default="http://jaeger:14268/api/traces", env="JAEGER_ENDPOINT")
    
    @property
    def is_development(self) -> bool:
        return self.environment == "development"
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()