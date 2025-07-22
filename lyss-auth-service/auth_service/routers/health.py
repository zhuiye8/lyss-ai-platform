"""
Auth Service 健康检查路由
提供服务健康状态检查接口
"""

from fastapi import APIRouter, Request
from typing import Optional

from ..models.schemas.response import HealthResponse
from ..utils.redis_client import redis_client
from ..utils.logging import logger
from ..dependencies import get_settings, SettingsDep

router = APIRouter()


@router.get("/health", summary="健康检查")
async def health_check(request: Request, settings: SettingsDep):
    """
    检查Auth Service及其依赖服务的健康状态
    
    Returns:
        dict: 服务健康状态信息，包括监控指标
    """
    dependencies = {}
    
    try:
        # 检查Redis连接
        redis_healthy = await redis_client.is_connected()
        dependencies["redis"] = "healthy" if redis_healthy else "unhealthy"
        
        # 判断整体状态
        all_healthy = all(status == "healthy" for status in dependencies.values())
        overall_status = "healthy" if all_healthy else "degraded"
        
        # 获取监控指标（如果有）
        metrics = {}
        try:
            # 从请求获取监控中间件
            if hasattr(request.app, 'user_middleware'):
                from ..middleware.monitoring_middleware import MonitoringMiddleware
                for middleware in request.app.user_middleware:
                    if isinstance(middleware.cls, type) and issubclass(middleware.cls, MonitoringMiddleware):
                        if hasattr(middleware, 'kwargs') and 'instance' in middleware.kwargs:
                            monitoring_instance = middleware.kwargs['instance']
                            metrics = monitoring_instance.get_current_metrics()
                            break
        except Exception as e:
            logger.debug(f"获取监控指标失败: {str(e)}")
        
        # 记录健康检查日志
        logger.info(
            f"健康检查完成 - 状态: {overall_status}",
            operation="health_check",
            data={"dependencies": dependencies},
            success=all_healthy,
        )
        
        response_data = {
            "service": "lyss-auth-service",
            "version": "1.0.0",
            "status": overall_status,
            "timestamp": logger._get_timestamp(),
            "environment": settings.environment,
            "dependencies": dependencies
        }
        
        if metrics:
            response_data["metrics"] = metrics
        
        return response_data
        
    except Exception as e:
        # 健康检查失败
        logger.error(
            f"健康检查失败: {str(e)}",
            operation="health_check",
            data={"error": str(e)},
        )
        
        return {
            "service": "lyss-auth-service", 
            "version": "1.0.0",
            "status": "unhealthy",
            "timestamp": logger._get_timestamp(),
            "error": str(e),
            "dependencies": {"error": str(e)}
        }


@router.get("/metrics", summary="监控指标")
async def get_metrics(request: Request, time_range: Optional[str] = "hour"):
    """
    获取详细的监控指标数据
    
    Args:
        time_range: 时间范围 (minute, hour)
        
    Returns:
        dict: 详细的监控指标
    """
    try:
        # 简化版指标返回（实际应该从监控中间件获取）
        basic_metrics = {
            "service": "lyss-auth-service",
            "timestamp": logger._get_timestamp(),
            "time_range": time_range,
            "request_count": 0,
            "error_count": 0,
            "avg_response_time": 0.0,
            "error_rate": 0.0,
            "active_connections": 0
        }
        
        return {
            "success": True,
            "data": basic_metrics,
            "message": "监控指标获取成功"
        }
        
    except Exception as e:
        logger.error(
            f"获取监控指标失败: {str(e)}",
            operation="get_metrics",
            data={"error": str(e)}
        )
        
        return {
            "success": False,
            "error": str(e),
            "message": "监控指标获取失败"
        }