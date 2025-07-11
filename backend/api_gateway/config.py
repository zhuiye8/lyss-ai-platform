"""
API Gateway 配置管理模块

负责管理API网关的所有配置项，包括服务注册、认证配置、CORS设置等
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class ServiceRegistry(BaseModel):
    """服务注册表配置"""
    
    auth_service: str = Field(..., description="认证服务地址")
    tenant_service: str = Field(..., description="租户服务地址")
    eino_service: str = Field(..., description="EINO服务地址")
    memory_service: str = Field(..., description="记忆服务地址")


class RouteConfig(BaseModel):
    """路由配置"""
    
    target: str = Field(..., description="目标服务地址")
    require_auth: bool = Field(True, description="是否需要认证")
    service_name: str = Field(..., description="服务名称")
    timeout: int = Field(30, description="请求超时时间(秒)")


class Settings(BaseSettings):
    """API Gateway 配置类"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="API_GATEWAY_"
    )
    
    # 服务配置
    host: str = Field(default="0.0.0.0", description="服务监听地址")
    port: int = Field(default=8000, description="服务监听端口")
    debug: bool = Field(default=False, description="调试模式")
    
    # JWT配置
    secret_key: str = Field(..., min_length=32, description="JWT签名密钥")
    algorithm: str = Field(default="HS256", description="JWT算法")
    access_token_expire_minutes: int = Field(default=30, description="访问令牌过期时间(分钟)")
    
    # CORS配置
    cors_origins: List[str] = Field(
        default=["http://localhost:3000"],
        description="允许的跨域源"
    )
    cors_allow_credentials: bool = Field(default=True, description="是否允许凭证")
    
    # 下游服务地址
    auth_service_url: str = Field(default="http://localhost:8001", env="AUTH_SERVICE_URL")
    tenant_service_url: str = Field(default="http://localhost:8002", env="TENANT_SERVICE_URL")
    eino_service_url: str = Field(default="http://localhost:8003", env="EINO_SERVICE_URL")
    memory_service_url: str = Field(default="http://localhost:8004", env="MEMORY_SERVICE_URL")
    
    # 请求配置
    request_timeout: int = Field(default=30, description="请求超时时间(秒)")
    max_request_size: int = Field(default=10 * 1024 * 1024, description="最大请求体大小(字节)")
    
    # 日志配置
    log_level: str = Field(default="INFO", description="日志级别")
    log_format: str = Field(default="json", description="日志格式")
    
    # 健康检查配置
    health_check_interval: int = Field(default=30, description="健康检查间隔(秒)")
    health_check_timeout: int = Field(default=5, description="健康检查超时(秒)")
    
    # 速率限制
    rate_limit_requests: int = Field(default=100, description="速率限制请求数")
    rate_limit_window: int = Field(default=60, description="速率限制窗口(秒)")
    
    # 环境标识
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """解析CORS源列表"""
        if isinstance(v, str):
            try:
                import json
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("secret_key")
    def validate_secret_key(cls, v):
        """验证密钥长度"""
        if len(v) < 32:
            raise ValueError("SECRET_KEY必须至少32个字符")
        return v
    
    @property
    def service_registry(self) -> ServiceRegistry:
        """获取服务注册表"""
        return ServiceRegistry(
            auth_service=self.auth_service_url,
            tenant_service=self.tenant_service_url,
            eino_service=self.eino_service_url,
            memory_service=self.memory_service_url
        )
    
    @property
    def route_config(self) -> Dict[str, RouteConfig]:
        """获取路由配置"""
        return {
            "/api/v1/auth": RouteConfig(
                target=self.auth_service_url,
                require_auth=False,
                service_name="auth_service",
                timeout=self.request_timeout
            ),
            "/api/v1/admin": RouteConfig(
                target=self.tenant_service_url,
                require_auth=True,
                service_name="tenant_service",
                timeout=self.request_timeout
            ),
            "/api/v1/chat": RouteConfig(
                target=self.eino_service_url,
                require_auth=True,
                service_name="eino_service",
                timeout=self.request_timeout
            ),
            "/api/v1/memory": RouteConfig(
                target=self.memory_service_url,
                require_auth=True,
                service_name="memory_service",
                timeout=self.request_timeout
            )
        }
    
    @property
    def security_headers(self) -> Dict[str, str]:
        """获取安全头配置"""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
        }


# 全局配置实例
settings = Settings()