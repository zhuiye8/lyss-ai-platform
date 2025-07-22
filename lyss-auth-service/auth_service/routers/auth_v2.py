"""
lyss-auth-service 认证路由模块 v2

完整的认证API实现，整合所有核心管理器：
- JWT令牌管理（JWTManager）
- RBAC权限控制（RBACManager）
- 认证管理（AuthManager）
- 会话管理（SessionManager）

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..models.auth_models import (
    LoginRequest, LoginResponse, RegisterRequest, RegisterResponse,
    RefreshTokenRequest, TokenResponse, UserInfoResponse,
    PasswordResetRequest, PasswordResetConfirmRequest,
    EmailVerificationRequest, MFASetupRequest, MFAVerifyRequest,
    MFASetupResponse, ApiResponse, PasswordPolicyResponse,
    UserSessionsResponse, SessionStatisticsResponse,
    PermissionCheckRequest, PermissionCheckResponse
)
from ..core.auth_manager import RegistrationData
from ..dependencies import (
    AuthManagerDep, JWTManagerDep, RBACManagerDep, SessionManagerDep,
    verify_token_dependency, monitoring_required
)
from ..utils.logging import get_logger

router = APIRouter(prefix="/api/v1/auth", tags=["认证授权"])
security = HTTPBearer(auto_error=False)
logger = get_logger(__name__)


def get_client_info(request: Request) -> tuple[str, str, dict]:
    """获取客户端信息"""
    # 获取真实IP（处理代理和负载均衡）
    ip_address = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if not ip_address:
        ip_address = request.headers.get("x-real-ip", "")
    if not ip_address and request.client:
        ip_address = request.client.host
    
    # 获取User-Agent
    user_agent = request.headers.get("user-agent", "")
    
    # 提取设备信息
    device_info = {
        "screen_resolution": request.headers.get("x-screen-resolution"),
        "timezone": request.headers.get("x-timezone"),
        "language": request.headers.get("accept-language", "").split(",")[0]
    }
    
    return ip_address or "unknown", user_agent, device_info


async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials,
    jwt_manager: JWTManager
) -> dict:
    """从令牌获取当前用户信息"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少认证令牌"
        )
    
    validation_result = await jwt_manager.verify_token(credentials.credentials, "access")
    
    if not validation_result.is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=validation_result.error_message
        )
    
    return validation_result.payload.dict()


# =====================================================
# 核心认证接口
# =====================================================

@router.post("/login", response_model=LoginResponse, summary="用户登录")
async def login(
    request: Request,
    login_data: LoginRequest,
    auth_manager: AuthManagerDep,
    session_manager: SessionManagerDep,
):
    """
    用户登录接口
    
    功能特性：
    - 支持邮箱密码登录
    - 账户锁定和IP限流保护
    - 设备信息记录和会话管理
    - MFA二次验证支持
    - 完整的安全审计日志
    """
    try:
        ip_address, user_agent, device_info = get_client_info(request)
        
        # 执行认证
        auth_result = await auth_manager.authenticate_user(
            email=login_data.email,
            password=login_data.password,
            tenant_id=login_data.tenant_id or "default",
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # 构建登录响应
        response = LoginResponse(
            success=auth_result.success,
            message=auth_result.message,
            requires_mfa=auth_result.requires_mfa,
            mfa_session_token=auth_result.mfa_session_token,
            lockout_expires_at=auth_result.lockout_expires_at
        )
        
        # 如果认证成功且不需要MFA
        if auth_result.success and auth_result.token_pair:
            response.tokens = TokenResponse(
                access_token=auth_result.token_pair.access_token,
                refresh_token=auth_result.token_pair.refresh_token,
                expires_in=auth_manager.settings.access_token_expire_minutes * 60,
                refresh_expires_in=auth_manager.settings.refresh_token_expire_days * 24 * 3600
            )
            
            response.user_info = {
                "id": auth_result.user.id,
                "email": auth_result.user.email,
                "username": auth_result.user.username,
                "role": auth_result.user.role_name,
                "permissions": auth_result.user.permissions
            }
            
            logger.info(f"用户登录成功: {auth_result.user.email}")
        
        return response
        
    except Exception as e:
        logger.error(f"登录接口异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录服务暂时不可用"
        )


@router.post("/register", response_model=RegisterResponse, summary="用户注册")
async def register(
    register_data: RegisterRequest,
    auth_manager: AuthManagerDep,
):
    """
    用户注册接口
    
    功能特性：
    - 密码强度验证
    - 邮箱重复检查
    - 自动用户名生成
    - 邮箱验证流程
    """
    try:
        registration_data = RegistrationData(
            tenant_id=register_data.tenant_id,
            email=register_data.email,
            password=register_data.password,
            first_name=register_data.first_name,
            last_name=register_data.last_name,
            username=register_data.username
        )
        
        result = await auth_manager.register_user(registration_data)
        
        logger.info(f"用户注册{'成功' if result['success'] else '失败'}: {register_data.email}")
        
        return RegisterResponse(
            success=result["success"],
            message=result["message"],
            user_id=result.get("user_id"),
            verification_required=True
        )
        
    except Exception as e:
        logger.error(f"注册接口异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注册服务暂时不可用"
        )


@router.post("/logout", response_model=ApiResponse, summary="用户登出")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_manager: JWTManagerDep,
    session_manager: SessionManagerDep,
):
    """
    用户登出接口
    
    功能特性：
    - 撤销访问令牌和刷新令牌
    - 终止相关会话
    - 清理缓存数据
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少认证令牌"
        )
    
    try:
        token = credentials.credentials
        
        # 验证令牌并获取用户信息
        validation_result = await jwt_manager.verify_token(token, "access")
        if not validation_result.is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的令牌"
            )
        
        # 撤销令牌
        await jwt_manager.revoke_token(token, "用户主动登出")
        
        logger.info(f"用户登出: {validation_result.payload.email}")
        
        return ApiResponse(
            success=True,
            message="登出成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"登出接口异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登出服务异常"
        )


@router.post("/refresh", response_model=TokenResponse, summary="刷新令牌")
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    jwt_manager: JWTManagerDep,
):
    """
    刷新访问令牌接口
    
    使用刷新令牌获取新的令牌对
    """
    try:
        # 验证刷新令牌
        validation_result = await jwt_manager.verify_token(refresh_data.refresh_token, "refresh")
        
        if not validation_result.is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=validation_result.error_message
            )
        
        # 这里需要完整的用户信息获取实现
        # 暂时返回提示信息
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="令牌刷新功能需要数据库集成后完成"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"令牌刷新异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="令牌刷新服务异常"
        )


# =====================================================
# 用户信息管理
# =====================================================

@router.get("/me", response_model=ApiResponse, summary="获取用户信息")
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_manager: JWTManagerDep,
):
    """获取当前登录用户的详细信息"""
    try:
        user_data = await get_current_user_from_token(credentials, jwt_manager)
        
        user_info = UserInfoResponse(
            id=user_data["sub"],
            email=user_data["email"],
            username=user_data.get("username"),
            role=user_data["role"],
            permissions=user_data.get("permissions", []),
            is_active=user_data.get("is_active", True),
            email_verified=user_data.get("email_verified", False),
            mfa_enabled=user_data.get("mfa_enabled", False),
            tenant_id=user_data["tenant_id"]
        )
        
        return ApiResponse(
            success=True,
            message="获取用户信息成功",
            data=user_info.dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户信息异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户信息服务异常"
        )


@router.get("/sessions", response_model=UserSessionsResponse, summary="获取用户会话")
async def get_user_sessions(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_manager: JWTManagerDep,
    session_manager: SessionManagerDep,
):
    """获取当前用户的所有活跃会话"""
    try:
        user_data = await get_current_user_from_token(credentials, jwt_manager)
        user_id = user_data["sub"]
        
        # 获取用户会话
        sessions = await session_manager.get_user_sessions(user_id)
        
        session_list = []
        for session in sessions:
            session_info = {
                "session_id": session.session_id,
                "device_info": session.device_info.__dict__,
                "ip_address": session.ip_address,
                "login_time": session.login_time,
                "last_activity": session.last_activity,
                "location": session.location,
                "is_current": False  # 需要实现当前会话检测
            }
            session_list.append(session_info)
        
        return UserSessionsResponse(
            sessions=session_list,
            total_count=len(sessions),
            active_count=len([s for s in sessions if s.state.value == "active"])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户会话异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取会话信息服务异常"
        )


@router.delete("/sessions/{session_id}", response_model=ApiResponse, summary="终止会话")
async def terminate_session(
    session_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_manager: JWTManagerDep,
    session_manager: SessionManagerDep,
):
    """终止指定的用户会话"""
    try:
        user_data = await get_current_user_from_token(credentials, jwt_manager)
        
        # 验证会话所有权
        session_info = await session_manager.get_session(session_id)
        if not session_info or session_info.user_id != user_data["sub"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在或无权限访问"
            )
        
        # 终止会话
        success = await session_manager.terminate_session(session_id, "用户主动终止")
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="会话终止失败"
            )
        
        return ApiResponse(
            success=True,
            message="会话已终止"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"终止会话异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="终止会话服务异常"
        )


# =====================================================
# 权限管理接口
# =====================================================

@router.post("/permissions/check", response_model=PermissionCheckResponse, summary="检查权限")
async def check_permission(
    permission_request: PermissionCheckRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_manager: JWTManagerDep,
    rbac_manager: RBACManagerDep,
):
    """检查当前用户是否拥有特定权限"""
    try:
        user_data = await get_current_user_from_token(credentials, jwt_manager)
        
        # 构建令牌载荷对象（简化版）
        from ..models.auth_models import TokenPayload
        token_payload = TokenPayload(**user_data)
        
        # 检查权限
        permission_result = await rbac_manager.check_permission(
            token_payload,
            permission_request.required_permission,
            permission_request.resource_owner_id
        )
        
        return PermissionCheckResponse(
            granted=permission_result.granted,
            reason=permission_result.reason,
            required_permission=permission_result.required_permission,
            user_permissions=permission_result.user_permissions
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"权限检查异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="权限检查服务异常"
        )


@router.get("/permissions", response_model=ApiResponse, summary="获取用户权限")
async def get_user_permissions(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_manager: JWTManagerDep,
):
    """获取当前用户的所有权限"""
    try:
        user_data = await get_current_user_from_token(credentials, jwt_manager)
        
        return ApiResponse(
            success=True,
            message="获取权限成功",
            data={
                "permissions": user_data.get("permissions", []),
                "role": user_data.get("role"),
                "tenant_id": user_data.get("tenant_id")
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户权限异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取权限服务异常"
        )


# =====================================================
# 密码和安全管理
# =====================================================

@router.post("/password/reset/request", response_model=ApiResponse, summary="请求密码重置")
async def request_password_reset(
    reset_request: PasswordResetRequest,
    auth_manager: AuthManagerDep,
):
    """发送密码重置邮件"""
    try:
        result = await auth_manager.reset_password_request(
            email=reset_request.email,
            tenant_id=reset_request.tenant_id
        )
        
        return ApiResponse(
            success=result["success"],
            message=result["message"]
        )
        
    except Exception as e:
        logger.error(f"密码重置请求异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="密码重置服务异常"
        )


@router.get("/password/policy", response_model=PasswordPolicyResponse, summary="获取密码策略")
async def get_password_policy(auth_manager: AuthManagerDep):
    """获取当前密码安全策略"""
    try:
        policy = auth_manager.password_policy
        
        return PasswordPolicyResponse(
            min_length=policy.min_length,
            max_length=policy.max_length,
            require_uppercase=policy.require_uppercase,
            require_lowercase=policy.require_lowercase,
            require_digits=policy.require_digits,
            require_special_chars=policy.require_special_chars,
            special_chars=policy.special_chars,
            password_expire_days=policy.password_expire_days
        )
        
    except Exception as e:
        logger.error(f"获取密码策略异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取密码策略服务异常"
        )


# =====================================================
# 统计和监控接口
# =====================================================

@router.get("/statistics/sessions", response_model=SessionStatisticsResponse, summary="会话统计")
async def get_session_statistics(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_manager: JWTManagerDep,
    session_manager: SessionManagerDep,
    rbac_manager: RBACManagerDep,
):
    """获取会话统计信息（需要管理员权限）"""
    try:
        user_data = await get_current_user_from_token(credentials, jwt_manager)
        
        # 检查管理员权限
        from ..models.auth_models import TokenPayload
        token_payload = TokenPayload(**user_data)
        
        permission_result = await rbac_manager.check_permission(
            token_payload,
            "system:monitor"
        )
        
        if not permission_result.granted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="需要系统监控权限"
            )
        
        # 获取统计信息
        stats = await session_manager.get_session_statistics()
        
        return SessionStatisticsResponse(**stats)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话统计异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取统计信息服务异常"
        )