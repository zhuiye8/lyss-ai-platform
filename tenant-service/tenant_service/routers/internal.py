# -*- coding: utf-8 -*-
"""
内部服务API路由

为其他微服务提供的内部接口，不对外暴露
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from ..core.database import get_db
from ..models.schemas.base import ApiResponse
from ..models.schemas.user import UserVerifyRequest, UserVerifyResponse, UserPasswordVerifyResponse
from ..repositories.user_repository import UserRepository

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