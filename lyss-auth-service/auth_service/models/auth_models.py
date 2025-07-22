"""
认证服务数据模型

定义认证服务相关的所有数据模型，包括：
- 用户模型（数据库实体和业务模型）
- 令牌载荷模型
- 请求响应模型
- 认证结果模型

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field, validator
from dataclasses import dataclass


# =====================================================
# 基础数据模型
# =====================================================

class UserModel(BaseModel):
    """用户业务模型"""
    id: str
    tenant_id: str
    email: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    hashed_password: str
    role_name: str
    permissions: List[str] = []
    is_active: bool = True
    email_verified: bool = False
    mfa_enabled: bool = False
    last_login_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TokenPayload(BaseModel):
    """JWT令牌载荷模型"""
    sub: str  # 用户ID
    tenant_id: str
    email: str
    username: Optional[str] = None
    role: str
    permissions: List[str] = []
    is_active: bool = True
    email_verified: bool = False
    mfa_enabled: bool = False
    exp: int  # 过期时间戳
    iat: int  # 签发时间戳
    jti: str  # JWT ID

    class Config:
        from_attributes = True


# =====================================================
# 请求模型
# =====================================================

class LoginRequest(BaseModel):
    """登录请求模型"""
    email: EmailStr = Field(..., description="用户邮箱")
    password: str = Field(..., min_length=1, description="用户密码")
    tenant_id: Optional[str] = Field(None, description="租户ID")
    device_info: Optional[Dict[str, Any]] = Field(None, description="设备信息")
    
    @validator('password')
    def validate_password(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('密码不能为空')
        return v


class RegisterRequest(BaseModel):
    """用户注册请求模型"""
    email: EmailStr = Field(..., description="用户邮箱")
    password: str = Field(..., min_length=8, max_length=128, description="用户密码")
    first_name: Optional[str] = Field(None, max_length=100, description="名")
    last_name: Optional[str] = Field(None, max_length=100, description="姓")
    username: Optional[str] = Field(None, max_length=100, description="用户名")
    tenant_id: str = Field(..., description="租户ID")
    
    @validator('password')
    def validate_password_strength(cls, v):
        """验证密码强度"""
        if len(v) < 8:
            raise ValueError('密码长度至少8个字符')
        if not any(c.isupper() for c in v):
            raise ValueError('密码必须包含至少一个大写字母')
        if not any(c.islower() for c in v):
            raise ValueError('密码必须包含至少一个小写字母')
        if not any(c.isdigit() for c in v):
            raise ValueError('密码必须包含至少一个数字')
        return v


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求模型"""
    refresh_token: str = Field(..., description="刷新令牌")


class PasswordResetRequest(BaseModel):
    """密码重置请求模型"""
    email: EmailStr = Field(..., description="用户邮箱")
    tenant_id: str = Field(..., description="租户ID")


class PasswordResetConfirmRequest(BaseModel):
    """确认密码重置请求模型"""
    reset_token: str = Field(..., description="重置令牌")
    new_password: str = Field(..., min_length=8, max_length=128, description="新密码")
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """验证新密码强度"""
        if len(v) < 8:
            raise ValueError('密码长度至少8个字符')
        return v


class EmailVerificationRequest(BaseModel):
    """邮箱验证请求模型"""
    verification_token: str = Field(..., description="验证令牌")


class MFASetupRequest(BaseModel):
    """MFA设置请求模型"""
    mfa_type: str = Field(..., description="MFA类型：totp、sms")
    phone_number: Optional[str] = Field(None, description="手机号（SMS MFA）")


class MFAVerifyRequest(BaseModel):
    """MFA验证请求模型"""
    mfa_session_token: str = Field(..., description="MFA会话令牌")
    verification_code: str = Field(..., min_length=6, max_length=8, description="验证码")


class OAuth2AuthorizeRequest(BaseModel):
    """OAuth2授权请求模型"""
    provider: str = Field(..., description="OAuth2提供商 (google, github, microsoft)")
    tenant_id: str = Field(..., description="租户ID")
    redirect_after_auth: Optional[str] = Field(None, description="认证成功后的重定向URL")


class OAuth2CallbackRequest(BaseModel):
    """OAuth2回调请求模型"""
    code: str = Field(..., description="授权码")
    state: str = Field(..., description="状态参数")
    error: Optional[str] = Field(None, description="错误信息")
    error_description: Optional[str] = Field(None, description="错误描述")


class PermissionCheckRequest(BaseModel):
    """权限检查请求模型"""
    required_permission: str = Field(..., description="所需权限")
    resource_owner_id: Optional[str] = Field(None, description="资源所有者ID")


# =====================================================
# 响应模型
# =====================================================

class TokenResponse(BaseModel):
    """令牌响应模型"""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int  # 访问令牌过期时间（秒）
    refresh_expires_in: int  # 刷新令牌过期时间（秒）


class LoginResponse(BaseModel):
    """登录响应模型"""
    success: bool
    message: str
    tokens: Optional[TokenResponse] = None
    user_info: Optional[Dict[str, Any]] = None
    requires_mfa: bool = False
    mfa_session_token: Optional[str] = None
    lockout_expires_at: Optional[datetime] = None


class RegisterResponse(BaseModel):
    """注册响应模型"""
    success: bool
    message: str
    user_id: Optional[str] = None
    verification_required: bool = True


class UserInfoResponse(BaseModel):
    """用户信息响应模型"""
    id: str
    email: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str
    permissions: List[str]
    is_active: bool
    email_verified: bool
    mfa_enabled: bool
    last_login_at: Optional[datetime] = None
    tenant_id: str


class SessionInfoResponse(BaseModel):
    """会话信息响应模型"""
    session_id: str
    device_info: Dict[str, Any]
    ip_address: str
    login_time: datetime
    last_activity: datetime
    location: Optional[str] = None
    is_current: bool = False


class UserSessionsResponse(BaseModel):
    """用户会话列表响应模型"""
    sessions: List[SessionInfoResponse]
    total_count: int
    active_count: int


class PermissionCheckResponse(BaseModel):
    """权限检查响应模型"""
    granted: bool
    reason: Optional[str] = None
    required_permission: Optional[str] = None
    user_permissions: Optional[List[str]] = None


class MFASetupResponse(BaseModel):
    """MFA设置响应模型"""
    success: bool
    message: str
    secret_key: Optional[str] = None  # TOTP密钥
    qr_code_url: Optional[str] = None  # TOTP二维码URL


class OAuth2AuthorizeResponse(BaseModel):
    """OAuth2授权响应模型"""
    auth_url: str
    state: str
    provider: str
    message: str = "请在新窗口中完成OAuth2认证"


class OAuth2ProvidersResponse(BaseModel):
    """OAuth2提供商列表响应模型"""
    providers: List[Dict[str, Any]]
    total_count: int
    message: str = "获取OAuth2提供商列表成功"


class OAuth2LoginResponse(BaseModel):
    """OAuth2登录响应模型"""
    success: bool
    message: str
    tokens: Optional[TokenResponse] = None
    user_info: Optional[Dict[str, Any]] = None
    is_new_user: bool = False  # 是否为新注册用户
    provider: Optional[str] = None


class SessionStatisticsResponse(BaseModel):
    """会话统计响应模型"""
    active_sessions: int
    suspicious_sessions: int
    active_users: int
    device_distribution: Dict[str, int]
    avg_sessions_per_user: float


# =====================================================
# 内部数据模型
# =====================================================

@dataclass
class AuthContext:
    """认证上下文"""
    user_id: str
    tenant_id: str
    session_id: str
    permissions: List[str]
    is_admin: bool = False


class ApiResponse(BaseModel):
    """统一API响应模型"""
    success: bool
    message: str
    data: Optional[Any] = None
    errors: Optional[List[str]] = None
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PaginatedResponse(BaseModel):
    """分页响应模型"""
    success: bool = True
    message: str = "查询成功"
    data: List[Any]
    pagination: Dict[str, Any]
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# =====================================================
# 错误模型
# =====================================================

class AuthError(BaseModel):
    """认证错误模型"""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ValidationError(BaseModel):
    """验证错误模型"""
    field: str
    message: str
    value: Optional[Any] = None


# =====================================================
# 配置模型
# =====================================================

class PasswordPolicyResponse(BaseModel):
    """密码策略响应模型"""
    min_length: int
    max_length: int
    require_uppercase: bool
    require_lowercase: bool
    require_digits: bool
    require_special_chars: bool
    special_chars: str
    password_expire_days: int


class SecuritySettingsResponse(BaseModel):
    """安全设置响应模型"""
    password_policy: PasswordPolicyResponse
    session_timeout_minutes: int
    max_concurrent_sessions: int
    mfa_enabled: bool
    lockout_enabled: bool
    max_failed_attempts: int
    lockout_duration_minutes: int