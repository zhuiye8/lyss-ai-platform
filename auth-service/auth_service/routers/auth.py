"""
Auth Service 用户认证路由
实现用户登录接口，严格遵循OAuth2标准
"""

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm

from ..models.schemas.login import TokenResponse
from ..models.schemas.response import ApiResponse
from ..services.auth_service import auth_service
from ..middleware.request_logging import request_id_var
from ..utils.logging import logger

router = APIRouter()


def get_client_info(request: Request) -> dict:
    """提取客户端信息"""
    # 获取客户端IP
    client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    if not client_ip:
        client_ip = request.headers.get("X-Real-IP", "")
    if not client_ip and request.client:
        client_ip = request.client.host

    # 获取用户代理
    user_agent = request.headers.get("User-Agent", "")

    return {
        "client_ip": client_ip or "unknown",
        "user_agent": user_agent,
    }


@router.post(
    "/token",
    response_model=ApiResponse[TokenResponse],
    summary="用户登录",
    description="使用用户名/邮箱和密码进行登录，返回JWT访问令牌和刷新令牌",
    responses={
        200: {
            "description": "登录成功",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "token_type": "bearer",
                            "expires_in": 1800,
                            "refresh_token": "refresh_token_string",
                            "user_info": {
                                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                                "email": "user@example.com",
                                "tenant_id": "550e8400-e29b-41d4-a716-446655440001",
                                "role": "end_user",
                                "is_active": True,
                            },
                        },
                        "message": "登录成功",
                        "request_id": "req-20250710143025-a1b2c3d4",
                        "timestamp": "2025-07-10T10:30:00Z",
                    }
                }
            },
        },
        401: {
            "description": "认证失败",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": {
                            "code": "3004",
                            "message": "用户名或密码错误",
                            "details": None,
                        },
                        "request_id": "req-20250710143025-a1b2c3d4",
                        "timestamp": "2025-07-10T10:30:00Z",
                    }
                }
            },
        },
        429: {
            "description": "速率限制",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": {
                            "code": "1005",
                            "message": "登录尝试次数过多，请60秒后再试",
                            "details": {
                                "max_attempts": 10,
                                "window_seconds": 60,
                                "current_attempts": 11,
                            },
                        },
                        "request_id": "req-20250710143025-a1b2c3d4",
                        "timestamp": "2025-07-10T10:30:00Z",
                    }
                }
            },
        },
    },
)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """
    用户登录接口

    使用OAuth2PasswordRequestForm标准格式接收登录凭证：
    - username: 用户名或邮箱地址
    - password: 用户密码

    成功登录后返回：
    - access_token: JWT访问令牌（30分钟有效期）
    - refresh_token: 刷新令牌（7天有效期）
    - user_info: 用户基本信息
    """
    # 获取请求ID和客户端信息
    try:
        request_id = request_id_var.get()
    except LookupError:
        request_id = "unknown"

    client_info = get_client_info(request)

    # 记录登录尝试
    logger.info(
        f"用户登录尝试: {form_data.username}",
        operation="login_attempt",
        data={
            "username": form_data.username,
            "client_ip": client_info["client_ip"],
            "user_agent": client_info["user_agent"],
        },
    )

    # 执行认证
    token_response = await auth_service.authenticate_user(
        username=form_data.username,
        password=form_data.password,
        client_ip=client_info["client_ip"],
        user_agent=client_info["user_agent"],
        request_id=request_id,
    )

    # 返回成功响应
    return ApiResponse(
        success=True,
        data=token_response,
        message="登录成功",
        request_id=request_id,
    )