"""
Lyss AI Platform API Gateway
Main entry point for the FastAPI application
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import uvicorn

from common.config import get_settings
from common.database import init_database, close_database
from common.redis_client import init_redis, close_redis
from api_gateway.middleware.auth import (
    AuthenticationMiddleware,
    RateLimitMiddleware,
    CORSMiddleware as CustomCORSMiddleware,
    AuditLogMiddleware
)
from api_gateway.routers import health
from api_gateway.routers.auth import router as auth_router


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("Starting Lyss AI Platform API Gateway...")
    
    # Initialize database
    await init_database()
    
    # Initialize Redis
    await init_redis()
    
    # Setup monitoring (TODO: 实现监控配置)
    # setup_monitoring(app)
    
    print("API Gateway started successfully!")
    
    yield
    
    # Shutdown
    print("Shutting down API Gateway...")
    
    # Close database
    await close_database()
    
    # Close Redis
    await close_redis()
    
    print("API Gateway shutdown complete!")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    openapi_url="/openapi.json" if settings.is_development else None,
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.is_development else ["api.lyss.ai", "*.lyss.ai"]
)

# Custom middleware
app.add_middleware(AuditLogMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.default_rate_limit)
app.add_middleware(AuthenticationMiddleware)

# Include routers
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(auth_router, prefix=f"{settings.api_prefix}/auth", tags=["Authentication"])

# Metrics endpoint
@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    from starlette.responses import Response
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Global exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    from datetime import datetime
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "request_id": getattr(request.state, "request_id", None),
            "timestamp": datetime.utcnow().isoformat(),
            "errors": [
                {
                    "code": f"HTTP_{exc.status_code}",
                    "message": exc.detail
                }
            ]
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    import traceback
    from datetime import datetime
    
    # Log the error
    print(f"Unhandled exception: {exc}")
    print(traceback.format_exc())
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "request_id": getattr(request.state, "request_id", None),
            "timestamp": datetime.utcnow().isoformat(),
            "errors": [
                {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred"
                }
            ]
        }
    )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Lyss AI Platform",
        "version": settings.app_version,
        "environment": settings.environment,
        "docs_url": "/docs" if settings.is_development else None
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
        log_level="info",
        access_log=True
    )