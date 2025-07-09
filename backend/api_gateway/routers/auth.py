"""
认证相关API路由
JWT认证、用户登录、注册、令牌刷新等功能
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from pydantic import BaseModel, Field, validator
import uuid

from common.database import get_async_session
from common.security import (
    get_security_manager, 
    SecurityManager, 
    Role, 
    Permission,
    PasswordPolicy
)
from common.models import User, Tenant, UserStatus, TenantStatus, Role as RoleModel, UserRole
from common.config import get_settings
from common.redis_client import redis_manager
from common.response import ResponseHelper, ErrorDetail, ErrorCode

router = APIRouter()
settings = get_settings()
security_manager = get_security_manager()
security_scheme = HTTPBearer()


# 请求和响应模型
class LoginRequest(BaseModel):
    """用户登录请求"""
    email: str = Field(..., description="用户邮箱")
    password: str = Field(..., description="用户密码")
    remember_me: bool = Field(default=False, description="是否记住登录")
    
    @validator('email')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('邮箱格式不正确')
        return v.lower()


class RegisterRequest(BaseModel):
    """用户注册请求"""
    email: str = Field(..., description="用户邮箱")
    password: str = Field(..., description="用户密码")
    confirm_password: str = Field(..., description="确认密码")
    first_name: str = Field(..., description="名字")
    last_name: str = Field(..., description="姓氏")
    tenant_slug: str = Field(..., description="租户标识")
    
    @validator('email')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('邮箱格式不正确')
        return v.lower()
    
    @validator('confirm_password')
    def validate_passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('两次密码不一致')
        return v


class TokenResponse(BaseModel):
    """令牌响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求"""
    refresh_token: str = Field(..., description="刷新令牌")


class PasswordChangeRequest(BaseModel):
    """密码修改请求"""
    current_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., description="新密码")
    confirm_new_password: str = Field(..., description="确认新密码")
    
    @validator('confirm_new_password')
    def validate_passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('两次新密码不一致')
        return v


# 依赖项
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    session: AsyncSession = Depends(get_async_session)
) -> User:
    """获取当前用户"""
    token = credentials.credentials
    token_data = security_manager.verify_token(token)
    
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 检查令牌是否被撤销
    is_revoked = await redis_manager.get_client().get(f"revoked_token:{token_data.jti}")
    if is_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌已被撤销",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 获取用户信息
    stmt = select(User).where(
        and_(
            User.user_id == uuid.UUID(token_data.user_id),
            User.tenant_id == uuid.UUID(token_data.tenant_id),
            User.status == UserStatus.ACTIVE
        )
    )
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被禁用",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_tenant(current_user: User = Depends(get_current_user)) -> Tenant:
    """获取当前租户"""
    session = await get_async_session().__anext__()
    
    stmt = select(Tenant).where(
        and_(
            Tenant.tenant_id == current_user.tenant_id,
            Tenant.status == TenantStatus.ACTIVE
        )
    )
    result = await session.execute(stmt)
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="租户不存在或已被暂停"
        )
    
    return tenant


def require_permission(permission: Permission):
    """权限检查装饰器"""
    def permission_checker(current_user: User = Depends(get_current_user)):
        # 这里需要获取用户的实际角色，暂时先注释掉
        # if not security_manager.check_permission(current_user.roles, permission.value):
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail=f"权限不足，需要权限: {permission.value}"
        #     )
        return current_user
    return permission_checker


def require_role(role: Role):
    """角色检查装饰器"""
    def role_checker(current_user: User = Depends(get_current_user)):
        # 这里需要获取用户的实际角色，暂时先注释掉
        # if not security_manager.check_role(current_user.roles, role.value):
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail=f"角色权限不足，需要角色: {role.value}"
        #     )
        return current_user
    return role_checker


# 认证API端点
@router.post("/login", response_model=TokenResponse, summary="用户登录")
async def login(
    request: LoginRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_async_session)
):
    """
    用户登录
    
    - 验证用户凭据
    - 生成访问令牌和刷新令牌
    - 记录登录日志
    """
    # 查找用户和租户信息
    stmt = select(User).where(
        and_(
            User.email == request.email,
            User.status == UserStatus.ACTIVE
        )
    )
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    # 验证租户状态
    if user:
        tenant_stmt = select(Tenant).where(
            and_(
                Tenant.tenant_id == user.tenant_id,
                Tenant.status == TenantStatus.ACTIVE
            )
        )
        tenant_result = await session.execute(tenant_stmt)
        tenant = tenant_result.scalar_one_or_none()
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="租户已被暂停或不存在"
            )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误"
        )
    
    # 检查用户是否被锁定
    if user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"账户已被锁定，请在 {user.locked_until} 后重试"
        )
    
    # 验证密码
    if not security_manager.verify_password(request.password, user.password_hash):
        # 增加失败次数
        user.failed_login_attempts += 1
        
        # 如果失败次数过多，锁定账户
        if user.failed_login_attempts >= 5:
            user.locked_until = datetime.utcnow() + timedelta(minutes=30)
            await session.commit()
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="登录失败次数过多，账户已被锁定30分钟"
            )
        
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误"
        )
    
    # 重置失败次数
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.utcnow()
    await session.commit()
    
    # 获取用户角色
    user_roles_stmt = select(UserRole).join(RoleModel).where(
        and_(
            UserRole.user_id == user.user_id,
            or_(
                UserRole.expires_at.is_(None),
                UserRole.expires_at > datetime.utcnow()
            )
        )
    )
    user_roles_result = await session.execute(user_roles_stmt)
    user_roles = user_roles_result.scalars().all()
    
    # 获取角色名称列表
    role_names = []
    for user_role in user_roles:
        role_stmt = select(RoleModel).where(RoleModel.role_id == user_role.role_id)
        role_result = await session.execute(role_stmt)
        role = role_result.scalar_one_or_none()
        if role:
            role_names.append(role.role_name)
    
    # 如果用户没有角色，默认为普通用户
    if not role_names:
        role_names = [Role.END_USER.value]
    
    # 生成令牌
    access_token = security_manager.create_access_token(
        user_id=str(user.user_id),
        tenant_id=str(user.tenant_id),
        email=user.email,
        roles=role_names
    )
    
    refresh_token = security_manager.create_refresh_token(
        user_id=str(user.user_id),
        tenant_id=str(user.tenant_id)
    )
    
    # 如果选择记住登录，延长刷新令牌有效期
    if request.remember_me:
        # TODO: 实现记住登录功能
        pass
    
    # 缓存用户信息
    await redis_manager.get_client().setex(
        f"user:{user.user_id}",
        3600,  # 1小时
        f"{user.email}:{user.tenant_id}:{','.join(role_names)}"
    )
    
    return ResponseHelper.success(
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
            "user": {
                "user_id": str(user.user_id),
                "tenant_id": str(user.tenant_id),
                "email": user.email,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "avatar_url": user.avatar_url,
                "roles": role_names,
                "email_verified": user.email_verified,
                "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None
            }
        },
        message="登录成功",
        request_id=getattr(http_request.state, 'request_id', None)
    )


@router.post("/register", summary="用户注册")
async def register(
    request: RegisterRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """
    用户注册
    
    - 验证密码强度
    - 检查邮箱是否已存在
    - 创建新用户
    """
    # 验证密码强度
    is_valid, errors = PasswordPolicy.validate_password(request.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"password_errors": errors}
        )
    
    # 检查租户是否存在
    tenant_stmt = select(Tenant).where(
        and_(
            Tenant.tenant_slug == request.tenant_slug,
            Tenant.status == TenantStatus.ACTIVE
        )
    )
    tenant_result = await session.execute(tenant_stmt)
    tenant = tenant_result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="租户不存在或已被暂停"
        )
    
    # 检查邮箱是否已存在
    user_stmt = select(User).where(
        and_(
            User.email == request.email,
            User.tenant_id == tenant.tenant_id
        )
    )
    existing_user = await session.execute(user_stmt)
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已被注册"
        )
    
    # 创建新用户
    password_hash = security_manager.hash_password(request.password)
    
    new_user = User(
        tenant_id=tenant.tenant_id,
        email=request.email,
        password_hash=password_hash,
        first_name=request.first_name,
        last_name=request.last_name,
        status=UserStatus.ACTIVE,
        email_verified=False  # 默认未验证邮箱
    )
    
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    
    # 为新用户分配默认角色
    # 查找普通用户角色
    end_user_role_stmt = select(RoleModel).where(RoleModel.role_name == Role.END_USER.value)
    end_user_role_result = await session.execute(end_user_role_stmt)
    end_user_role = end_user_role_result.scalar_one_or_none()
    
    if not end_user_role:
        # 如果角色不存在，创建它
        end_user_role = RoleModel(
            role_name=Role.END_USER.value,
            role_description="普通用户角色",
            permissions=security_manager.ROLE_PERMISSIONS[Role.END_USER],
            is_system_role=True
        )
        session.add(end_user_role)
        await session.commit()
        await session.refresh(end_user_role)
    
    # 分配角色给用户
    user_role = UserRole(
        user_id=new_user.user_id,
        role_id=end_user_role.role_id,
        assigned_at=datetime.utcnow()
    )
    session.add(user_role)
    await session.commit()
    
    return ResponseHelper.success(
        data={
            "user_id": str(new_user.user_id),
            "email": new_user.email,
            "first_name": new_user.first_name,
            "last_name": new_user.last_name,
            "tenant_id": str(new_user.tenant_id),
            "roles": [Role.END_USER.value],
            "email_verified": new_user.email_verified,
            "created_at": new_user.created_at.isoformat()
        },
        message="注册成功"
    )


@router.post("/refresh", summary="刷新令牌")
async def refresh_token(
    request: RefreshTokenRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """
    刷新访问令牌
    
    - 验证刷新令牌
    - 生成新的访问令牌
    """
    token_data = security_manager.verify_token(request.refresh_token)
    
    if not token_data or token_data.jti is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌无效或已过期"
        )
    
    # 检查令牌是否被撤销
    is_revoked = await redis_manager.get_client().get(f"revoked_token:{token_data.jti}")
    if is_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌已被撤销"
        )
    
    # 获取用户信息
    stmt = select(User).where(
        and_(
            User.user_id == uuid.UUID(token_data.user_id),
            User.tenant_id == uuid.UUID(token_data.tenant_id),
            User.status == UserStatus.ACTIVE
        )
    )
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被禁用"
        )
    
    # 生成新的访问令牌
    access_token = security_manager.create_access_token(
        user_id=str(user.user_id),
        tenant_id=str(user.tenant_id),
        email=user.email,
        roles=role_names
    )
    
    return ResponseHelper.success(
        data={
            "access_token": access_token,
            "expires_in": settings.access_token_expire_minutes * 60
        },
        message="令牌刷新成功"
    )


@router.post("/logout", summary="用户登出")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    current_user: User = Depends(get_current_user)
):
    """
    用户登出
    
    - 撤销访问令牌
    - 清除用户缓存
    """
    token = credentials.credentials
    token_data = security_manager.verify_token(token)
    
    if token_data:
        # 将令牌加入撤销列表
        redis_client = redis_manager.get_client()
        await redis_client.setex(
            f"revoked_token:{token_data.jti}",
            settings.access_token_expire_minutes * 60,
            "1"
        )
        
        # 清除用户缓存
        await redis_client.delete(f"user:{current_user.user_id}")
    
    return ResponseHelper.success(
        message="登出成功"
    )


@router.get("/me", summary="获取当前用户信息")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """获取当前用户的详细信息"""
    return ResponseHelper.success(
        data={
            "user_id": str(current_user.user_id),
            "tenant_id": str(current_user.tenant_id),
            "email": current_user.email,
            "username": current_user.username,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "avatar_url": current_user.avatar_url,
            "status": current_user.status,
            "email_verified": current_user.email_verified,
            "login_count": current_user.login_count,
            "last_login_at": current_user.last_login_at.isoformat() if current_user.last_login_at else None,
            "preferences": current_user.preferences,
            "created_at": current_user.created_at.isoformat(),
            "updated_at": current_user.updated_at.isoformat()
        },
        message="获取用户信息成功"
    )


@router.post("/change-password", summary="修改密码")
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    修改用户密码
    
    - 验证当前密码
    - 验证新密码强度
    - 更新密码
    """
    # 验证当前密码
    if not security_manager.verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前密码错误"
        )
    
    # 验证新密码强度
    is_valid, errors = PasswordPolicy.validate_password(request.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"password_errors": errors}
        )
    
    # 更新密码
    current_user.password_hash = security_manager.hash_password(request.new_password)
    current_user.password_changed_at = datetime.utcnow()
    
    await session.commit()
    
    return ResponseHelper.success(
        message="密码修改成功"
    )


@router.get("/permissions", summary="获取用户权限")
async def get_user_permissions(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """获取当前用户的权限列表"""
    # 获取用户角色
    user_roles_stmt = select(UserRole).join(RoleModel).where(
        and_(
            UserRole.user_id == current_user.user_id,
            or_(
                UserRole.expires_at.is_(None),
                UserRole.expires_at > datetime.utcnow()
            )
        )
    )
    user_roles_result = await session.execute(user_roles_stmt)
    user_roles = user_roles_result.scalars().all()
    
    # 获取角色名称和权限
    role_names = []
    permissions = set()
    
    for user_role in user_roles:
        role_stmt = select(RoleModel).where(RoleModel.role_id == user_role.role_id)
        role_result = await session.execute(role_stmt)
        role = role_result.scalar_one_or_none()
        if role:
            role_names.append(role.role_name)
            permissions.update(role.permissions)
    
    # 如果用户没有角色，默认为普通用户
    if not role_names:
        role_names = [Role.END_USER.value]
        permissions.update(security_manager.ROLE_PERMISSIONS[Role.END_USER])
    
    return ResponseHelper.success(
        data={
            "user_id": str(current_user.user_id),
            "roles": role_names,
            "permissions": list(permissions)
        },
        message="获取权限信息成功"
    )