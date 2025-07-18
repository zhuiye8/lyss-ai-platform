"""
Auth Service 内部服务接口路由
提供给其他微服务使用的令牌验证接口
"""

from fastapi import APIRouter, Request

from ..models.schemas.token import TokenVerifyRequest, TokenVerifyResponse
from ..models.schemas.response import ApiResponse
from ..services.auth_service import auth_service
from ..middleware.request_logging import request_id_var
from ..utils.logging import logger

router = APIRouter()


@router.post(
    "/verify",
    response_model=ApiResponse[TokenVerifyResponse],
    summary="验证JWT令牌（内部接口）",
    description="供其他微服务调用的令牌验证接口，验证JWT令牌的有效性并返回用户信息",
    responses={
        200: {
            "description": "令牌验证成功",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "valid": True,
                            "payload": {
                                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                                "tenant_id": "550e8400-e29b-41d4-a716-446655440001",
                                "role": "end_user",
                                "email": "user@example.com",
                                "exp": 1234567890,
                                "jti": "token-unique-id",
                            },
                        },
                        "request_id": "req-20250710143025-a1b2c3d4",
                        "timestamp": "2025-07-10T10:30:00Z",
                    }
                }
            },
        },
        200: {
            "description": "令牌验证失败",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {"valid": False, "payload": None},
                        "request_id": "req-20250710143025-a1b2c3d4",
                        "timestamp": "2025-07-10T10:30:00Z",
                    }
                }
            },
        },
    },
    tags=["内部接口"],
)
async def verify_token(request: Request, verify_request: TokenVerifyRequest):
    """
    验证JWT令牌（内部服务专用）

    此接口专门供其他微服务调用，用于验证JWT令牌的有效性。
    与公开API不同，此接口不会抛出异常，而是返回验证结果。

    验证过程包括：
    1. JWT签名验证
    2. 令牌过期时间检查
    3. 令牌格式和必需字段验证
    4. 黑名单检查

    Args:
        verify_request: 包含要验证的JWT令牌

    Returns:
        令牌验证结果，包含是否有效和载荷信息
    """
    # 获取请求ID
    try:
        request_id = request_id_var.get()
    except LookupError:
        request_id = "unknown"

    try:
        # 验证令牌
        payload = await auth_service.verify_token(verify_request.token)

        # 记录成功验证
        logger.debug(
            "令牌验证成功",
            operation="token_verify",
            data={
                "user_id": payload.get("user_id"),
                "tenant_id": payload.get("tenant_id"),
                "jti": payload.get("jti"),
            },
        )

        # 返回验证成功响应
        return ApiResponse(
            success=True,
            data=TokenVerifyResponse(valid=True, payload=payload),
            request_id=request_id,
        )

    except Exception as e:
        # 令牌验证失败，但不抛出异常，而是返回验证失败结果
        logger.debug(
            f"令牌验证失败: {str(e)}",
            operation="token_verify",
            data={"error": str(e), "error_type": type(e).__name__},
        )

        # 返回验证失败响应
        return ApiResponse(
            success=True,
            data=TokenVerifyResponse(valid=False, payload=None),
            request_id=request_id,
        )