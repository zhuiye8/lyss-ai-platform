"""
Auth Service 配置管理模块
使用pydantic-settings从环境变量加载配置
严格遵循 docs/STANDARDS.md 中的环境变量命名规范
"""

from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings


class AuthServiceSettings(BaseSettings):
    """Auth Service 配置类"""

    # =================================
    # 🌍 服务基本配置
    # =================================
    auth_service_host: str = Field(default="0.0.0.0", description="服务绑定地址")
    auth_service_port: int = Field(default=8001, description="服务端口")
    environment: str = Field(default="development", description="运行环境")
    debug: bool = Field(default=True, description="调试模式")

    # =================================
    # 🔐 JWT 安全配置
    # =================================
    secret_key: str = Field(
        default="lyss_auth_jwt_secret_key_2025_replace_in_production_32chars",
        min_length=32,
        description="JWT签名密钥，生产环境必须更换",
    )
    algorithm: str = Field(default="HS256", description="JWT签名算法")
    access_token_expire_minutes: int = Field(
        default=30, description="访问令牌过期时间（分钟）"
    )
    refresh_token_expire_days: int = Field(
        default=7, description="刷新令牌过期时间（天）"
    )
    jwt_issuer: str = Field(default="lyss-auth-service", description="JWT签发者")
    jwt_audience: str = Field(default="lyss-platform", description="JWT受众")

    # =================================
    # 🗄️ Redis 缓存配置
    # =================================
    redis_host: str = Field(default="localhost", description="Redis主机地址")
    redis_port: int = Field(default=6379, description="Redis端口")
    redis_password: str = Field(default="", description="Redis密码")
    redis_db: int = Field(default=0, description="Redis数据库编号")
    redis_max_connections: int = Field(default=50, description="Redis最大连接数")

    # =================================
    # 🌐 服务依赖配置
    # =================================
    tenant_service_url: str = Field(
        default="http://localhost:8002", description="Tenant Service URL"
    )

    # =================================
    # 🔒 安全配置
    # =================================
    max_login_attempts: int = Field(
        default=10, description="同一IP最大登录尝试次数"
    )
    rate_limit_window: int = Field(default=60, description="速率限制时间窗口（秒）")

    # =================================
    # 📝 日志配置
    # =================================
    log_level: str = Field(default="INFO", description="日志级别")
    log_format: str = Field(default="json", description="日志格式")
    log_file_path: str = Field(
        default="logs/auth_service.log", description="日志文件路径"
    )

    # =================================
    # 📊 监控配置
    # =================================
    health_check_timeout: str = Field(default="10s", description="健康检查超时时间")

    # =================================
    # 🎯 CORS 配置
    # =================================
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="允许的CORS源",
    )
    cors_allow_credentials: bool = Field(default=True, description="允许CORS凭证")

    class Config:
        """Pydantic配置"""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        # 允许从环境变量读取配置
        env_prefix = ""

    def get_redis_url(self) -> str:
        """获取Redis连接URL"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        else:
            return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    def get_log_config(self) -> dict:
        """获取日志配置字典"""
        return {
            "level": self.log_level,
            "format": self.log_format,
            "file_path": self.log_file_path,
        }

    def is_production(self) -> bool:
        """判断是否为生产环境"""
        return self.environment.lower() == "production"

    def is_development(self) -> bool:
        """判断是否为开发环境"""
        return self.environment.lower() == "development"

    def validate_production_config(self) -> List[str]:
        """
        验证生产环境配置
        返回配置问题列表
        """
        issues = []

        if self.is_production():
            # 检查JWT密钥是否为默认值
            if "replace_in_production" in self.secret_key:
                issues.append("生产环境必须更换默认的JWT密钥")

            # 检查调试模式
            if self.debug:
                issues.append("生产环境应关闭调试模式")

            # 检查Redis密码
            if not self.redis_password:
                issues.append("生产环境Redis应设置密码")

        return issues


# 全局配置实例
settings = AuthServiceSettings()

# 验证生产环境配置
if settings.is_production():
    config_issues = settings.validate_production_config()
    if config_issues:
        import warnings

        for issue in config_issues:
            warnings.warn(f"生产环境配置问题: {issue}", UserWarning)