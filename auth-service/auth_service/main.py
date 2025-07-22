"""
Auth Service FastAPI主应用
Lyss AI Platform 认证服务入口点
严格遵循微服务架构和API设计规范
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .middleware.error_handler import ErrorHandlerMiddleware
from .middleware.request_logging import RequestLoggingMiddleware
from .middleware.auth_middleware import AuthenticationMiddleware, SecurityHeadersMiddleware
from .middleware.rate_limit_middleware import RateLimitMiddleware
from .middleware.monitoring_middleware import MonitoringMiddleware
from .routers import health, auth, auth_v2, oauth2, mfa, security_policy, tokens, internal
from .utils.redis_client import redis_client
from .utils.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    
    # 启动时初始化
    logger.info("正在启动Auth Service", operation="startup")
    
    try:
        # 连接Redis
        await redis_client.connect()
        logger.info("Redis连接成功", operation="redis_connect")
        
        # 验证生产环境配置
        if settings.is_production():
            config_issues = settings.validate_production_config()
            if config_issues:
                for issue in config_issues:
                    logger.warning(f"生产环境配置问题: {issue}", operation="config_validation")
        
        logger.info(
            "Auth Service启动完成", 
            operation="startup_complete",
            data={
                "environment": settings.environment,
                "debug": settings.debug,
                "host": settings.auth_service_host,
                "port": settings.auth_service_port,
            }
        )
        
        yield  # 应用运行期间
        
    except Exception as e:
        logger.error(
            f"Auth Service启动失败: {str(e)}", 
            operation="startup_failed",
            data={"error": str(e)}
        )
        raise
    
    finally:
        # 关闭时清理
        logger.info("正在关闭Auth Service", operation="shutdown")
        
        try:
            # 断开Redis连接
            await redis_client.disconnect()
            logger.info("Redis连接已断开", operation="redis_disconnect")
            
        except Exception as e:
            logger.error(
                f"关闭过程中发生错误: {str(e)}", 
                operation="shutdown_error",
                data={"error": str(e)}
            )
        
        logger.info("Auth Service已关闭", operation="shutdown_complete")


# 创建FastAPI应用实例
app = FastAPI(
    title="Lyss Auth Service",
    description="Lyss AI Platform 专用认证服务 - 提供JWT令牌管理和用户认证功能",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,  # 生产环境关闭文档
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan,
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 添加自定义中间件（注意顺序很重要）
# 1. 监控中间件 - 最外层，记录所有请求
app.add_middleware(MonitoringMiddleware)

# 2. 安全头中间件 - 添加安全相关HTTP头
app.add_middleware(SecurityHeadersMiddleware)

# 3. 限流中间件 - 在认证之前进行限流
app.add_middleware(RateLimitMiddleware)

# 4. 认证中间件 - 处理JWT令牌验证和用户上下文注入
app.add_middleware(AuthenticationMiddleware, require_auth_by_default=False)

# 5. 错误处理中间件 - 统一错误处理和响应格式
app.add_middleware(ErrorHandlerMiddleware)

# 6. 请求日志中间件 - 最内层，记录详细的请求日志
app.add_middleware(RequestLoggingMiddleware)

# 注册路由
app.include_router(
    health.router,
    tags=["健康检查"],
)

# 原版本认证路由（OAuth2标准）
app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["用户认证（标准版）"],
)

# 增强版认证路由（企业级功能）
app.include_router(
    auth_v2.router,
    tags=["认证授权（增强版）"],
)

# OAuth2联邦认证路由
app.include_router(
    oauth2.router,
    tags=["OAuth2联邦认证"],
)

# MFA多因素认证路由
app.include_router(
    mfa.router,
    tags=["多因素认证"],
)

# 安全策略管理路由
app.include_router(
    security_policy.router,
    tags=["安全策略管理"],
)

app.include_router(
    tokens.router,
    prefix="/api/v1/auth",
    tags=["令牌管理"],
)

app.include_router(
    internal.router,
    prefix="/internal/auth",
    tags=["内部服务接口"],
)


@app.get("/", include_in_schema=False)
async def root():
    """根路径重定向"""
    return {
        "service": "Lyss Auth Service",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if settings.debug else "disabled",
    }


if __name__ == "__main__":
    import uvicorn
    
    # 直接运行时的配置
    uvicorn.run(
        "auth_service.main:app",
        host=settings.auth_service_host,
        port=settings.auth_service_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=False,  # 使用自定义日志中间件
    )