"""
API Gateway 主应用模块

FastAPI应用的入口点，负责应用初始化和中间件配置
"""

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.gzip import GZipMiddleware

from .config import settings
from .core.logging import setup_logging, get_logger
from .middleware.cors import setup_cors_middleware
from .middleware.request_id import RequestIdMiddleware
from .middleware.auth import AuthMiddleware, TenantContextMiddleware
from .middleware.rate_limit import RateLimitMiddleware, AdaptiveRateLimitMiddleware
from .middleware.error_handler import (
    ErrorHandlingMiddleware,
    custom_http_exception_handler,
    custom_validation_exception_handler
)
from .routers import health, proxy
from .services.base_client import service_manager
from .utils.constants import CUSTOM_HEADERS


# 设置日志
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    
    Args:
        app: FastAPI应用实例
    """
    # 启动时的操作
    logger.info("🚀 API Gateway启动中...")
    
    # 记录配置信息
    logger.info(
        "配置加载完成",
        extra={
            "environment": settings.environment,
            "debug": settings.debug,
            "cors_origins": settings.cors_origins,
            "service_registry": {
                "auth": settings.auth_service_url,
                "tenant": settings.tenant_service_url,
                "eino": settings.eino_service_url,
                "memory": settings.memory_service_url
            }
        }
    )
    
    logger.info("✅ API Gateway启动完成")
    
    yield
    
    # 关闭时的操作
    logger.info("🛑 API Gateway关闭中...")
    
    # 关闭服务客户端
    try:
        await service_manager.close_all()
        logger.info("✅ 服务客户端关闭完成")
    except Exception as e:
        logger.error(f"❌ 服务客户端关闭失败: {str(e)}")
    
    logger.info("✅ API Gateway关闭完成")


# 创建FastAPI应用实例
app = FastAPI(
    title="Lyss AI Platform API Gateway",
    description="企业级AI服务聚合与管理平台的API网关服务",
    version="1.0.0",
    debug=settings.debug,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None
)


# 添加中间件（注意顺序：后添加的先执行）
def setup_middleware():
    """设置中间件"""
    
    # 1. 错误处理中间件（最外层）
    app.add_middleware(ErrorHandlingMiddleware)
    
    # 2. Gzip压缩中间件
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # 3. 速率限制中间件（在开发环境使用自适应限制）
    if settings.debug:
        app.add_middleware(AdaptiveRateLimitMiddleware)
    else:
        app.add_middleware(RateLimitMiddleware)
    
    # 4. 租户上下文中间件
    app.add_middleware(TenantContextMiddleware)
    
    # 5. 认证中间件
    app.add_middleware(AuthMiddleware)
    
    # 6. 请求ID中间件
    app.add_middleware(RequestIdMiddleware)
    
    # 7. CORS和安全头中间件（最内层）
    setup_cors_middleware(app)


# 设置异常处理器
def setup_exception_handlers():
    """设置异常处理器"""
    
    # 自定义验证异常处理器
    app.add_exception_handler(
        RequestValidationError,
        custom_validation_exception_handler
    )


# 包含路由
def setup_routes():
    """设置路由"""
    
    # 健康检查路由
    app.include_router(health.router, tags=["健康检查"])
    
    # 代理路由
    app.include_router(proxy.router, tags=["代理服务"])


# 添加中间件请求日志
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    记录请求日志
    
    Args:
        request: 请求对象
        call_next: 下一个处理器
        
    Returns:
        响应对象
    """
    import time
    
    start_time = time.time()
    request_id = getattr(request.state, "request_id", "")
    
    # 跳过健康检查的详细日志
    if request.url.path.startswith("/health"):
        response = await call_next(request)
        return response
    
    # 记录请求开始
    logger.info(
        f"请求开始: {request.method} {request.url.path}",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params) if request.query_params else None,
            "user_agent": request.headers.get("user-agent", ""),
            "client_ip": request.client.host if request.client else "unknown",
            "operation": "request_start"
        }
    )
    
    # 处理请求
    response = await call_next(request)
    
    # 计算处理时间
    process_time = time.time() - start_time
    
    # 记录请求结束
    logger.info(
        f"请求完成: {request.method} {request.url.path} -> {response.status_code}",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": int(process_time * 1000),
            "operation": "request_complete"
        }
    )
    
    # 添加处理时间头部
    response.headers["X-Process-Time"] = str(process_time)
    
    return response


# 初始化应用
def create_app() -> FastAPI:
    """
    创建并配置FastAPI应用
    
    Returns:
        配置好的FastAPI应用实例
    """
    setup_middleware()
    setup_exception_handlers()
    setup_routes()
    
    return app

# 立即初始化应用
setup_middleware()
setup_exception_handlers()
setup_routes()


# 如果直接运行此文件，启动应用
if __name__ == "__main__":
    uvicorn.run(
        "api_gateway.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        access_log=False,  # 我们使用自定义日志
        log_config=None   # 使用我们自己的日志配置
    )


# 导出应用实例
__all__ = ["app", "create_app"]