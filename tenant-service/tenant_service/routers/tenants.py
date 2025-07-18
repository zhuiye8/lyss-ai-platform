# -*- coding: utf-8 -*-
"""
租户管理API路由

提供租户的CRUD操作接口
"""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from ..core.database import get_db
from ..models.schemas.base import ApiResponse, PaginatedResponse
from ..models.schemas.tenant import (
    TenantCreateRequest,
    TenantUpdateRequest, 
    TenantResponse,
    TenantDetailResponse,
    TenantStatsResponse,
    TenantListParams
)
from ..services.tenant_service import TenantService

logger = structlog.get_logger()
router = APIRouter()


async def get_request_id(request: Request) -> str:
    """获取请求ID"""
    return request.headers.get("X-Request-ID", str(uuid.uuid4()))


@router.post(
    "/admin/tenants",
    response_model=ApiResponse[TenantResponse],
    status_code=status.HTTP_201_CREATED,
    summary="创建租户",
    description="创建新的租户，需要超级管理员权限"
)
async def create_tenant(
    request_data: TenantCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id)
) -> ApiResponse[TenantResponse]:
    """
    创建新租户
    
    Args:
        request_data: 租户创建请求数据
        request: FastAPI请求对象
        db: 数据库会话
        request_id: 请求ID
        
    Returns:
        创建的租户信息
        
    Raises:
        HTTPException: 当slug已存在或创建失败时
    """
    try:
        # 初始化租户服务
        tenant_service = TenantService(db)
        
        # 创建租户
        tenant = await tenant_service.create_tenant(request_data, request_id)
        
        return ApiResponse[TenantResponse](
            success=True,
            data=tenant,
            message="租户创建成功",
            request_id=request_id
        )
        
    except ValueError as e:
        # slug已存在等业务逻辑错误
        logger.warning(
            "租户创建失败：业务逻辑错误",
            request_id=request_id,
            error=str(e),
            operation="create_tenant_api"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "3005",
                "message": str(e),
                "details": {"field": "slug"}
            }
        )
    except Exception as e:
        # 其他未预期错误
        logger.error(
            "租户创建过程中发生异常",
            request_id=request_id,
            error=str(e),
            operation="create_tenant_api"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "5003",
                "message": "内部服务器错误",
                "details": {"error": "租户创建过程中发生异常"}
            }
        )


@router.get(
    "/admin/tenants",
    response_model=ApiResponse[PaginatedResponse[TenantResponse]],
    summary="获取租户列表",
    description="获取分页的租户列表，支持筛选和搜索"
)
async def get_tenant_list(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="状态过滤"),
    subscription_plan: Optional[str] = Query(None, description="订阅计划过滤"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="排序方向"),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id)
) -> ApiResponse[PaginatedResponse[TenantResponse]]:
    """
    获取租户列表
    
    Args:
        request: FastAPI请求对象
        page: 页码
        page_size: 每页数量
        status: 状态过滤
        subscription_plan: 订阅计划过滤
        search: 搜索关键词
        sort_by: 排序字段
        sort_order: 排序方向
        db: 数据库会话
        request_id: 请求ID
        
    Returns:
        分页的租户列表
    """
    try:
        # 构建查询参数
        params = TenantListParams(
            page=page,
            page_size=page_size,
            status=status,
            subscription_plan=subscription_plan,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # 初始化租户服务
        tenant_service = TenantService(db)
        
        # 获取租户列表
        result = await tenant_service.get_tenant_list(params, request_id)
        
        return ApiResponse[PaginatedResponse[TenantResponse]](
            success=True,
            data=result,
            message="租户列表获取成功",
            request_id=request_id
        )
        
    except Exception as e:
        logger.error(
            "获取租户列表过程中发生异常",
            request_id=request_id,
            error=str(e),
            operation="get_tenant_list_api"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "5003",
                "message": "内部服务器错误",
                "details": {"error": "获取租户列表过程中发生异常"}
            }
        )


@router.get(
    "/admin/tenants/{tenant_id}",
    response_model=ApiResponse[TenantDetailResponse],
    summary="获取租户详情",
    description="根据ID获取租户的详细信息，包含统计数据"
)
async def get_tenant_detail(
    tenant_id: uuid.UUID,
    request: Request,
    include_stats: bool = Query(True, description="是否包含统计信息"),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id)
) -> ApiResponse[TenantDetailResponse]:
    """
    获取租户详情
    
    Args:
        tenant_id: 租户ID
        request: FastAPI请求对象
        include_stats: 是否包含统计信息
        db: 数据库会话
        request_id: 请求ID
        
    Returns:
        租户详细信息
        
    Raises:
        HTTPException: 当租户不存在时
    """
    try:
        # 初始化租户服务
        tenant_service = TenantService(db)
        
        # 获取租户信息
        tenant = await tenant_service.get_tenant_by_id(tenant_id, request_id, include_stats)
        
        if not tenant:
            logger.warning(
                "租户详情获取失败：租户不存在",
                request_id=request_id,
                tenant_id=str(tenant_id),
                operation="get_tenant_detail_api"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "3001",
                    "message": "租户不存在",
                    "details": {"tenant_id": str(tenant_id)}
                }
            )
        
        return ApiResponse[TenantDetailResponse](
            success=True,
            data=tenant,
            message="租户详情获取成功",
            request_id=request_id
        )
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(
            "获取租户详情过程中发生异常",
            request_id=request_id,
            tenant_id=str(tenant_id),
            error=str(e),
            operation="get_tenant_detail_api"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "5003",
                "message": "内部服务器错误",
                "details": {"error": "获取租户详情过程中发生异常"}
            }
        )


@router.put(
    "/admin/tenants/{tenant_id}",
    response_model=ApiResponse[TenantResponse],
    summary="更新租户信息",
    description="更新租户的基本信息"
)
async def update_tenant(
    tenant_id: uuid.UUID,
    request_data: TenantUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id)
) -> ApiResponse[TenantResponse]:
    """
    更新租户信息
    
    Args:
        tenant_id: 租户ID
        request_data: 更新请求数据
        request: FastAPI请求对象
        db: 数据库会话
        request_id: 请求ID
        
    Returns:
        更新后的租户信息
        
    Raises:
        HTTPException: 当租户不存在时
    """
    try:
        # 初始化租户服务
        tenant_service = TenantService(db)
        
        # 更新租户
        tenant = await tenant_service.update_tenant(tenant_id, request_data, request_id)
        
        if not tenant:
            logger.warning(
                "租户更新失败：租户不存在",
                request_id=request_id,
                tenant_id=str(tenant_id),
                operation="update_tenant_api"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "3001",
                    "message": "租户不存在",
                    "details": {"tenant_id": str(tenant_id)}
                }
            )
        
        return ApiResponse[TenantResponse](
            success=True,
            data=tenant,
            message="租户更新成功",
            request_id=request_id
        )
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(
            "更新租户过程中发生异常",
            request_id=request_id,
            tenant_id=str(tenant_id),
            error=str(e),
            operation="update_tenant_api"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "5003",
                "message": "内部服务器错误",
                "details": {"error": "更新租户过程中发生异常"}
            }
        )


@router.delete(
    "/admin/tenants/{tenant_id}",
    response_model=ApiResponse[dict],
    summary="删除租户",
    description="软删除租户（设置为inactive状态）"
)
async def delete_tenant(
    tenant_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id)
) -> ApiResponse[dict]:
    """
    删除租户
    
    Args:
        tenant_id: 租户ID
        request: FastAPI请求对象
        db: 数据库会话
        request_id: 请求ID
        
    Returns:
        删除结果
        
    Raises:
        HTTPException: 当租户不存在时
    """
    try:
        # 初始化租户服务
        tenant_service = TenantService(db)
        
        # 删除租户
        success = await tenant_service.delete_tenant(tenant_id, request_id)
        
        if not success:
            logger.warning(
                "租户删除失败：租户不存在",
                request_id=request_id,
                tenant_id=str(tenant_id),
                operation="delete_tenant_api"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "3001",
                    "message": "租户不存在",
                    "details": {"tenant_id": str(tenant_id)}
                }
            )
        
        return ApiResponse[dict](
            success=True,
            data={"tenant_id": str(tenant_id), "deleted": True},
            message="租户删除成功",
            request_id=request_id
        )
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(
            "删除租户过程中发生异常",
            request_id=request_id,
            tenant_id=str(tenant_id),
            error=str(e),
            operation="delete_tenant_api"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "5003",
                "message": "内部服务器错误",
                "details": {"error": "删除租户过程中发生异常"}
            }
        )


@router.get(
    "/admin/tenants/{tenant_id}/stats",
    response_model=ApiResponse[TenantStatsResponse],
    summary="获取租户统计信息",
    description="获取租户的详细统计数据"
)
async def get_tenant_stats(
    tenant_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id)
) -> ApiResponse[TenantStatsResponse]:
    """
    获取租户统计信息
    
    Args:
        tenant_id: 租户ID
        request: FastAPI请求对象
        db: 数据库会话
        request_id: 请求ID
        
    Returns:
        租户统计信息
        
    Raises:
        HTTPException: 当租户不存在时
    """
    try:
        # 初始化租户服务
        tenant_service = TenantService(db)
        
        # 获取统计信息
        stats = await tenant_service.get_tenant_stats(tenant_id, request_id)
        
        if not stats:
            logger.warning(
                "租户统计信息获取失败：租户不存在",
                request_id=request_id,
                tenant_id=str(tenant_id),
                operation="get_tenant_stats_api"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "3001",
                    "message": "租户不存在",
                    "details": {"tenant_id": str(tenant_id)}
                }
            )
        
        return ApiResponse[TenantStatsResponse](
            success=True,
            data=stats,
            message="租户统计信息获取成功",
            request_id=request_id
        )
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(
            "获取租户统计信息过程中发生异常",
            request_id=request_id,
            tenant_id=str(tenant_id),
            error=str(e),
            operation="get_tenant_stats_api"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "5003",
                "message": "内部服务器错误",
                "details": {"error": "获取租户统计信息过程中发生异常"}
            }
        )