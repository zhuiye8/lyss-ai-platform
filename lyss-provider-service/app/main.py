"""
FastAPI应用主入口

创建和配置FastAPI应用实例，注册所有路由和中间件。
包含启动时初始化逻辑和优雅关闭处理。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import logging

from app.core.config import settings
from app.core.database import init_db
from app.api.v1.providers import router as providers_router
from app.api.v1.channels import router as channels_router
from app.api.v1.proxy import router as proxy_router
from app.providers.registry import provider_registry
from app.channels.manager import channel_manager
from app.proxy.handler import proxy_handler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="Lyss Provider Service",
    description="多供应商管理服务 - 统一管理AI服务提供商",
    version="1.0.0",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None
)

# 添加中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# 注册路由
app.include_router(providers_router)
app.include_router(channels_router) 
app.include_router(proxy_router)

@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化操作"""
    logger.info("正在启动 Lyss Provider Service...")
    
    try:
        # 初始化数据库连接
        await init_db()
        logger.info("数据库连接初始化完成")
        
        # 初始化供应商注册表
        await provider_registry.initialize()
        logger.info("供应商注册表初始化完成")
        
        # 初始化Channel管理器
        await channel_manager.initialize()
        logger.info("Channel管理器初始化完成")
        
        logger.info("Lyss Provider Service 启动完成")
        
    except Exception as e:
        logger.error(f"服务启动失败: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理操作"""
    logger.info("正在关闭 Lyss Provider Service...")
    
    # 停止健康检查任务
    if channel_manager._health_check_task:
        channel_manager._health_check_task.cancel()
    
    # 清理代理处理器资源
    await proxy_handler.cleanup()
    
    logger.info("Lyss Provider Service 已关闭")

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "service": "lyss-provider-service",
        "version": "1.0.0",
        "providers": len(provider_registry.providers),
        "channels": len(channel_manager.channels)
    }

@app.get("/")
async def root():
    """根路径信息"""
    return {
        "service": "Lyss Provider Service",
        "description": "多供应商管理服务",
        "version": "1.0.0",
        "docs": "/docs"
    }