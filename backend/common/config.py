"""
Configuration management for Lyss AI Platform
"""
import os
from typing import Optional, Dict, Any, List
from pydantic import Field, validator
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Main application settings"""
    # Application info
    app_name: str = Field(default="Lyss AI Platform", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    app_description: str = Field(default="Enterprise AI Service Aggregation Platform", env="APP_DESCRIPTION")
    
    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Security
    secret_key: str = Field(env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # Password settings
    password_min_length: int = Field(default=8, env="PASSWORD_MIN_LENGTH")
    password_require_special: bool = Field(default=True, env="PASSWORD_REQUIRE_SPECIAL")
    
    # Rate limiting
    default_rate_limit: int = Field(default=100, env="DEFAULT_RATE_LIMIT")
    burst_rate_limit: int = Field(default=200, env="BURST_RATE_LIMIT")
    
    # Database
    db_host: str = Field(default="localhost", env="DB_HOST")
    db_port: int = Field(default=5432, env="DB_PORT")
    db_username: str = Field(default="lyss_user", env="DB_USERNAME")
    db_password: str = Field(default="lyss_password", env="DB_PASSWORD")
    db_database: str = Field(default="lyss_platform", env="DB_DATABASE")
    db_ssl_mode: str = Field(default="prefer", env="DB_SSL_MODE")
    db_pool_size: int = Field(default=20, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=30, env="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(default=30, env="DB_POOL_TIMEOUT")
    print(f"实际使用的配置: {db_username}, {db_password}, {db_database}")
    
    # Redis
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_max_connections: int = Field(default=50, env="REDIS_MAX_CONNECTIONS")
    redis_socket_timeout: int = Field(default=5, env="REDIS_SOCKET_TIMEOUT")
    redis_socket_connect_timeout: int = Field(default=5, env="REDIS_SOCKET_CONNECT_TIMEOUT")
    
    # API settings
    api_prefix: str = Field(default="/api/v1", env="API_PREFIX")
    cors_origins: str = Field(default="*", env="CORS_ORIGINS")
    
    # EINO service
    eino_host: str = Field(default="localhost", env="EINO_HOST")
    eino_port: int = Field(default=8080, env="EINO_PORT")
    eino_timeout: int = Field(default=30, env="EINO_TIMEOUT")
    
    # Memory service
    memory_host: str = Field(default="localhost", env="MEMORY_HOST")
    memory_port: int = Field(default=8001, env="MEMORY_PORT")
    memory_timeout: int = Field(default=10, env="MEMORY_TIMEOUT")
    
    # Monitoring
    prometheus_port: int = Field(default=8000, env="PROMETHEUS_PORT")
    jaeger_endpoint: str = Field(default="http://jaeger:14268/api/traces", env="JAEGER_ENDPOINT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    health_check_interval: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")
    health_check_timeout: int = Field(default=5, env="HEALTH_CHECK_TIMEOUT")
    
    # Tenant settings
    max_tenants: int = Field(default=1000, env="MAX_TENANTS")
    default_tenant_quota: Dict[str, Any] = Field(default_factory=lambda: {
        "max_users": 10,
        "max_conversations_per_user": 100,
        "max_api_calls_per_month": 10000,
        "max_storage_gb": 1.0,
        "max_memory_entries": 1000
    })
    
    @validator('secret_key')
    def validate_secret_key(cls, v):
        """验证密钥长度"""
        if len(v) < 32:
            raise ValueError('SECRET_KEY must be at least 32 characters long')
        return v
    
    @validator('environment')
    def validate_environment(cls, v):
        """验证环境配置"""
        if v not in ['development', 'staging', 'production']:
            raise ValueError('Environment must be one of: development, staging, production')
        return v
    
    @property
    def cors_origins_list(self) -> List[str]:
        """将CORS origins字符串转换为列表"""
        if isinstance(self.cors_origins, str):
            return [origin.strip() for origin in self.cors_origins.split(',')]
        return self.cors_origins
    
    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.environment == 'development'
    
    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.environment == 'production'
    
    @property
    def database_url(self) -> str:
        """数据库连接URL"""
        return f"postgresql+asyncpg://{self.db_username}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_database}"
    
    @property
    def database_sync_url(self) -> str:
        """同步数据库连接URL"""
        return f"postgresql://{self.db_username}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_database}"
    
    @property
    def redis_url(self) -> str:
        """Redis连接URL"""
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    @property
    def eino_url(self) -> str:
        """EINO服务URL"""
        return f"http://{self.eino_host}:{self.eino_port}"
    
    @property
    def memory_url(self) -> str:
        """Memory服务URL"""
        return f"http://{self.memory_host}:{self.memory_port}"
    
    class Config:
        env_file = "../.env"  # 从根目录加载.env文件
        case_sensitive = False
        extra = "ignore"  # 忽略额外的环境变量


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()