"""
应用配置管理

集中管理所有配置项，支持从环境变量读取配置，
包含数据库、Redis、安全配置等。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import os
from typing import List, Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """应用配置类"""
    
    # 基础配置
    app_name: str = Field("Lyss Provider Service", env="APP_NAME")
    environment: str = Field("development", env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")
    
    # 服务配置
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8003, env="PORT")
    
    # 数据库配置
    database_url: str = Field(..., env="DATABASE_URL")
    database_pool_size: int = Field(20, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(30, env="DATABASE_MAX_OVERFLOW")
    
    # Redis配置
    redis_url: str = Field("redis://localhost:6379/2", env="REDIS_URL")
    redis_password: Optional[str] = Field(None, env="REDIS_PASSWORD")
    
    # JWT配置
    secret_key: str = Field(..., env="SECRET_KEY")
    algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # CORS配置
    allowed_origins: List[str] = Field(
        ["http://localhost:3000", "http://localhost:8000"],
        env="ALLOWED_ORIGINS"
    )
    
    # 外部服务配置
    auth_service_url: str = Field("http://localhost:8001", env="AUTH_SERVICE_URL")
    user_service_url: str = Field("http://localhost:8002", env="USER_SERVICE_URL")
    
    # 供应商配置
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    google_api_key: Optional[str] = Field(None, env="GOOGLE_API_KEY")
    deepseek_api_key: Optional[str] = Field(None, env="DEEPSEEK_API_KEY")
    
    # Channel管理配置
    health_check_interval: int = Field(60, env="HEALTH_CHECK_INTERVAL")  # 秒
    max_retries: int = Field(3, env="MAX_RETRIES")
    request_timeout: int = Field(30, env="REQUEST_TIMEOUT")  # 秒
    
    # 日志配置
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        
    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.environment == "development"
    
    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.environment == "production"


# 全局配置实例
settings = Settings()