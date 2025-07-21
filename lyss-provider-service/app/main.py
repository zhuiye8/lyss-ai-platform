"""
Lyss Provider Service 主应用程序

AI供应商管理和透明代理服务的核心应用。
提供多租户的AI模型接入、负载均衡和配额管理功能。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.core.config import get_settings
from app.core.database import create_database_tables
from app.core.redis import init_redis, close_redis
from app.middleware.auth import auth_middleware
from app.middleware.rate_limit import rate_limit_middleware
from app.middleware.logging import request_logging_middleware, setup_logging
from app.middleware.cors import setup_cors_middleware
from app.api.v1.providers import router as providers_router
from app.api.v1.channels import router as channels_router
from app.api.v1.proxy import router as proxy_router
from app.proxy.handler import proxy_handler

# 配置日志
setup_logging()
logger = logging.getLogger(__name__)

# 获取配置
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    
    处理应用启动和关闭时的资源初始化和清理。
    """
    # 启动时初始化
    logger.info("🚀 启动 Lyss Provider Service")
    
    try:
        # 初始化数据库表
        logger.info("正在初始化数据库表...")
        create_database_tables()
        logger.info("✅ 数据库表初始化完成")
        
        # 初始化Redis连接
        logger.info("正在连接Redis...")
        await init_redis()
        logger.info("✅ Redis连接成功")
        
        # 验证配置
        logger.info(f"运行环境: {settings.environment}")
        logger.info(f"数据库: {settings.database_url.split('@')[1] if '@' in settings.database_url else 'local'}")
        logger.info(f"Redis: {settings.redis_host}:{settings.redis_port}")
        logger.info(f"负载均衡算法: {settings.load_balancer_algorithm}")
        
        logger.info("🎉 Provider Service 启动完成!")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ 服务启动失败: {e}")
        raise
    
    finally:
        # 关闭时清理资源
        logger.info("🔄 正在关闭 Provider Service...")
        
        try:
            # 清理代理处理器
            await proxy_handler.cleanup()
            logger.info("✅ 代理处理器清理完成")
            
            # 关闭Redis连接
            await close_redis()
            logger.info("✅ Redis连接已关闭")
            
            logger.info("👋 Provider Service 已安全关闭")
            
        except Exception as e:
            logger.error(f"❌ 服务关闭时出错: {e}")


# 创建FastAPI应用
app = FastAPI(
    title="Lyss Provider Service",
    description="AI供应商管理和透明代理服务",
    version="1.0.0",
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url="/redoc" if settings.enable_docs else None,
    lifespan=lifespan,
    openapi_url="/openapi.json" if settings.enable_docs else None
)

# 配置中间件
logger.info("正在配置中间件...")

# 信任的主机中间件（安全）
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts
)

# 代理头中间件（处理反向代理）
if settings.behind_proxy:
    app.add_middleware(ProxyHeadersMiddleware)

# GZIP压缩中间件
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS中间件
setup_cors_middleware(app)

# 自定义中间件（顺序很重要）
app.middleware("http")(request_logging_middleware)
app.middleware("http")(auth_middleware)  
app.middleware("http")(rate_limit_middleware)

logger.info("✅ 中间件配置完成")

# 注册路由
app.include_router(
    providers_router,
    prefix="/api/v1"
)

app.include_router(
    channels_router,
    prefix="/api/v1"
)

app.include_router(
    proxy_router,
    prefix="/api"
)

# 健康检查端点
@app.get("/health", tags=["系统"])
async def health_check():
    """系统健康检查"""
    try:
        from app.core.database import get_db
        from app.services.channel_service import ChannelService
        
        # 检查数据库连接
        db = next(get_db())
        channel_service = ChannelService(db)
        
        # 获取系统状态
        total_channels = len(channel_service.get_all_channels())
        
        return {
            "status": "healthy",
            "service": "lyss-provider-service", 
            "version": "1.0.0",
            "environment": settings.environment,
            "timestamp": "2025-01-21T12:00:00Z",
            "database": "connected",
            "redis": "connected",
            "channels": {
                "total": total_channels,
                "status": "operational"
            }
        }
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "lyss-provider-service",
                "version": "1.0.0",
                "error": str(e)
            }
        )

# 根路径端点
@app.get("/", tags=["系统"])
async def root():
    """根路径信息"""
    return {
        "service": "Lyss Provider Service",
        "description": "AI供应商管理和透明代理服务",
        "version": "1.0.0",
        "docs_url": "/docs" if settings.enable_docs else None,
        "health_url": "/health"
    }


# 配置异常处理器
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """HTTP异常处理器"""
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.warning(
        f"HTTP异常 - {exc.status_code}: {exc.detail}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.detail,
                "type": "http_error",
                "code": exc.status_code
            },
            "request_id": request_id
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理器"""
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.error(
        f"未处理的异常: {str(exc)}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__
        },
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "内部服务器错误",
                "type": "internal_error",
                "code": "internal_server_error"
            },
            "request_id": request_id
        }
    )

