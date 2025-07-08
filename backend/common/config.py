"""
Configuration management for Lyss AI Platform
"""
import os
from typing import Optional, Dict, Any, List
from pydantic import BaseSettings, Field, validator
from functools import lru_cache


class DatabaseSettings(BaseSettings):
    """Database configuration"""
    host: str = Field(default="localhost", env="DB_HOST")
    port: int = Field(default=5432, env="DB_PORT")
    username: str = Field(default="lyss_user", env="DB_USERNAME")
    password: str = Field(default="lyss_password", env="DB_PASSWORD")
    database: str = Field(default="lyss_platform", env="DB_DATABASE")
    
    # Connection pool settings
    pool_size: int = Field(default=20, env="DB_POOL_SIZE")
    max_overflow: int = Field(default=30, env="DB_MAX_OVERFLOW")
    pool_timeout: int = Field(default=30, env="DB_POOL_TIMEOUT")
    
    # SSL settings
    ssl_mode: str = Field(default="prefer", env="DB_SSL_MODE")
    
    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    @property
    def sync_url(self) -> str:
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


class RedisSettings(BaseSettings):
    """Redis configuration"""
    host: str = Field(default="localhost", env="REDIS_HOST")
    port: int = Field(default=6379, env="REDIS_PORT")
    password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    db: int = Field(default=0, env="REDIS_DB")
    
    # Connection pool settings
    max_connections: int = Field(default=50, env="REDIS_MAX_CONNECTIONS")
    socket_timeout: int = Field(default=5, env="REDIS_SOCKET_TIMEOUT")
    socket_connect_timeout: int = Field(default=5, env="REDIS_SOCKET_CONNECT_TIMEOUT")
    
    @property
    def url(self) -> str:
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"


class SecuritySettings(BaseSettings):
    """Security configuration"""
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
    
    @validator('secret_key')
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError('SECRET_KEY must be at least 32 characters long')
        return v


class EINOSettings(BaseSettings):
    """EINO service configuration"""
    host: str = Field(default="localhost", env="EINO_HOST")
    port: int = Field(default=8080, env="EINO_PORT")
    timeout: int = Field(default=30, env="EINO_TIMEOUT")
    
    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


class MemorySettings(BaseSettings):
    """Memory service configuration"""
    host: str = Field(default="localhost", env="MEMORY_HOST")
    port: int = Field(default=8001, env="MEMORY_PORT")
    timeout: int = Field(default=10, env="MEMORY_TIMEOUT")
    
    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


class MonitoringSettings(BaseSettings):
    """Monitoring configuration"""
    prometheus_port: int = Field(default=8000, env="PROMETHEUS_PORT")
    jaeger_endpoint: str = Field(default="http://jaeger:14268/api/traces", env="JAEGER_ENDPOINT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Health check settings
    health_check_interval: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")
    health_check_timeout: int = Field(default=5, env="HEALTH_CHECK_TIMEOUT")


class Settings(BaseSettings):
    """Main application settings"""
    # Application info
    app_name: str = Field(default="Lyss AI Platform", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    app_description: str = Field(default="Enterprise AI Service Aggregation Platform", env="APP_DESCRIPTION")
    
    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # API settings
    api_prefix: str = Field(default="/api/v1", env="API_PREFIX")
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    
    # Component settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    eino: EINOSettings = Field(default_factory=EINOSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    
    # Tenant settings
    max_tenants: int = Field(default=1000, env="MAX_TENANTS")
    default_tenant_quota: Dict[str, Any] = Field(default_factory=lambda: {
        "max_users": 10,
        "max_conversations_per_user": 100,
        "max_api_calls_per_month": 10000,
        "max_storage_gb": 1.0,
        "max_memory_entries": 1000
    })
    
    @validator('environment')
    def validate_environment(cls, v):
        if v not in ['development', 'staging', 'production']:
            raise ValueError('Environment must be one of: development, staging, production')
        return v
    
    @validator('cors_origins', pre=True)
    def validate_cors_origins(cls, v):
        if isinstance(v, str):
            return v.split(',')
        return v
    
    @property
    def is_development(self) -> bool:
        return self.environment == 'development'
    
    @property
    def is_production(self) -> bool:
        return self.environment == 'production'
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()