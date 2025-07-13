# -*- coding: utf-8 -*-
"""
Tenant Service 主应用入口

FastAPI应用的主要配置和启动
"""

import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import structlog

from .config import get_settings
from .core.database import init_db, close_db
from .routers import health

# 获取配置
settings = get_settings()

# 配置结构化日志
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(ensure_ascii=False)
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理"""
    # 启动时执行
    logger.info("正在启动 Tenant Service", version=settings.version)
    
    # 初始化数据库
    try:
        await init_db()
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.error("数据库初始化失败", error=str(e))
        raise
    
    yield
    
    # 关闭时执行
    logger.info("正在关闭 Tenant Service")
    await close_db()
    logger.info("Tenant Service 已关闭")


# 创建FastAPI应用
app = FastAPI(
    title="Lyss AI Platform - Tenant Service",
    description="租户管理服务：负责租户管理、用户管理、供应商凭证管理等核心业务数据操作",
    version=settings.version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置受信任主机（生产环境）
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", settings.host]
    )


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next) -> Response:
    """请求日志中间件"""
    # 生成请求ID
    request_id = str(uuid.uuid4())
    
    # 记录请求开始
    logger.info(
        "请求开始",
        request_id=request_id,
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    # 处理请求
    try:
        response = await call_next(request)
        
        # 记录请求完成
        logger.info(
            "请求完成",
            request_id=request_id,
            status_code=response.status_code,
            method=request.method,
            url=str(request.url)
        )
        
        # 添加请求ID到响应头
        response.headers["X-Request-ID"] = request_id
        
        return response
        
    except Exception as e:
        # 记录请求错误
        logger.error(
            "请求处理失败",
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            error=str(e)
        )
        raise


# 导入所有路由模块
from .routers import health, internal, tenants, users, suppliers

# 注册路由
app.include_router(health.router, tags=["健康检查"])
app.include_router(internal.router, tags=["内部服务接口"])

# 根路径
@app.get("/", summary="服务信息")
async def root():
    """获取服务基本信息"""
    return {
        "service": "lyss-tenant-service",
        "version": settings.version,
        "status": "running",
        "environment": settings.environment
    }