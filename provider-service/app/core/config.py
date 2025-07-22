"""
应用配置管理

集中管理所有配置项，支持从环境变量读取配置，
包含数据库、Redis、安全配置等。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import os
from functools import lru_cache
from typing import List, Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """应用配置类"""
    
    # 基础配置
    app_name: str = Field("lyss-provider-service", env="APP_NAME")
    app_version: str = Field("1.0.0", env="APP_VERSION")
    environment: str = Field("development", env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    # 服务配置
    host: str = Field("0.0.0.0", env="PROVIDER_SERVICE_HOST")
    port: int = Field(8003, env="PROVIDER_SERVICE_PORT")
    
    # 数据库配置
    database_url: str = Field(
        "postgresql://lyss:lyss123@localhost:5433/lyss_provider_db", 
        env="PROVIDER_SERVICE_DATABASE_URL"
    )
    database_pool_size: int = Field(20, env="DB_POOL_SIZE")
    database_max_overflow: int = Field(30, env="DB_MAX_OVERFLOW")
    database_echo: bool = Field(False, env="DB_ECHO")
    
    # Redis配置
    redis_url: str = Field("redis://localhost:6380/2", env="PROVIDER_SERVICE_REDIS_URL")
    redis_password: Optional[str] = Field(None, env="REDIS_PASSWORD")
    redis_db: int = Field(2, env="REDIS_DB")
    redis_pool_size: int = Field(20, env="REDIS_POOL_SIZE")
    redis_timeout: int = Field(30, env="REDIS_TIMEOUT")
    
    # JWT配置
    secret_key: str = Field("your-super-secret-jwt-key-min-32-chars", env="PROVIDER_SERVICE_JWT_SECRET")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(1440, env="JWT_EXPIRE_MINUTES")
    
    # 加密配置
    encryption_key: str = Field("your-32-char-encryption-key-here", env="PROVIDER_SERVICE_ENCRYPTION_KEY")
    encryption_algorithm: str = Field("AES-256-GCM", env="ENCRYPTION_ALGORITHM")
    
    # CORS配置
    cors_origins: List[str] = Field(
        ["http://localhost:3000", "https://lyss.dev"],
        env="CORS_ORIGINS"
    )
    cors_methods: List[str] = Field(
        ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        env="CORS_METHODS"
    )
    cors_headers: List[str] = Field(["*"], env="CORS_HEADERS")
    
    # 外部服务配置 (本地启动模式)
    user_service_url: str = Field("http://localhost:8002", env="USER_SERVICE_URL")
    auth_service_url: str = Field("http://localhost:8001", env="AUTH_SERVICE_URL")
    chat_service_url: str = Field("http://localhost:8004", env="CHAT_SERVICE_URL")
    memory_service_url: str = Field("http://localhost:8005", env="MEMORY_SERVICE_URL")
    
    # 中间件和安全配置
    enable_docs: bool = Field(True, env="ENABLE_DOCS")
    allowed_hosts: List[str] = Field(["*"], env="ALLOWED_HOSTS")
    behind_proxy: bool = Field(False, env="BEHIND_PROXY")
    
    # Redis连接配置
    redis_host: str = Field("localhost", env="REDIS_HOST")
    redis_port: int = Field(6380, env="REDIS_PORT")
    
    # API限流配置
    rate_limit_per_user: dict = Field({
        "requests_per_minute": 100,
        "requests_per_hour": 1000
    }, env="RATE_LIMIT_PER_USER")
    rate_limit_per_ip: dict = Field({
        "requests_per_minute": 30,
        "requests_per_hour": 500
    }, env="RATE_LIMIT_PER_IP")
    rate_limit_storage_url: str = Field("redis://localhost:6380/3", env="RATE_LIMIT_STORAGE_URL")
    
    # Channel健康检查配置
    health_check_interval: int = Field(60, env="HEALTH_CHECK_INTERVAL")
    health_check_timeout: int = Field(30, env="HEALTH_CHECK_TIMEOUT")
    health_check_max_retries: int = Field(3, env="HEALTH_CHECK_MAX_RETRIES")
    health_check_retry_delay: int = Field(5, env="HEALTH_CHECK_RETRY_DELAY")
    
    # 供应商API配置
    default_provider_timeout: int = Field(30, env="DEFAULT_PROVIDER_TIMEOUT")
    default_provider_max_retries: int = Field(3, env="DEFAULT_PROVIDER_MAX_RETRIES")
    default_provider_retry_delay: int = Field(1, env="DEFAULT_PROVIDER_RETRY_DELAY")
    
    # 负载均衡配置
    load_balancer_algorithm: str = Field("weighted_random", env="LOAD_BALANCER_ALGORITHM")
    load_balancer_health_factor: float = Field(0.8, env="LOAD_BALANCER_HEALTH_FACTOR")
    load_balancer_response_time_factor: float = Field(0.2, env="LOAD_BALANCER_RESPONSE_TIME_FACTOR")
    
    # 监控配置
    enable_request_logging: bool = Field(True, env="ENABLE_REQUEST_LOGGING")
    enable_performance_metrics: bool = Field(True, env="ENABLE_PERFORMANCE_METRICS")
    enable_health_checks: bool = Field(True, env="ENABLE_HEALTH_CHECKS")
    log_request_body: bool = Field(False, env="LOG_REQUEST_BODY")
    log_response_body: bool = Field(False, env="LOG_RESPONSE_BODY")
    
    # Channel管理配置
    default_channel_priority: int = Field(1, env="DEFAULT_CHANNEL_PRIORITY")
    default_channel_weight: int = Field(100, env="DEFAULT_CHANNEL_WEIGHT")
    default_max_requests_per_minute: int = Field(1000, env="DEFAULT_MAX_REQUESTS_PER_MINUTE")
    min_channel_success_rate: float = Field(0.8, env="MIN_CHANNEL_SUCCESS_RATE")
    
    # 请求日志配置
    request_log_retention_days: int = Field(30, env="REQUEST_LOG_RETENTION_DAYS")
    cleanup_schedule: str = Field("0 2 * * *", env="CLEANUP_SCHEDULE")
    enable_auto_cleanup: bool = Field(True, env="ENABLE_AUTO_CLEANUP")
    
    # 配额管理配置
    default_daily_request_limit: int = Field(10000, env="DEFAULT_DAILY_REQUEST_LIMIT")
    default_daily_token_limit: int = Field(1000000, env="DEFAULT_DAILY_TOKEN_LIMIT")
    default_monthly_request_limit: int = Field(300000, env="DEFAULT_MONTHLY_REQUEST_LIMIT")
    default_monthly_token_limit: int = Field(30000000, env="DEFAULT_MONTHLY_TOKEN_LIMIT")
    quota_reset_timezone: str = Field("Asia/Shanghai", env="QUOTA_RESET_TIMEZONE")
    
    # 缓存配置
    cache_provider_configs_ttl: int = Field(3600, env="CACHE_PROVIDER_CONFIGS_TTL")
    cache_channel_metrics_ttl: int = Field(300, env="CACHE_CHANNEL_METRICS_TTL")
    cache_health_status_ttl: int = Field(60, env="CACHE_HEALTH_STATUS_TTL")
    cache_credentials_ttl: int = Field(1800, env="CACHE_CREDENTIALS_TTL")
    
    # 开发环境配置
    dev_auto_reload: bool = Field(True, env="DEV_AUTO_RELOAD")
    dev_mock_credentials: bool = Field(False, env="DEV_MOCK_CREDENTIALS")
    dev_bypass_auth: bool = Field(False, env="DEV_BYPASS_AUTH")
    
    # OpenTelemetry配置
    otel_endpoint: Optional[str] = Field(None, env="OTEL_EXPORTER_OTLP_ENDPOINT")
    otel_service_name: str = Field("lyss-provider-service", env="OTEL_SERVICE_NAME")
    otel_service_version: str = Field("1.0.0", env="OTEL_SERVICE_VERSION")
    enable_tracing: bool = Field(False, env="ENABLE_TRACING")
    
    # Prometheus配置
    prometheus_metrics_path: str = Field("/metrics", env="PROMETHEUS_METRICS_PATH")
    enable_prometheus: bool = Field(False, env="ENABLE_PROMETHEUS")
    
    # 安全配置
    secure_cookies: bool = Field(False, env="SECURE_COOKIES")
    secure_headers: bool = Field(False, env="SECURE_HEADERS")
    force_https: bool = Field(False, env="FORCE_HTTPS")
    
    # 文件配置
    max_request_size: int = Field(10485760, env="MAX_REQUEST_SIZE")  # 10MB
    max_upload_size: int = Field(52428800, env="MAX_UPLOAD_SIZE")   # 50MB
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        
    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.environment.lower() == "development"
    
    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.environment.lower() == "production"
    
    @property
    def is_testing(self) -> bool:
        """是否为测试环境"""
        return self.environment.lower() == "testing"


@lru_cache()
def get_settings() -> Settings:
    """获取配置实例（缓存）"""
    return Settings()