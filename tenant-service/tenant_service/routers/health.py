# -*- coding: utf-8 -*-
"""
健康检查路由

提供服务健康状态检查接口
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..models.schemas.base import HealthCheckResponse
from ..config import get_settings

settings = get_settings()
router = APIRouter()


@router.get("/health", response_model=HealthCheckResponse, summary="健康检查")
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthCheckResponse:
    """
    检查服务健康状态
    
    Returns:
        HealthCheckResponse: 健康检查结果
    """
    dependencies = {}
    
    # 检查数据库连接
    try:
        from sqlalchemy import text
        result = await db.execute(text("SELECT 1"))
        value = result.scalar()
        if value == 1:
            dependencies["database"] = "healthy"
        else:
            dependencies["database"] = "unhealthy"
    except Exception as e:
        dependencies["database"] = "unhealthy"
    
    # 检查pgcrypto扩展
    try:
        from sqlalchemy import text
        result = await db.execute(text("SELECT pgp_sym_encrypt('test', 'test_key')"))
        crypto_result = result.scalar()
        if crypto_result:
            dependencies["pgcrypto"] = "healthy"
        else:
            dependencies["pgcrypto"] = "unhealthy"
    except Exception as e:
        dependencies["pgcrypto"] = "unhealthy"
    
    # 判断总体状态
    overall_status = "healthy" if all(
        status == "healthy" for status in dependencies.values()
    ) else "unhealthy"
    
    return HealthCheckResponse(
        status=overall_status,
        version=settings.version,
        dependencies=dependencies
    )