"""
Configuration management for Memory Service
符合Mem0AI官方标准的配置
"""
from typing import Optional, List, Dict, Any
from pydantic import Field
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Memory服务主配置类 - 符合Mem0AI标准"""
    
    # ===========================================
    # 基础应用配置
    # ===========================================
    app_name: str = Field(default="Lyss Memory Service", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # 服务配置
    host: str = Field(default="localhost", env="MEMORY_HOST")
    port: int = Field(default=8001, env="MEMORY_PORT")
    timeout: int = Field(default=30, env="MEMORY_TIMEOUT")
    
    # 安全配置
    secret_key: str = Field(env="SECRET_KEY")
    
    # 日志配置
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # ===========================================
    # Mem0AI核心配置 (符合官方标准)
    # ===========================================
    
    # 必需的OpenAI配置 (Mem0AI默认LLM)
    openai_api_key: str = Field(env="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", env="OPENAI_BASE_URL")
    openai_embedding_model: str = Field(default="text-embedding-ada-002", env="OPENAI_EMBEDDING_MODEL")
    
    # ===========================================
    # 数据库配置
    # ===========================================
    
    # Redis配置 (用于向量存储)
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_db: int = Field(default=1, env="REDIS_DB")  # 使用不同的DB避免冲突
    
    # PostgreSQL配置 (用于元数据存储)
    db_host: str = Field(default="localhost", env="DB_HOST")
    db_port: int = Field(default=5432, env="DB_PORT")
    db_username: str = Field(default="lyss_dev_user", env="DB_USERNAME")
    db_password: str = Field(default="lyss_dev_password", env="DB_PASSWORD")
    db_database: str = Field(default="lyss_platform_dev", env="DB_DATABASE")
    
    # ===========================================
    # 向量数据库配置
    # ===========================================
    
    # 向量数据库提供商 (redis, qdrant, chroma, weaviate)
    vector_db_provider: str = Field(default="redis", env="VECTOR_DB_PROVIDER")
    
    # Qdrant配置
    qdrant_host: str = Field(default="localhost", env="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, env="QDRANT_PORT")
    qdrant_api_key: Optional[str] = Field(default=None, env="QDRANT_API_KEY")
    
    # ===========================================
    # Embedding配置
    # ===========================================
    
    # Embedding提供商 (sentence-transformers, openai, huggingface)
    embedding_provider: str = Field(default="sentence-transformers", env="EMBEDDING_PROVIDER")
    embedding_model: str = Field(default="all-MiniLM-L6-v2", env="EMBEDDING_MODEL")
    embedding_max_length: int = Field(default=512, env="EMBEDDING_MAX_LENGTH")
    embedding_batch_size: int = Field(default=32, env="EMBEDDING_BATCH_SIZE")
    
    # ===========================================
    # Memory服务配置
    # ===========================================
    
    # Memory保留和限制
    memory_retention_days: int = Field(default=365, env="MEMORY_RETENTION_DAYS")
    max_memories_per_user: int = Field(default=10000, env="MAX_MEMORIES_PER_USER")
    
    # 搜索配置
    default_search_limit: int = Field(default=10, env="DEFAULT_SEARCH_LIMIT")
    max_search_limit: int = Field(default=100, env="MAX_SEARCH_LIMIT")
    similarity_threshold: float = Field(default=0.7, env="SIMILARITY_THRESHOLD")
    
    # 功能开关
    enable_auto_categorization: bool = Field(default=True, env="ENABLE_AUTO_CATEGORIZATION")
    enable_importance_scoring: bool = Field(default=True, env="ENABLE_IMPORTANCE_SCORING")
    enable_memory_consolidation: bool = Field(default=True, env="ENABLE_MEMORY_CONSOLIDATION")
    
    # 后台任务配置
    cleanup_interval_hours: int = Field(default=24, env="CLEANUP_INTERVAL_HOURS")
    consolidation_interval_hours: int = Field(default=168, env="CONSOLIDATION_INTERVAL_HOURS")
    
    # ===========================================
    # 外部服务配置
    # ===========================================
    
    # API网关配置
    api_gateway_url: str = Field(default="http://localhost:8000", env="VITE_API_URL")
    
    # 监控配置
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    jaeger_endpoint: str = Field(default="http://localhost:14268/api/traces", env="JAEGER_ENDPOINT")
    
    # ===========================================
    # 计算属性
    # ===========================================
    
    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.environment == "development"
    
    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.environment == "production"
    
    @property
    def redis_url(self) -> str:
        """Redis连接URL"""
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    @property
    def database_url(self) -> str:
        """数据库连接URL"""
        return f"postgresql://{self.db_username}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_database}"
    
    @property
    def mem0_config(self) -> Dict[str, Any]:
        """
        生成符合Mem0AI标准的配置字典
        """
        config = {
            "llm": {
                "provider": "openai",
                "config": {
                    "model": "gpt-4o-mini",
                    "temperature": 0.1,
                    "max_tokens": 1000,
                    "api_key": self.openai_api_key,
                    "base_url": self.openai_base_url
                }
            },
            "embedder": {
                "provider": self.embedding_provider,
                "config": {
                    "model": self.embedding_model,
                    "embedding_dims": 384 if self.embedding_model == "all-MiniLM-L6-v2" else 1536,
                    "batch_size": self.embedding_batch_size
                }
            },
            "vector_store": {
                "provider": self.vector_db_provider,
                "config": {
                    "host": self.redis_host,
                    "port": self.redis_port,
                    "password": self.redis_password,
                    "db": self.redis_db
                }
            },
            "version": "v1.1"
        }
        
        # 如果使用OpenAI embedding，更新配置
        if self.embedding_provider == "openai":
            config["embedder"] = {
                "provider": "openai",
                "config": {
                    "model": self.openai_embedding_model,
                    "api_key": self.openai_api_key,
                    "base_url": self.openai_base_url
                }
            }
        
        return config
    
    class Config:
        env_file = "../.env"  # 从根目录加载.env文件
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """获取缓存的配置实例"""
    return Settings()


# 全局配置实例
settings = get_settings()