# -*- coding: utf-8 -*-
"""
供应商凭证管理API路由

提供供应商凭证的安全管理接口
"""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from ..core.database import get_db
from ..models.schemas.base import ApiResponse, PaginatedResponse, PaginationInfo
from ..models.schemas.supplier import (
    SupplierCredentialCreateRequest,
    SupplierCredentialUpdateRequest,
    SupplierCredentialResponse,
    SupplierCredentialDetailResponse,
    SupplierCredentialListParams,
    SupplierTestRequest,
    SupplierTestResponse
)
from ..services.supplier_service import SupplierService

logger = structlog.get_logger()
router = APIRouter()


async def get_request_id(request: Request) -> str:
    """获取请求ID"""
    return request.headers.get("X-Request-ID", str(uuid.uuid4()))


async def get_current_tenant_id(request: Request) -> str:
    """从请求头获取当前租户ID"""
    tenant_id = request.headers.get("X-Tenant-ID")
    if not tenant_id:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "2001", 
                "message": "缺少租户标识",
                "details": {"header": "X-Tenant-ID"}
            }
        )
    return tenant_id


@router.post(
    "/admin/suppliers",
    response_model=ApiResponse[SupplierCredentialResponse],
    status_code=status.HTTP_201_CREATED,
    summary="添加供应商凭证",
    description="添加新的AI供应商API密钥，使用pgcrypto加密存储"
)
async def create_supplier_credential(
    request_data: SupplierCredentialCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
    tenant_id: str = Depends(get_current_tenant_id)
) -> ApiResponse[SupplierCredentialResponse]:
    """
    创建供应商凭证
    
    Args:
        request_data: 凭证创建请求数据
        request: FastAPI请求对象
        db: 数据库会话
        request_id: 请求ID
        tenant_id: 当前租户ID
        
    Returns:
        创建的凭证信息（不包含API密钥）
    """
    try:
        supplier_service = SupplierService(db)
        credential = await supplier_service.create_credential(
            request_data, tenant_id, request_id
        )
        
        return ApiResponse[SupplierCredentialResponse](
            success=True,
            data=credential,
            message="供应商凭证添加成功",
            request_id=request_id
        )
        
    except ValueError as e:
        logger.warning(
            "供应商凭证创建失败：数据验证错误",
            request_id=request_id,
            tenant_id=tenant_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=400,
            detail={
                "code": "1001",
                "message": str(e),
                "details": {"provider_name": request_data.provider_name}
            }
        )
    except Exception as e:
        logger.error(
            "供应商凭证创建过程中发生异常",
            request_id=request_id,
            tenant_id=tenant_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "5003",
                "message": "内部服务器错误",
                "details": {"error": "供应商凭证创建失败"}
            }
        )


@router.get(
    "/admin/suppliers",
    response_model=PaginatedResponse[SupplierCredentialResponse],
    summary="获取供应商凭证列表",
    description="获取当前租户的供应商凭证列表（不返回API密钥）"
)
async def get_supplier_credentials(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    provider_name: Optional[str] = Query(None, description="供应商过滤"),
    is_active: Optional[bool] = Query(None, description="激活状态过滤"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="排序方向"),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
    tenant_id: str = Depends(get_current_tenant_id)
) -> PaginatedResponse[SupplierCredentialResponse]:
    """
    获取供应商凭证列表
    
    Args:
        request: FastAPI请求对象
        page: 页码
        page_size: 每页数量
        provider_name: 供应商过滤
        is_active: 激活状态过滤
        sort_by: 排序字段
        sort_order: 排序方向
        db: 数据库会话
        request_id: 请求ID
        tenant_id: 当前租户ID
        
    Returns:
        供应商凭证列表响应
    """
    try:
        supplier_service = SupplierService(db)
        
        # 构建查询参数
        list_params = SupplierCredentialListParams(
            page=page,
            page_size=page_size,
            provider_name=provider_name,
            is_active=is_active,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # 获取凭证列表
        credentials, total_count = await supplier_service.get_credentials_paginated(
            tenant_id, list_params, request_id
        )
        
        return PaginatedResponse[SupplierCredentialResponse](
            success=True,
            data=credentials,
            pagination=PaginationInfo(
                page=page,
                page_size=page_size,
                total_items=total_count,
                total_pages=(total_count + page_size - 1) // page_size,
                has_next=page * page_size < total_count,
                has_prev=page > 1
            ),
            message="供应商凭证列表获取成功",
            request_id=request_id
        )
        
    except Exception as e:
        logger.error(
            "获取供应商凭证列表过程中发生异常",
            request_id=request_id,
            tenant_id=tenant_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "5003",
                "message": "内部服务器错误",
                "details": {"error": "获取供应商凭证列表失败"}
            }
        )


@router.get(
    "/admin/suppliers/{credential_id}",
    response_model=ApiResponse[SupplierCredentialDetailResponse],
    summary="获取供应商凭证详情",
    description="获取指定供应商凭证的详细信息（不包含API密钥）"
)
async def get_supplier_credential(
    credential_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
    tenant_id: str = Depends(get_current_tenant_id)
) -> ApiResponse[SupplierCredentialDetailResponse]:
    """
    获取供应商凭证详情
    
    Args:
        credential_id: 凭证ID
        request: FastAPI请求对象
        db: 数据库会话
        request_id: 请求ID
        tenant_id: 当前租户ID
        
    Returns:
        供应商凭证详细信息
    """
    try:
        supplier_service = SupplierService(db)
        credential = await supplier_service.get_credential_detail(
            credential_id, tenant_id, request_id
        )
        
        if not credential:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "3004",
                    "message": "供应商凭证不存在",
                    "details": {"credential_id": str(credential_id)}
                }
            )
        
        return ApiResponse[SupplierCredentialDetailResponse](
            success=True,
            data=credential,
            message="供应商凭证详情获取成功",
            request_id=request_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "获取供应商凭证详情过程中发生异常",
            request_id=request_id,
            credential_id=str(credential_id),
            tenant_id=tenant_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "5003",
                "message": "内部服务器错误",
                "details": {"error": "获取供应商凭证详情失败"}
            }
        )


@router.put(
    "/admin/suppliers/{credential_id}",
    response_model=ApiResponse[SupplierCredentialResponse],
    summary="更新供应商凭证",
    description="更新供应商凭证信息（可选择更新API密钥）"
)
async def update_supplier_credential(
    credential_id: uuid.UUID,
    request_data: SupplierCredentialUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
    tenant_id: str = Depends(get_current_tenant_id)
) -> ApiResponse[SupplierCredentialResponse]:
    """
    更新供应商凭证信息
    
    Args:
        credential_id: 凭证ID
        request_data: 凭证更新请求数据
        request: FastAPI请求对象
        db: 数据库会话
        request_id: 请求ID
        tenant_id: 当前租户ID
        
    Returns:
        更新后的凭证信息
    """
    try:
        supplier_service = SupplierService(db)
        credential = await supplier_service.update_credential(
            credential_id, request_data, tenant_id, request_id
        )
        
        if not credential:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "3004",
                    "message": "供应商凭证不存在",
                    "details": {"credential_id": str(credential_id)}
                }
            )
        
        return ApiResponse[SupplierCredentialResponse](
            success=True,
            data=credential,
            message="供应商凭证更新成功",
            request_id=request_id
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(
            "供应商凭证更新失败：数据验证错误",
            request_id=request_id,
            credential_id=str(credential_id),
            tenant_id=tenant_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=400,
            detail={
                "code": "1001",
                "message": str(e),
                "details": {"credential_id": str(credential_id)}
            }
        )
    except Exception as e:
        logger.error(
            "供应商凭证更新过程中发生异常",
            request_id=request_id,
            credential_id=str(credential_id),
            tenant_id=tenant_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "5003",
                "message": "内部服务器错误",
                "details": {"error": "供应商凭证更新失败"}
            }
        )


@router.delete(
    "/admin/suppliers/{credential_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除供应商凭证",
    description="删除指定的供应商凭证"
)
async def delete_supplier_credential(
    credential_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
    tenant_id: str = Depends(get_current_tenant_id)
) -> None:
    """
    删除供应商凭证
    
    Args:
        credential_id: 凭证ID
        request: FastAPI请求对象
        db: 数据库会话
        request_id: 请求ID
        tenant_id: 当前租户ID
    """
    try:
        supplier_service = SupplierService(db)
        success = await supplier_service.delete_credential(
            credential_id, tenant_id, request_id
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "3004",
                    "message": "供应商凭证不存在",
                    "details": {"credential_id": str(credential_id)}
                }
            )
        
        # 204状态码不返回内容
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "供应商凭证删除过程中发生异常",
            request_id=request_id,
            credential_id=str(credential_id),
            tenant_id=tenant_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "5003",
                "message": "内部服务器错误",
                "details": {"error": "供应商凭证删除失败"}
            }
        )


@router.post(
    "/admin/suppliers/{credential_id}/test",
    response_model=ApiResponse[SupplierTestResponse],
    summary="测试供应商连接",
    description="测试供应商API密钥是否有效"
)
async def test_supplier_credential(
    credential_id: uuid.UUID,
    test_request: SupplierTestRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
    tenant_id: str = Depends(get_current_tenant_id)
) -> ApiResponse[SupplierTestResponse]:
    """
    测试供应商API连接
    
    Args:
        credential_id: 凭证ID
        test_request: 测试请求数据
        request: FastAPI请求对象
        db: 数据库会话
        request_id: 请求ID
        tenant_id: 当前租户ID
        
    Returns:
        测试结果
    """
    try:
        supplier_service = SupplierService(db)
        test_result = await supplier_service.test_credential(
            credential_id, test_request, tenant_id, request_id
        )
        
        if not test_result:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "3004",
                    "message": "供应商凭证不存在",
                    "details": {"credential_id": str(credential_id)}
                }
            )
        
        return ApiResponse[SupplierTestResponse](
            success=True,
            data=test_result,
            message="供应商连接测试完成",
            request_id=request_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "供应商连接测试过程中发生异常",
            request_id=request_id,
            credential_id=str(credential_id),
            tenant_id=tenant_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "5003",
                "message": "内部服务器错误",
                "details": {"error": "供应商连接测试失败"}
            }
        )