"""
健康检查路由模块

提供API Gateway和下游服务的健康检查接口
"""

from typing import Dict, Any
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse

from ..services.base_client import service_manager
from ..core.dependencies import get_request_id
from ..core.logging import get_logger
from ..utils.helpers import build_success_response, build_error_response
from ..utils.constants import HEALTH_STATUS
from ..config import settings


logger = get_logger(__name__)
router = APIRouter()


@router.get("/health", summary="健康检查", description="检查API Gateway和所有下游服务的健康状态")
async def health_check(
    request: Request,
    request_id: str = Depends(get_request_id)
) -> JSONResponse:
    """
    健康检查接口
    
    Args:
        request: FastAPI请求对象
        request_id: 请求ID
        
    Returns:
        健康检查结果
    """
    try:
        # 检查所有下游服务的健康状态
        service_health = await service_manager.health_check_all(request_id)
        
        # 计算总体健康状态
        overall_status = _calculate_overall_health(service_health)
        
        # 构建响应数据
        health_data = {
            "status": overall_status,
            "version": "1.0.0",
            "timestamp": None,  # 会在build_success_response中设置
            "services": service_health,
            "gateway": {
                "status": HEALTH_STATUS["HEALTHY"],
                "version": "1.0.0",
                "environment": settings.environment,
                "debug": settings.debug
            }
        }
        
        # 记录健康检查日志
        logger.info(
            f"健康检查完成: {overall_status}",
            extra={
                "request_id": request_id,
                "operation": "health_check",
                "overall_status": overall_status,
                "service_count": len(service_health),
                "healthy_services": len([s for s in service_health.values() if s.get("status") == "healthy"])
            }
        )
        
        # 根据健康状态设置HTTP状态码
        if overall_status == HEALTH_STATUS["HEALTHY"]:
            status_code = 200
        elif overall_status == HEALTH_STATUS["DEGRADED"]:
            status_code = 207  # Multi-Status
        else:
            status_code = 503  # Service Unavailable
        
        response = build_success_response(
            data=health_data,
            message=f"服务状态: {overall_status}",
            request_id=request_id
        )
        
        return JSONResponse(content=response, status_code=status_code)
        
    except Exception as e:
        logger.error(
            f"健康检查失败: {str(e)}",
            extra={
                "request_id": request_id,
                "operation": "health_check",
                "error": str(e)
            }
        )
        
        error_response = build_error_response(
            error_code="5003",
            message=f"健康检查失败: {str(e)}",
            details={"error": str(e)},
            request_id=request_id
        )
        
        return JSONResponse(content=error_response, status_code=500)


@router.get("/health/simple", summary="简单健康检查", description="返回简单的健康状态")
async def simple_health_check(
    request: Request,
    request_id: str = Depends(get_request_id)
) -> JSONResponse:
    """
    简单健康检查接口
    
    Args:
        request: FastAPI请求对象
        request_id: 请求ID
        
    Returns:
        简单的健康检查结果
    """
    try:
        response = build_success_response(
            data={
                "status": HEALTH_STATUS["HEALTHY"],
                "service": "api_gateway",
                "version": "1.0.0"
            },
            message="API Gateway运行正常",
            request_id=request_id
        )
        
        return JSONResponse(content=response, status_code=200)
        
    except Exception as e:
        error_response = build_error_response(
            error_code="5003",
            message=f"健康检查失败: {str(e)}",
            request_id=request_id
        )
        
        return JSONResponse(content=error_response, status_code=500)


@router.get("/health/services", summary="服务健康检查", description="检查所有下游服务的健康状态")
async def services_health_check(
    request: Request,
    request_id: str = Depends(get_request_id)
) -> JSONResponse:
    """
    服务健康检查接口
    
    Args:
        request: FastAPI请求对象
        request_id: 请求ID
        
    Returns:
        下游服务的健康检查结果
    """
    try:
        # 检查所有下游服务的健康状态
        service_health = await service_manager.health_check_all(request_id)
        
        # 计算总体健康状态
        overall_status = _calculate_overall_health(service_health)
        
        response = build_success_response(
            data={
                "overall_status": overall_status,
                "services": service_health
            },
            message=f"服务检查完成: {overall_status}",
            request_id=request_id
        )
        
        # 根据健康状态设置HTTP状态码
        if overall_status == HEALTH_STATUS["HEALTHY"]:
            status_code = 200
        elif overall_status == HEALTH_STATUS["DEGRADED"]:
            status_code = 207
        else:
            status_code = 503
        
        return JSONResponse(content=response, status_code=status_code)
        
    except Exception as e:
        logger.error(
            f"服务健康检查失败: {str(e)}",
            extra={
                "request_id": request_id,
                "operation": "services_health_check",
                "error": str(e)
            }
        )
        
        error_response = build_error_response(
            error_code="5003",
            message=f"服务健康检查失败: {str(e)}",
            details={"error": str(e)},
            request_id=request_id
        )
        
        return JSONResponse(content=error_response, status_code=500)


def _calculate_overall_health(service_health: Dict[str, Any]) -> str:
    """
    计算总体健康状态
    
    Args:
        service_health: 服务健康状态字典
        
    Returns:
        总体健康状态
    """
    if not service_health:
        return HEALTH_STATUS["UNKNOWN"]
    
    healthy_count = 0
    total_count = len(service_health)
    
    for service_status in service_health.values():
        if service_status.get("status") == HEALTH_STATUS["HEALTHY"]:
            healthy_count += 1
    
    # 计算健康比例
    health_ratio = healthy_count / total_count
    
    if health_ratio == 1.0:
        return HEALTH_STATUS["HEALTHY"]
    elif health_ratio >= 0.5:
        return HEALTH_STATUS["DEGRADED"]
    else:
        return HEALTH_STATUS["UNHEALTHY"]