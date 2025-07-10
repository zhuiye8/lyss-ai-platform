# -*- coding: utf-8 -*-
"""
用户管理API路由

提供用户的CRUD操作接口
"""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from ..core.database import get_db
from ..models.schemas.base import ApiResponse, PaginatedResponse
from ..models.schemas.user import (
    UserCreateRequest,
    UserUpdateRequest, 
    UserResponse,
    UserDetailResponse,
    UserListParams
)
from ..services.user_service import UserService

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
    "/admin/users",
    response_model=ApiResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="创建用户",
    description="在当前租户下创建新用户，需要租户管理员权限"
)
async def create_user(
    request_data: UserCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
    tenant_id: str = Depends(get_current_tenant_id)
) -> ApiResponse[UserResponse]:
    """
    创建新用户
    
    Args:
        request_data: 用户创建请求数据
        request: FastAPI请求对象
        db: 数据库会话
        request_id: 请求ID
        tenant_id: 当前租户ID
        
    Returns:
        创建的用户信息
    """
    try:
        user_service = UserService(db)
        user = await user_service.create_user(request_data, tenant_id, request_id)
        
        return ApiResponse[UserResponse](
            success=True,
            data=user,
            message="用户创建成功",
            request_id=request_id
        )
        
    except ValueError as e:
        logger.warning(
            "用户创建失败：数据验证错误",
            request_id=request_id,
            tenant_id=tenant_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=400,
            detail={
                "code": "1001",
                "message": str(e),
                "details": {"request_data": request_data.model_dump()}
            }
        )
    except Exception as e:
        logger.error(
            "用户创建过程中发生异常",
            request_id=request_id,
            tenant_id=tenant_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "5003",
                "message": "内部服务器错误",
                "details": {"error": "用户创建失败"}
            }
        )


@router.get(
    "/admin/users",
    response_model=PaginatedResponse[UserResponse],
    summary="获取用户列表",
    description="分页获取当前租户的用户列表"
)
async def get_users(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    role: Optional[str] = Query(None, description="角色过滤"),
    is_active: Optional[bool] = Query(None, description="激活状态过滤"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="排序方向"),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
    tenant_id: str = Depends(get_current_tenant_id)
) -> PaginatedResponse[UserResponse]:
    """
    获取用户列表
    
    Args:
        request: FastAPI请求对象
        page: 页码
        page_size: 每页数量
        search: 搜索关键词
        role: 角色过滤
        is_active: 激活状态过滤
        sort_by: 排序字段
        sort_order: 排序方向
        db: 数据库会话
        request_id: 请求ID
        tenant_id: 当前租户ID
        
    Returns:
        用户列表响应
    """
    try:
        user_service = UserService(db)
        
        # 构建查询参数
        list_params = UserListParams(
            page=page,
            page_size=page_size,
            search=search,
            role=role,
            is_active=is_active,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # 获取用户列表
        users, total_count = await user_service.get_users_paginated(
            tenant_id, list_params, request_id
        )
        
        return PaginatedResponse[UserResponse](
            success=True,
            data=users,
            pagination=PaginationInfo(
                page=page,
                page_size=page_size,
                total_items=total_count,
                total_pages=(total_count + page_size - 1) // page_size,
                has_next=page * page_size < total_count,
                has_prev=page > 1
            ),
            message="用户列表获取成功",
            request_id=request_id
        )
        
    except Exception as e:
        logger.error(
            "获取用户列表过程中发生异常",
            request_id=request_id,
            tenant_id=tenant_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "5003",
                "message": "内部服务器错误",
                "details": {"error": "获取用户列表失败"}
            }
        )


@router.get(
    "/admin/users/{user_id}",
    response_model=ApiResponse[UserDetailResponse],
    summary="获取用户详情",
    description="获取指定用户的详细信息"
)
async def get_user(
    user_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
    tenant_id: str = Depends(get_current_tenant_id)
) -> ApiResponse[UserDetailResponse]:
    """
    获取用户详情
    
    Args:
        user_id: 用户ID
        request: FastAPI请求对象
        db: 数据库会话
        request_id: 请求ID
        tenant_id: 当前租户ID
        
    Returns:
        用户详细信息
    """
    try:
        user_service = UserService(db)
        user = await user_service.get_user_detail(user_id, tenant_id, request_id)
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "3003",
                    "message": "用户不存在",
                    "details": {"user_id": str(user_id)}
                }
            )
        
        return ApiResponse[UserDetailResponse](
            success=True,
            data=user,
            message="用户详情获取成功",
            request_id=request_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "获取用户详情过程中发生异常",
            request_id=request_id,
            user_id=str(user_id),
            tenant_id=tenant_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "5003",
                "message": "内部服务器错误",
                "details": {"error": "获取用户详情失败"}
            }
        )


@router.put(
    "/admin/users/{user_id}",
    response_model=ApiResponse[UserResponse],
    summary="更新用户",
    description="更新用户信息"
)
async def update_user(
    user_id: uuid.UUID,
    request_data: UserUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
    tenant_id: str = Depends(get_current_tenant_id)
) -> ApiResponse[UserResponse]:
    """
    更新用户信息
    
    Args:
        user_id: 用户ID
        request_data: 用户更新请求数据
        request: FastAPI请求对象
        db: 数据库会话
        request_id: 请求ID
        tenant_id: 当前租户ID
        
    Returns:
        更新后的用户信息
    """
    try:
        user_service = UserService(db)
        user = await user_service.update_user(user_id, request_data, tenant_id, request_id)
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "3003",
                    "message": "用户不存在",
                    "details": {"user_id": str(user_id)}
                }
            )
        
        return ApiResponse[UserResponse](
            success=True,
            data=user,
            message="用户更新成功",
            request_id=request_id
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(
            "用户更新失败：数据验证错误",
            request_id=request_id,
            user_id=str(user_id),
            tenant_id=tenant_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=400,
            detail={
                "code": "1001",
                "message": str(e),
                "details": {"user_id": str(user_id)}
            }
        )
    except Exception as e:
        logger.error(
            "用户更新过程中发生异常",
            request_id=request_id,
            user_id=str(user_id),
            tenant_id=tenant_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "5003",
                "message": "内部服务器错误",
                "details": {"error": "用户更新失败"}
            }
        )


@router.delete(
    "/admin/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除用户",
    description="删除指定用户（软删除）"
)
async def delete_user(
    user_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
    tenant_id: str = Depends(get_current_tenant_id)
) -> None:
    """
    删除用户（软删除）
    
    Args:
        user_id: 用户ID
        request: FastAPI请求对象
        db: 数据库会话
        request_id: 请求ID
        tenant_id: 当前租户ID
    """
    try:
        user_service = UserService(db)
        success = await user_service.delete_user(user_id, tenant_id, request_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "3003",
                    "message": "用户不存在",
                    "details": {"user_id": str(user_id)}
                }
            )
        
        # 204状态码不返回内容
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "用户删除过程中发生异常",
            request_id=request_id,
            user_id=str(user_id),
            tenant_id=tenant_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "5003",
                "message": "内部服务器错误",
                "details": {"error": "用户删除失败"}
            }
        )


@router.patch(
    "/admin/users/{user_id}/status",
    response_model=ApiResponse[UserResponse],
    summary="更新用户状态",
    description="激活或禁用用户"
)
async def update_user_status(
    user_id: uuid.UUID,
    is_active: bool,
    request: Request,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
    tenant_id: str = Depends(get_current_tenant_id)
) -> ApiResponse[UserResponse]:
    """
    更新用户激活状态
    
    Args:
        user_id: 用户ID
        is_active: 是否激活
        request: FastAPI请求对象
        db: 数据库会话
        request_id: 请求ID
        tenant_id: 当前租户ID
        
    Returns:
        更新后的用户信息
    """
    try:
        user_service = UserService(db)
        user = await user_service.update_user_status(user_id, is_active, tenant_id, request_id)
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "3003",
                    "message": "用户不存在",
                    "details": {"user_id": str(user_id)}
                }
            )
        
        status_text = "激活" if is_active else "禁用"
        return ApiResponse[UserResponse](
            success=True,
            data=user,
            message=f"用户{status_text}成功",
            request_id=request_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "用户状态更新过程中发生异常",
            request_id=request_id,
            user_id=str(user_id),
            tenant_id=tenant_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "5003",
                "message": "内部服务器错误",
                "details": {"error": "用户状态更新失败"}
            }
        )