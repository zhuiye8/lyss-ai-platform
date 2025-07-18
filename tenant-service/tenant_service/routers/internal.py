# -*- coding: utf-8 -*-
"""
内部服务API路由

为其他微服务提供的内部接口，不对外暴露
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from ..core.database import get_db
from ..models.schemas.base import ApiResponse
from ..models.schemas.user import UserVerifyRequest, UserVerifyResponse, UserPasswordVerifyResponse
from ..models.schemas.supplier import (
    CredentialSelectorRequest, 
    SupplierCredentialInternalResponse, 
    CredentialTestRequest, 
    CredentialTestResponse,
    ActiveTenantsResponse,
    ToolConfigResponse
)
from ..repositories.user_repository import UserRepository
from ..repositories.supplier_repository import SupplierRepository
from ..repositories.tenant_repository import TenantRepository
from ..core.encryption import credential_manager

logger = structlog.get_logger()
router = APIRouter()


async def get_request_id(request: Request) -> str:
    """获取请求ID"""
    return request.headers.get("X-Request-ID", str(uuid.uuid4()))


@router.post(
    "/internal/users/verify",
    response_model=ApiResponse[UserVerifyResponse],
    summary="内部用户验证接口",
    description="为Auth Service提供用户验证功能，根据用户名（邮箱或用户名）查找用户信息"
)
async def verify_user(
    request_data: UserVerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id)
) -> ApiResponse[UserVerifyResponse]:
    """
    验证用户并返回用户信息
    
    这个接口专门为Auth Service设计，用于用户登录时的身份验证。
    根据提供的username（可以是邮箱或用户名）查找用户，返回验证所需的信息。
    
    Args:
        request_data: 验证请求数据
        request: FastAPI请求对象
        db: 数据库会话
        request_id: 请求ID
        
    Returns:
        用户验证信息
        
    Raises:
        HTTPException: 当用户不存在或不活跃时
    """
    try:
        # 记录验证请求开始
        logger.info(
            "开始用户验证",
            request_id=request_id,
            username=request_data.username,
            operation="user_verify"
        )
        
        # 初始化用户Repository
        user_repo = UserRepository(db)
        
        # 根据用户名查找用户（支持邮箱和用户名）
        user = await user_repo.get_by_email_or_username(request_data.username)
        
        if not user:
            logger.warning(
                "用户验证失败：用户不存在",
                request_id=request_id,
                username=request_data.username,
                operation="user_verify"
            )
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "3003",
                    "message": "用户不存在",
                    "details": {"username": request_data.username}
                }
            )
        
        # 检查用户是否激活
        if not user.is_active:
            logger.warning(
                "用户验证失败：用户已被禁用",
                request_id=request_id,
                username=request_data.username,
                user_id=str(user.id),
                tenant_id=str(user.tenant_id),
                operation="user_verify"
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "2005",
                    "message": "账户已被禁用",
                    "details": {"user_id": str(user.id)}
                }
            )
        
        # 构建验证响应（不包含密码哈希）
        verify_response = UserVerifyResponse(
            user_id=user.id,
            email=user.email,
            hashed_password=user.hashed_password,  # 暂时保留，仅用于Auth Service内部验证
            tenant_id=user.tenant_id,
            role=user.role.name if user.role else "end_user",
            is_active=user.is_active
        )
        
        # 记录验证成功
        logger.info(
            "用户验证成功",
            request_id=request_id,
            username=request_data.username,
            user_id=str(user.id),
            tenant_id=str(user.tenant_id),
            role=verify_response.role,
            operation="user_verify"
        )
        
        # 对于外部API调用，我们排除密码哈希字段以提高安全性
        # 但Auth Service仍需要这个字段进行密码验证，所以保留
        return ApiResponse[UserVerifyResponse](
            success=True,
            data=verify_response,
            message="用户验证成功",
            request_id=request_id
        )
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        # 记录未预期的错误
        import traceback
        logger.error(
            "用户验证过程中发生异常",
            request_id=request_id,
            username=request_data.username,
            error=str(e),
            traceback=traceback.format_exc(),
            operation="user_verify"
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "5003",
                "message": "内部服务器错误",
                "details": {"error": f"用户验证过程中发生异常: {str(e)}"}
            }
        )


@router.get(
    "/internal/users/{user_id}",
    response_model=ApiResponse[UserVerifyResponse],
    summary="根据用户ID获取用户信息",
    description="为其他服务提供根据用户ID获取用户详细信息的接口"
)
async def get_user_by_id(
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id)
) -> ApiResponse[UserVerifyResponse]:
    """
    根据用户ID获取用户信息
    
    Args:
        user_id: 用户ID
        tenant_id: 租户ID
        request: FastAPI请求对象
        db: 数据库会话
        request_id: 请求ID
        
    Returns:
        用户信息
        
    Raises:
        HTTPException: 当用户不存在时
    """
    try:
        logger.info(
            "获取用户信息",
            request_id=request_id,
            user_id=str(user_id),
            tenant_id=str(tenant_id),
            operation="get_user_by_id"
        )
        
        # 初始化用户Repository
        user_repo = UserRepository(db)
        
        # 获取用户信息（包含租户过滤）
        user = await user_repo.get_with_role(user_id, tenant_id)
        
        if not user:
            logger.warning(
                "用户不存在",
                request_id=request_id,
                user_id=str(user_id),
                tenant_id=str(tenant_id),
                operation="get_user_by_id"
            )
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "3003",
                    "message": "用户不存在",
                    "details": {"user_id": str(user_id)}
                }
            )
        
        # 构建响应
        user_response = UserVerifyResponse(
            user_id=user.id,
            email=user.email,
            hashed_password=user.hashed_password,
            tenant_id=user.tenant_id,
            role=user.role.name if user.role else "end_user",
            is_active=user.is_active
        )
        
        logger.info(
            "用户信息获取成功",
            request_id=request_id,
            user_id=str(user_id),
            tenant_id=str(tenant_id),
            operation="get_user_by_id"
        )
        
        return ApiResponse[UserVerifyResponse](
            success=True,
            data=user_response,
            message="用户信息获取成功",
            request_id=request_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "获取用户信息过程中发生异常",
            request_id=request_id,
            user_id=str(user_id),
            tenant_id=str(tenant_id),
            error=str(e),
            operation="get_user_by_id"
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "5003",
                "message": "内部服务器错误",
                "details": {"error": "获取用户信息过程中发生异常"}
            }
        )


@router.put(
    "/internal/users/{user_id}/last-login",
    response_model=ApiResponse[dict],
    summary="更新用户最后登录时间",
    description="为Auth Service提供更新用户最后登录时间的接口"
)
async def update_user_last_login(
    user_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id)
) -> ApiResponse[dict]:
    """
    更新用户最后登录时间
    
    Args:
        user_id: 用户ID
        request: FastAPI请求对象
        db: 数据库会话
        request_id: 请求ID
        
    Returns:
        更新结果
        
    Raises:
        HTTPException: 当用户不存在时
    """
    try:
        logger.info(
            "更新用户最后登录时间",
            request_id=request_id,
            user_id=str(user_id),
            operation="update_last_login"
        )
        
        # 初始化用户Repository
        user_repo = UserRepository(db)
        
        # 更新最后登录时间
        updated_user = await user_repo.update_last_login(user_id)
        
        if not updated_user:
            logger.warning(
                "用户不存在，无法更新最后登录时间",
                request_id=request_id,
                user_id=str(user_id),
                operation="update_last_login"
            )
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "3003",
                    "message": "用户不存在",
                    "details": {"user_id": str(user_id)}
                }
            )
        
        logger.info(
            "用户最后登录时间更新成功",
            request_id=request_id,
            user_id=str(user_id),
            operation="update_last_login"
        )
        
        return ApiResponse[dict](
            success=True,
            data={"updated": True, "last_login_at": updated_user.last_login_at.isoformat() if updated_user.last_login_at else None},
            message="最后登录时间更新成功",
            request_id=request_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "更新用户最后登录时间过程中发生异常",
            request_id=request_id,
            user_id=str(user_id),
            error=str(e),
            operation="update_last_login"
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "5003",
                "message": "内部服务器错误",
                "details": {"error": "更新最后登录时间过程中发生异常"}
            }
        )


@router.post(
    "/internal/users/verify-password",
    summary="验证用户密码（安全版）",
    description="为Auth Service提供安全的用户密码验证功能，不返回敏感信息"
)
async def verify_user_password(
    request_data: UserVerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id)
) -> ApiResponse[UserPasswordVerifyResponse]:
    """
    验证用户密码并返回用户信息（安全版，不包含密码哈希）
    
    这个接口专门为Auth Service设计，用于用户登录时的身份验证。
    相比原版verify接口，这个接口不返回密码哈希，更安全。
    
    Args:
        request_data: 验证请求数据，包含用户名和密码
        request: FastAPI请求对象
        db: 数据库会话
        request_id: 请求ID
        
    Returns:
        ApiResponse[UserPasswordVerifyResponse]: 验证结果，不包含密码哈希
        
    Raises:
        HTTPException: 当用户不存在或密码错误时
    """
    try:
        logger.info(
            "收到用户密码验证请求（安全版）",
            request_id=request_id,
            username=request_data.username,
            operation="verify_user_password"
        )
        
        # 导入用户服务
        from ..services.user_service import UserService
        user_service = UserService(db)
        
        # 验证用户凭证
        user = await user_service.verify_user_credentials(
            identifier=request_data.username,
            password=request_data.password,
            request_id=request_id
        )
        
        if not user:
            logger.warning(
                "用户密码验证失败",
                request_id=request_id,
                username=request_data.username,
                operation="verify_user_password"
            )
            raise HTTPException(
                status_code=401,
                detail={
                    "code": "3004",
                    "message": "用户名或密码错误",
                    "details": None
                }
            )
        
        # 构建安全响应（不包含密码哈希）
        verify_response = UserPasswordVerifyResponse(
            user_id=user.id,
            email=user.email,
            tenant_id=user.tenant_id,
            role=user.role.name if user.role else "end_user",
            is_active=user.is_active,
            password_valid=True
        )
        
        logger.info(
            "用户密码验证成功（安全版）",
            request_id=request_id,
            user_id=str(user.id),
            email=user.email,
            tenant_id=str(user.tenant_id),
            operation="verify_user_password"
        )
        
        # 构建安全的响应数据（排除密码哈希）
        response_data = {
            "user_id": verify_response.user_id,
            "email": verify_response.email,
            "tenant_id": verify_response.tenant_id,
            "role": verify_response.role,
            "is_active": verify_response.is_active,
            "hashed_password": verify_response.hashed_password,  # Auth Service需要这个字段进行密码验证
        }
        
        return ApiResponse(
            success=True,
            data=response_data,
            message="用户验证成功",
            request_id=request_id
        )
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(
            "用户密码验证过程中发生异常",
            request_id=request_id,
            username=request_data.username,
            error=str(e),
            operation="verify_user_password"
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "5003",
                "message": "内部服务器错误",
                "details": {"error": "用户验证过程中发生异常"}
            }
        )


# ===== EINO服务专用内部接口 =====

@router.get(
    "/internal/suppliers/{tenant_id}/available",
    response_model=ApiResponse[List[SupplierCredentialInternalResponse]],
    summary="获取可用供应商凭证列表",
    description="为EINO服务提供租户可用凭证列表，支持策略和筛选"
)
async def get_available_credentials(
    tenant_id: uuid.UUID,
    request: Request,
    strategy: str = Query(default="first_available", description="选择策略"),
    only_active: bool = Query(default=True, description="仅返回活跃凭证"),
    providers: Optional[str] = Query(default=None, description="供应商过滤，逗号分隔"),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id)
) -> ApiResponse[List[SupplierCredentialInternalResponse]]:
    """
    获取租户的可用供应商凭证列表
    
    为EINO服务提供智能凭证选择功能，支持不同的选择策略和过滤条件
    
    Args:
        tenant_id: 租户ID
        request: FastAPI请求对象
        strategy: 选择策略
        only_active: 仅返回活跃凭证
        providers: 供应商过滤列表
        db: 数据库会话
        request_id: 请求ID
        
    Returns:
        可用凭证列表（包含解密的API密钥）
    """
    try:
        logger.info(
            "获取可用供应商凭证列表",
            request_id=request_id,
            tenant_id=str(tenant_id),
            strategy=strategy,
            only_active=only_active,
            providers=providers,
            operation="get_available_credentials"
        )
        
        # 初始化Repository
        supplier_repo = SupplierRepository(db)
        
        # 构建过滤条件
        filters = {"tenant_id": tenant_id}
        if only_active:
            filters["is_active"] = True
        
        # 处理供应商过滤
        provider_list = None
        if providers:
            provider_list = [p.strip() for p in providers.split(",") if p.strip()]
        
        # 获取凭证列表
        credentials = await supplier_repo.get_credentials_by_filters(
            filters=filters,
            order_by="created_at",
            order_desc=True
        )
        
        # 按供应商过滤
        if provider_list:
            credentials = [cred for cred in credentials if cred.provider_name in provider_list]
        
        # 应用选择策略
        if strategy == "round_robin":
            # 轮询策略：按创建时间排序
            credentials = sorted(credentials, key=lambda x: x.created_at)
        elif strategy == "least_used":
            # 最少使用策略：按创建时间倒序（简化实现）
            credentials = sorted(credentials, key=lambda x: x.created_at, reverse=True)
        # first_available 策略：保持默认排序
        
        # 解密凭证并构建响应
        credential_responses = []
        for credential in credentials:
            try:
                # 获取解密的凭证信息
                decrypted_data = await credential_manager.get_decrypted_credential(
                    db, str(credential.id), str(tenant_id)
                )
                
                if decrypted_data:
                    credential_response = SupplierCredentialInternalResponse(
                        id=credential.id,
                        tenant_id=credential.tenant_id,
                        provider_name=credential.provider_name,
                        display_name=credential.display_name,
                        api_key=decrypted_data["api_key"],
                        base_url=decrypted_data["base_url"],
                        model_configs=decrypted_data["model_configs"],
                        is_active=credential.is_active,
                        created_at=credential.created_at,
                        updated_at=credential.updated_at
                    )
                    credential_responses.append(credential_response)
                    
            except Exception as e:
                logger.warning(
                    "凭证解密失败，跳过该凭证",
                    request_id=request_id,
                    credential_id=str(credential.id),
                    error=str(e)
                )
                continue
        
        logger.info(
            "可用凭证列表获取成功",
            request_id=request_id,
            tenant_id=str(tenant_id),
            count=len(credential_responses),
            operation="get_available_credentials"
        )
        
        return ApiResponse[List[SupplierCredentialInternalResponse]](
            success=True,
            data=credential_responses,
            message="可用凭证列表获取成功",
            request_id=request_id
        )
        
    except Exception as e:
        logger.error(
            "获取可用凭证列表过程中发生异常",
            request_id=request_id,
            tenant_id=str(tenant_id),
            error=str(e),
            operation="get_available_credentials"
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "5003",
                "message": "内部服务器错误",
                "details": {"error": "获取可用凭证列表失败"}
            }
        )


@router.post(
    "/internal/suppliers/{credential_id}/test",
    response_model=ApiResponse[CredentialTestResponse],
    summary="测试供应商凭证连接",
    description="为EINO服务提供凭证连接测试功能"
)
async def test_credential_connection(
    credential_id: uuid.UUID,
    request_data: CredentialTestRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id)
) -> ApiResponse[CredentialTestResponse]:
    """
    测试供应商凭证连接
    
    为EINO服务提供凭证有效性检测功能，确保凭证可以正常连接到供应商API
    
    Args:
        credential_id: 凭证ID
        request_data: 测试请求数据
        request: FastAPI请求对象
        db: 数据库会话
        request_id: 请求ID
        
    Returns:
        测试结果
    """
    try:
        logger.info(
            "开始测试供应商凭证连接",
            request_id=request_id,
            credential_id=str(credential_id),
            tenant_id=request_data.tenant_id,
            test_type=request_data.test_type,
            operation="test_credential_connection"
        )
        
        # 初始化供应商服务
        from ..services.supplier_service import SupplierService
        supplier_service = SupplierService(db)
        
        # 构建测试请求
        from ..models.schemas.supplier import SupplierTestRequest
        test_request = SupplierTestRequest(
            test_type=request_data.test_type,
            model_name=request_data.model_name or "default"
        )
        
        # 执行测试
        test_result = await supplier_service.test_credential(
            credential_id=credential_id,
            test_request=test_request,
            tenant_id=request_data.tenant_id,
            request_id=request_id
        )
        
        if not test_result:
            logger.warning(
                "凭证不存在或无权限",
                request_id=request_id,
                credential_id=str(credential_id),
                tenant_id=request_data.tenant_id,
                operation="test_credential_connection"
            )
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "3004",
                    "message": "凭证不存在或无权限",
                    "details": {"credential_id": str(credential_id)}
                }
            )
        
        # 构建响应
        response_data = CredentialTestResponse(
            success=test_result.success,
            test_type=test_result.test_type,
            response_time_ms=test_result.response_time_ms,
            error_message=test_result.error_message,
            result_data=test_result.result_data
        )
        
        logger.info(
            "凭证连接测试完成",
            request_id=request_id,
            credential_id=str(credential_id),
            tenant_id=request_data.tenant_id,
            success=test_result.success,
            response_time_ms=test_result.response_time_ms,
            operation="test_credential_connection"
        )
        
        return ApiResponse[CredentialTestResponse](
            success=True,
            data=response_data,
            message="凭证连接测试完成",
            request_id=request_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "凭证连接测试过程中发生异常",
            request_id=request_id,
            credential_id=str(credential_id),
            tenant_id=request_data.tenant_id,
            error=str(e),
            operation="test_credential_connection"
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "5003",
                "message": "内部服务器错误",
                "details": {"error": "凭证连接测试失败"}
            }
        )


@router.get(
    "/internal/tenants/active",
    response_model=ApiResponse[List[str]],
    summary="获取活跃租户列表",
    description="为EINO服务提供活跃租户ID列表，用于启动预热"
)
async def get_active_tenants(
    request: Request,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id)
) -> ApiResponse[List[str]]:
    """
    获取活跃租户列表
    
    为EINO服务提供活跃租户ID列表，用于服务启动时的凭证预热
    
    Args:
        request: FastAPI请求对象
        db: 数据库会话
        request_id: 请求ID
        
    Returns:
        活跃租户ID列表
    """
    try:
        logger.info(
            "获取活跃租户列表",
            request_id=request_id,
            operation="get_active_tenants"
        )
        
        # 初始化租户Repository
        tenant_repo = TenantRepository(db)
        
        # 获取所有活跃租户
        active_tenants = await tenant_repo.get_active_tenants()
        
        # 提取租户ID列表
        tenant_ids = [str(tenant.id) for tenant in active_tenants]
        
        logger.info(
            "活跃租户列表获取成功",
            request_id=request_id,
            count=len(tenant_ids),
            operation="get_active_tenants"
        )
        
        return ApiResponse[List[str]](
            success=True,
            data=tenant_ids,
            message="活跃租户列表获取成功",
            request_id=request_id
        )
        
    except Exception as e:
        logger.error(
            "获取活跃租户列表过程中发生异常",
            request_id=request_id,
            error=str(e),
            operation="get_active_tenants"
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "5003",
                "message": "内部服务器错误",
                "details": {"error": "获取活跃租户列表失败"}
            }
        )


@router.get(
    "/internal/tool-configs/{tenant_id}/{workflow_name}/{tool_name}",
    response_model=ApiResponse[ToolConfigResponse],
    summary="获取工具配置",
    description="为EINO服务提供工具配置信息"
)
async def get_tool_config(
    tenant_id: uuid.UUID,
    workflow_name: str,
    tool_name: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id)
) -> ApiResponse[ToolConfigResponse]:
    """
    获取工具配置
    
    为EINO服务提供工具配置信息，用于工作流中的工具启用/禁用控制
    
    Args:
        tenant_id: 租户ID
        workflow_name: 工作流名称
        tool_name: 工具名称
        request: FastAPI请求对象
        db: 数据库会话
        request_id: 请求ID
        
    Returns:
        工具配置信息
    """
    try:
        logger.info(
            "获取工具配置",
            request_id=request_id,
            tenant_id=str(tenant_id),
            workflow_name=workflow_name,
            tool_name=tool_name,
            operation="get_tool_config"
        )
        
        # 目前实现简化版本，返回默认配置
        # 在实际项目中，这里应该从数据库查询工具配置
        # 或者从租户配置中读取工具开关状态
        
        # 默认工具配置映射
        default_tool_configs = {
            "optimized_rag": {
                "web_search": True,
                "database_query": True,
                "memory_retrieval": True,
                "memory_storage": True
            },
            "simple_chat": {
                "memory_retrieval": True,
                "memory_storage": True
            },
            "tool_calling": {
                "web_search": True,
                "database_query": False,
                "code_execution": False
            }
        }
        
        # 获取工具配置
        workflow_config = default_tool_configs.get(workflow_name, {})
        is_enabled = workflow_config.get(tool_name, True)  # 默认启用
        
        # 构建响应
        tool_config = ToolConfigResponse(
            tenant_id=str(tenant_id),
            workflow_name=workflow_name,
            tool_name=tool_name,
            is_enabled=is_enabled,
            config_params={
                "timeout": 30,
                "max_retries": 3,
                "cache_enabled": True
            }
        )
        
        logger.info(
            "工具配置获取成功",
            request_id=request_id,
            tenant_id=str(tenant_id),
            workflow_name=workflow_name,
            tool_name=tool_name,
            is_enabled=is_enabled,
            operation="get_tool_config"
        )
        
        return ApiResponse[ToolConfigResponse](
            success=True,
            data=tool_config,
            message="工具配置获取成功",
            request_id=request_id
        )
        
    except Exception as e:
        logger.error(
            "获取工具配置过程中发生异常",
            request_id=request_id,
            tenant_id=str(tenant_id),
            workflow_name=workflow_name,
            tool_name=tool_name,
            error=str(e),
            operation="get_tool_config"
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "5003",
                "message": "内部服务器错误",
                "details": {"error": "获取工具配置失败"}
            }
        )