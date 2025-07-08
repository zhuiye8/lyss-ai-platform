"""
Lyss AI Platform Memory Service
Main entry point for the memory management service using Mem0AI
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import uvicorn

from .config import get_settings
from .services.memory_service import MemoryService
from .api import health, memory, admin
from .utils.logging import setup_logging

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("Starting Lyss AI Platform Memory Service...")
    
    # Setup logging
    setup_logging(settings.log_level)
    
    # Initialize memory service
    memory_service = MemoryService(settings)
    await memory_service.initialize()
    
    # Store in app state
    app.state.memory_service = memory_service
    
    print("Memory Service started successfully!")
    
    yield
    
    # Shutdown
    print("Shutting down Memory Service...")
    
    # Cleanup memory service
    await memory_service.cleanup()
    
    print("Memory Service shutdown complete!")


# Create FastAPI app
app = FastAPI(
    title="Lyss AI Platform Memory Service",
    description="Memory management service using Mem0AI for personalized AI experiences",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url="/redoc" if settings.environment == "development" else None,
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(memory.router, prefix="/api/v1/memory", tags=["Memory"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Administration"])

# Metrics endpoint
@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Global exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
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
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    import traceback
    
    print(f"Unhandled exception: {exc}")
    print(traceback.format_exc())
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
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
        "message": "Lyss AI Platform Memory Service",
        "version": "1.0.0",
        "environment": settings.environment,
        "docs_url": "/docs" if settings.environment == "development" else None
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.environment == "development",
        log_level="info"
    )