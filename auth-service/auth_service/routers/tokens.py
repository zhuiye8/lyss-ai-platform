"""
Auth Service 令牌管理路由
实现令牌刷新和用户登出功能
"""

from typing import Optional

from fastapi import APIRouter, Header, Request

from ..models.schemas.token import RefreshTokenRequest, RefreshTokenResponse, LogoutRequest
from ..models.schemas.response import ApiResponse, SuccessResponse
from ..services.auth_service import auth_service
from ..middleware.request_logging import request_id_var
from ..utils.logging import logger

router = APIRouter()


@router.post(
    "/refresh",
    response_model=ApiResponse[RefreshTokenResponse],
    summary="刷新访问令牌",
    description="使用刷新令牌获取新的访问令牌",
    responses={
        200: {
            "description": "令牌刷新成功",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "token_type": "bearer",
                            "expires_in": 1800,
                        },
                        "message": "令牌刷新成功",
                        "request_id": "req-20250710143025-a1b2c3d4",
                        "timestamp": "2025-07-10T10:30:00Z",
                    }
                }
            },
        },
        401: {
            "description": "刷新令牌无效或已过期",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": {
                            "code": "2002",
                            "message": "令牌已过期，请重新登录",
                            "details": {"expired_at": "2025-07-10T10:30:00Z"},
                        },
                        "request_id": "req-20250710143025-a1b2c3d4",
                        "timestamp": "2025-07-10T10:30:00Z",
                    }
                }
            },
        },
    },
)
async def refresh_token(request: Request, refresh_request: RefreshTokenRequest):
    """
    刷新访问令牌

    使用有效的刷新令牌获取新的访问令牌。刷新令牌通常有更长的有效期（7天），
    用于在访问令牌过期时获取新的访问令牌，避免用户频繁登录。

    Args:
        refresh_request: 包含刷新令牌的请求体

    Returns:
        新的访问令牌信息
    """
    # 获取请求ID
    try:
        request_id = request_id_var.get()
    except LookupError:
        request_id = "unknown"

    # 记录刷新尝试
    logger.info("令牌刷新请求", operation="token_refresh_attempt")

    # 执行令牌刷新
    refresh_response = await auth_service.refresh_access_token(
        refresh_token=refresh_request.refresh_token, request_id=request_id
    )

    # 返回成功响应
    return ApiResponse(
        success=True,
        data=refresh_response,
        message="令牌刷新成功",
        request_id=request_id,
    )


@router.post(
    "/logout",
    response_model=SuccessResponse,
    summary="用户登出",
    description="废止当前访问令牌，实现安全登出",
    responses={
        200: {
            "description": "登出成功",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "登出成功",
                        "request_id": "req-20250710143025-a1b2c3d4",
                        "timestamp": "2025-07-10T10:30:00Z",
                    }
                }
            },
        },
    },
)
async def logout(
    request: Request,
    logout_request: LogoutRequest,
    authorization: Optional[str] = Header(None),
):
    """
    用户登出

    将指定的访问令牌加入黑名单，实现安全登出。登出后该令牌将无法再用于访问受保护的资源。

    可以通过以下两种方式提供要废止的令牌：
    1. 在请求体中提供token字段
    2. 在Authorization头部提供Bearer令牌

    Args:
        logout_request: 登出请求体（可包含要废止的令牌）
        authorization: Authorization头部（可选）

    Returns:
        登出成功确认信息
    """
    # 获取请求ID
    try:
        request_id = request_id_var.get()
    except LookupError:
        request_id = "unknown"

    # 确定要废止的令牌
    token_to_revoke = logout_request.token

    # 如果请求体中没有令牌，尝试从Authorization头部获取
    if not token_to_revoke and authorization:
        try:
            scheme, token = authorization.split()
            if scheme.lower() == "bearer":
                token_to_revoke = token
        except ValueError:
            # Authorization头部格式错误，忽略
            pass

    # 记录登出尝试
    logger.info(
        "用户登出请求",
        operation="logout_attempt",
        data={"has_token": bool(token_to_revoke)},
    )

    # 执行登出
    success = await auth_service.logout_user(token_to_revoke)

    # 返回成功响应（即使令牌废止失败也返回成功，因为对用户来说登出意图已达成）
    return SuccessResponse(
        success=True,
        message="登出成功",
        request_id=request_id,
    )