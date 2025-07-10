# -*- coding: utf-8 -*-
"""
Tenant Service 配置管理

统一管理所有配置项，支持环境变量覆盖
"""

import os
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""
    
    # ===== 服务基本配置 =====
    app_name: str = "lyss-tenant-service"
    version: str = "1.0.0"
    environment: str = "development"
    debug: bool = True
    log_level: str = "INFO"
    
    # ===== 服务端口配置 =====
    host: str = "0.0.0.0"
    port: int = 8002
    
    # ===== 数据库配置 =====
    db_host: str = "localhost"
    db_port: int = 5432
    db_username: str = "lyss_user"
    db_password: str = "lyss_dev_password_2025"
    db_database: str = "lyss_platform"
    db_pool_size: int = 20
    db_max_overflow: int = 30
    
    # ===== pgcrypto加密密钥 =====
    pgcrypto_key: str
    
    # ===== 密码策略配置 =====
    min_password_length: int = 8
    require_special_chars: bool = True
    require_numbers: bool = True
    require_uppercase: bool = True
    
    # ===== 速率限制配置 =====
    max_requests_per_minute: int = 100
    rate_limit_window: int = 60
    
    # ===== 审计日志配置 =====
    audit_log_enabled: bool = True
    audit_log_level: str = "INFO"
    
    # ===== 日志配置 =====
    log_format: str = "json"
    log_file_path: Optional[str] = None
    
    @field_validator("pgcrypto_key")
    @classmethod
    def validate_pgcrypto_key(cls, v: str) -> str:
        """验证加密密钥长度"""
        if len(v) < 32:
            raise ValueError("pgcrypto密钥长度必须至少32字符")
        return v
    
    @property
    def database_url(self) -> str:
        """构建数据库连接URL"""
        return (
            f"postgresql+asyncpg://{self.db_username}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_database}"
        )
    
    @property
    def sync_database_url(self) -> str:
        """构建同步数据库连接URL（用于迁移）"""
        return (
            f"postgresql://{self.db_username}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_database}"
        )
    
    model_config = {
        "env_file": ".env",
        "env_prefix": "TENANT_SERVICE_",
        "case_sensitive": False
    }


# 全局配置实例
settings = Settings()


def get_settings() -> Settings:
    """获取配置实例"""
    return settings