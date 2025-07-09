"""
Health check endpoints
"""
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from common.database import get_async_session, db_manager
from common.redis_client import redis_manager
from common.config import get_settings

router = APIRouter()
settings = get_settings()


async def check_database_health() -> Dict[str, Any]:
    """Check database health"""
    try:
        health = await db_manager.health_check()
        return {
            "status": "healthy" if health else "unhealthy",
            "details": "Database connection successful" if health else "Database connection failed"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "details": f"Database error: {str(e)}"
        }


async def check_redis_health() -> Dict[str, Any]:
    """Check Redis health"""
    try:
        health = await redis_manager.health_check()
        return {
            "status": "healthy" if health else "unhealthy",
            "details": "Redis connection successful" if health else "Redis connection failed"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "details": f"Redis error: {str(e)}"
        }


async def check_external_services() -> Dict[str, Any]:
    """Check external services health"""
    services = {}
    
    # Check EINO service
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.eino_url}/health", timeout=5.0)
            services["eino_service"] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "details": f"HTTP {response.status_code}"
            }
    except Exception as e:
        services["eino_service"] = {
            "status": "unhealthy",
            "details": f"Connection error: {str(e)}"
        }
    
    # Check Memory service
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.memory_url}/health", timeout=5.0)
            services["memory_service"] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "details": f"HTTP {response.status_code}"
            }
    except Exception as e:
        services["memory_service"] = {
            "status": "unhealthy",
            "details": f"Connection error: {str(e)}"
        }
    
    return services


@router.get("/")
async def health_check():
    """Basic health check"""
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.app_version,
            "environment": settings.environment
        },
        "message": "Service is healthy"
    }


@router.get("/detailed")
async def detailed_health_check():
    """Detailed health check including dependencies"""
    
    # Check all services
    database_health = await check_database_health()
    redis_health = await check_redis_health()
    external_services = await check_external_services()
    
    # Determine overall status
    all_services = {
        "database": database_health,
        "redis": redis_health,
        **external_services
    }
    
    overall_healthy = all(
        service["status"] == "healthy" 
        for service in all_services.values()
    )
    
    response_data = {
        "status": "healthy" if overall_healthy else "unhealthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "environment": settings.environment,
        "services": all_services,
        "uptime_seconds": 0,  # TODO: Implement uptime tracking
        "checks_passed": sum(1 for s in all_services.values() if s["status"] == "healthy"),
        "total_checks": len(all_services)
    }
    
    status_code = 200 if overall_healthy else 503
    
    return {
        "success": overall_healthy,
        "data": response_data,
        "message": "All services healthy" if overall_healthy else "Some services unhealthy"
    }


@router.get("/readiness")
async def readiness_check():
    """Kubernetes readiness probe"""
    try:
        # Check critical dependencies
        db_health = await check_database_health()
        redis_health = await check_redis_health()
        
        is_ready = (
            db_health["status"] == "healthy" and 
            redis_health["status"] == "healthy"
        )
        
        if not is_ready:
            raise HTTPException(status_code=503, detail="Service not ready")
        
        return {
            "success": True,
            "data": {
                "status": "ready",
                "timestamp": datetime.utcnow().isoformat()
            },
            "message": "Service is ready"
        }
    
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service not ready: {str(e)}")


@router.get("/liveness")
async def liveness_check():
    """Kubernetes liveness probe"""
    return {
        "success": True,
        "data": {
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.app_version
        },
        "message": "Service is alive"
    }