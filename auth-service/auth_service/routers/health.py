"""
Auth Service 健康检查路由
提供服务健康状态检查接口
"""

from fastapi import APIRouter

from ..models.schemas.response import HealthResponse
from ..services.tenant_client import tenant_client
from ..utils.redis_client import redis_client
from ..utils.logging import logger

router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="健康检查")
async def health_check():
    """
    检查Auth Service及其依赖服务的健康状态
    
    Returns:
        HealthResponse: 服务健康状态信息
    """
    dependencies = {}
    
    try:
        # 检查Redis连接
        redis_healthy = await redis_client.is_connected()
        dependencies["redis"] = "healthy" if redis_healthy else "unhealthy"
        
        # 检查Tenant Service
        tenant_service_healthy = await tenant_client.health_check()
        dependencies["tenant_service"] = "healthy" if tenant_service_healthy else "unhealthy"
        
        # 判断整体状态
        all_healthy = all(status == "healthy" for status in dependencies.values())
        overall_status = "healthy" if all_healthy else "degraded"
        
        # 记录健康检查日志
        logger.info(
            f"健康检查完成 - 状态: {overall_status}",
            operation="health_check",
            data={"dependencies": dependencies},
            success=all_healthy,
        )
        
        return HealthResponse(
            status=overall_status,
            dependencies=dependencies,
        )
        
    except Exception as e:
        # 健康检查失败
        logger.error(
            f"健康检查失败: {str(e)}",
            operation="health_check",
            data={"error": str(e)},
        )
        
        return HealthResponse(
            status="unhealthy",
            dependencies={"error": str(e)},
        )