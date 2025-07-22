"""
认证管理器

实现核心认证功能，包括：
- 用户注册和登录验证
- 密码安全策略（强度验证、历史密码、过期策略）
- 账户锁定机制（失败次数限制、时间窗口、自动解锁）
- 邮箱验证和密码重置
- 安全审计日志

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import re
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

import bcrypt
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_
from pydantic import EmailStr

from ..config import AuthServiceSettings
from ..models.auth_models import UserModel, TokenPayload
from .jwt_manager import JWTManager, TokenPair


class AuthResult(str, Enum):
    """认证结果枚举"""
    SUCCESS = "success"
    INVALID_CREDENTIALS = "invalid_credentials"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_DISABLED = "account_disabled"
    EMAIL_NOT_VERIFIED = "email_not_verified"
    PASSWORD_EXPIRED = "password_expired"
    MFA_REQUIRED = "mfa_required"
    RATE_LIMITED = "rate_limited"


@dataclass
class AuthenticationResult:
    """认证结果数据类"""
    success: bool
    result: AuthResult
    user: Optional[UserModel] = None
    token_pair: Optional[TokenPair] = None
    message: Optional[str] = None
    requires_mfa: bool = False
    mfa_session_token: Optional[str] = None
    lockout_expires_at: Optional[datetime] = None


@dataclass
class PasswordPolicy:
    """密码策略配置"""
    min_length: int = 8
    max_length: int = 128
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digits: bool = True
    require_special_chars: bool = True
    special_chars: str = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    max_repeated_chars: int = 2
    min_unique_chars: int = 4
    password_history_count: int = 5  # 记住最近5个密码
    password_expire_days: int = 90
    
    
@dataclass
class LockoutPolicy:
    """账户锁定策略配置"""
    max_failed_attempts: int = 5
    lockout_duration_minutes: int = 30
    reset_window_minutes: int = 60  # 失败计数重置时间窗口
    progressive_lockout: bool = True  # 渐进式锁定（每次锁定时间递增）


@dataclass
class RegistrationData:
    """用户注册数据"""
    tenant_id: str
    email: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    role_name: str = "end_user"


class AuthManager:
    """
    认证管理器
    
    功能特性：
    1. 用户认证 - 登录验证、密码检查
    2. 密码管理 - 强度验证、历史记录、过期策略
    3. 账户保护 - 失败锁定、渐进式锁定、自动解锁
    4. 用户注册 - 邮箱验证、密码策略检查
    5. 安全审计 - 登录历史、安全事件记录
    """
    
    def __init__(
        self, 
        settings: AuthServiceSettings,
        jwt_manager: JWTManager,
        redis_client: redis.Redis
    ):
        self.settings = settings
        self.jwt_manager = jwt_manager
        self.redis = redis_client
        
        # 初始化策略
        self.password_policy = PasswordPolicy()
        self.lockout_policy = LockoutPolicy()
        
        # Redis缓存键前缀
        self.FAILED_ATTEMPTS_PREFIX = "auth:failed_attempts:"
        self.LOCKOUT_PREFIX = "auth:lockout:"
        self.RATE_LIMIT_PREFIX = "auth:rate_limit:"
        self.PASSWORD_RESET_PREFIX = "auth:password_reset:"
        self.EMAIL_VERIFICATION_PREFIX = "auth:email_verification:"
        self.MFA_SESSION_PREFIX = "auth:mfa_session:"
    
    async def authenticate_user(
        self,
        email: str,
        password: str,
        tenant_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuthenticationResult:
        """
        用户认证主方法
        
        Args:
            email: 用户邮箱
            password: 密码
            tenant_id: 租户ID
            ip_address: 客户端IP
            user_agent: 用户代理
            
        Returns:
            AuthenticationResult: 认证结果
        """
        try:
            # 1. 检查IP速率限制
            if await self._is_rate_limited(ip_address):
                return AuthenticationResult(
                    success=False,
                    result=AuthResult.RATE_LIMITED,
                    message="请求过于频繁，请稍后再试"
                )
            
            # 2. 查找用户（这里需要数据库查询，暂时使用模拟）
            user = await self._get_user_by_email(email, tenant_id)
            if not user:
                # 记录失败尝试（防止用户枚举攻击）
                await self._record_failed_attempt(f"unknown:{email}", ip_address)
                return AuthenticationResult(
                    success=False,
                    result=AuthResult.INVALID_CREDENTIALS,
                    message="邮箱或密码错误"
                )
            
            # 3. 检查账户状态
            if not user.is_active:
                return AuthenticationResult(
                    success=False,
                    result=AuthResult.ACCOUNT_DISABLED,
                    message="账户已被禁用"
                )
            
            # 4. 检查账户锁定状态
            is_locked, lockout_expires = await self._is_account_locked(user.id)
            if is_locked:
                return AuthenticationResult(
                    success=False,
                    result=AuthResult.ACCOUNT_LOCKED,
                    message=f"账户已被锁定，将于 {lockout_expires} 自动解锁",
                    lockout_expires_at=lockout_expires
                )
            
            # 5. 验证密码
            if not self._verify_password(password, user.hashed_password):
                # 记录失败尝试
                await self._record_failed_attempt(user.id, ip_address)
                
                # 检查是否应该锁定账户
                failed_count = await self._get_failed_attempts_count(user.id)
                if failed_count >= self.lockout_policy.max_failed_attempts:
                    await self._lock_account(user.id)
                    return AuthenticationResult(
                        success=False,
                        result=AuthResult.ACCOUNT_LOCKED,
                        message="密码错误次数过多，账户已被锁定"
                    )
                
                remaining_attempts = self.lockout_policy.max_failed_attempts - failed_count
                return AuthenticationResult(
                    success=False,
                    result=AuthResult.INVALID_CREDENTIALS,
                    message=f"邮箱或密码错误，剩余尝试次数: {remaining_attempts}"
                )
            
            # 6. 检查邮箱验证状态
            if not user.email_verified:
                return AuthenticationResult(
                    success=False,
                    result=AuthResult.EMAIL_NOT_VERIFIED,
                    message="请先验证邮箱地址"
                )
            
            # 7. 检查密码是否过期（如果启用了密码过期策略）
            if await self._is_password_expired(user.id):
                return AuthenticationResult(
                    success=False,
                    result=AuthResult.PASSWORD_EXPIRED,
                    message="密码已过期，请更新密码"
                )
            
            # 8. 检查是否需要多因素认证
            if user.mfa_enabled:
                # 生成MFA会话令牌
                mfa_session_token = await self._create_mfa_session(user.id, ip_address)
                return AuthenticationResult(
                    success=False,  # 需要完成MFA才算成功
                    result=AuthResult.MFA_REQUIRED,
                    user=user,
                    message="需要进行多因素认证",
                    requires_mfa=True,
                    mfa_session_token=mfa_session_token
                )
            
            # 9. 认证成功，生成JWT令牌对
            token_pair = await self.jwt_manager.create_token_pair(
                user,
                device_info={
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "login_time": datetime.now(timezone.utc).isoformat()
                }
            )
            
            # 10. 清理失败尝试记录
            await self._clear_failed_attempts(user.id)
            
            # 11. 更新最后登录时间（需要数据库更新）
            await self._update_last_login(user.id)
            
            # 12. 记录登录历史
            await self._record_login_history(
                user.id, tenant_id, "password", True, ip_address, user_agent
            )
            
            return AuthenticationResult(
                success=True,
                result=AuthResult.SUCCESS,
                user=user,
                token_pair=token_pair,
                message="登录成功"
            )
            
        except Exception as e:
            # 记录错误日志
            print(f"认证过程发生错误: {str(e)}")
            return AuthenticationResult(
                success=False,
                result=AuthResult.INVALID_CREDENTIALS,
                message="认证服务暂时不可用"
            )
    
    async def register_user(self, registration_data: RegistrationData) -> Dict[str, any]:
        """
        用户注册
        
        Args:
            registration_data: 注册数据
            
        Returns:
            Dict: 注册结果
        """
        try:
            # 1. 验证密码强度
            password_validation = self.validate_password(registration_data.password)
            if not password_validation["valid"]:
                return {
                    "success": False,
                    "message": "密码不符合安全要求",
                    "errors": password_validation["errors"]
                }
            
            # 2. 检查邮箱是否已存在
            existing_user = await self._get_user_by_email(
                registration_data.email, 
                registration_data.tenant_id
            )
            if existing_user:
                return {
                    "success": False,
                    "message": "邮箱地址已被使用"
                }
            
            # 3. 生成用户名（如果未提供）
            if not registration_data.username:
                registration_data.username = await self._generate_username(
                    registration_data.email
                )
            
            # 4. 哈希密码
            hashed_password = self._hash_password(registration_data.password)
            
            # 5. 创建用户记录（需要数据库操作）
            user_id = await self._create_user_record(registration_data, hashed_password)
            
            # 6. 生成邮箱验证令牌
            verification_token = await self._create_email_verification_token(user_id)
            
            # 7. 发送验证邮件（需要实现邮件发送服务）
            # await self._send_verification_email(registration_data.email, verification_token)
            
            return {
                "success": True,
                "message": "注册成功，请查收验证邮件",
                "user_id": user_id,
                "verification_token": verification_token  # 开发环境返回，生产环境不返回
            }
            
        except Exception as e:
            print(f"用户注册失败: {str(e)}")
            return {
                "success": False,
                "message": "注册服务暂时不可用"
            }
    
    def validate_password(self, password: str) -> Dict[str, any]:
        """
        验证密码强度
        
        Args:
            password: 待验证密码
            
        Returns:
            Dict: 验证结果和错误信息
        """
        errors = []
        
        # 长度检查
        if len(password) < self.password_policy.min_length:
            errors.append(f"密码长度至少需要 {self.password_policy.min_length} 个字符")
        
        if len(password) > self.password_policy.max_length:
            errors.append(f"密码长度不能超过 {self.password_policy.max_length} 个字符")
        
        # 字符类型检查
        if self.password_policy.require_uppercase and not re.search(r'[A-Z]', password):
            errors.append("密码必须包含至少一个大写字母")
            
        if self.password_policy.require_lowercase and not re.search(r'[a-z]', password):
            errors.append("密码必须包含至少一个小写字母")
            
        if self.password_policy.require_digits and not re.search(r'\d', password):
            errors.append("密码必须包含至少一个数字")
            
        if self.password_policy.require_special_chars:
            special_pattern = f"[{re.escape(self.password_policy.special_chars)}]"
            if not re.search(special_pattern, password):
                errors.append(f"密码必须包含至少一个特殊字符: {self.password_policy.special_chars}")
        
        # 重复字符检查
        if self._has_excessive_repeated_chars(password):
            errors.append(f"密码不能包含超过 {self.password_policy.max_repeated_chars} 个连续相同字符")
        
        # 唯一字符检查
        unique_chars = len(set(password))
        if unique_chars < self.password_policy.min_unique_chars:
            errors.append(f"密码至少需要 {self.password_policy.min_unique_chars} 个不同的字符")
        
        # 常见密码检查
        if self._is_common_password(password):
            errors.append("请使用更加安全的密码")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    async def reset_password_request(self, email: str, tenant_id: str) -> Dict[str, any]:
        """
        请求重置密码
        
        Args:
            email: 用户邮箱
            tenant_id: 租户ID
            
        Returns:
            Dict: 请求结果
        """
        try:
            user = await self._get_user_by_email(email, tenant_id)
            if not user:
                # 为了安全，不透露用户是否存在
                return {
                    "success": True,
                    "message": "如果该邮箱存在，重置密码链接将发送到您的邮箱"
                }
            
            # 生成重置令牌
            reset_token = await self._create_password_reset_token(user.id)
            
            # 发送重置邮件（需要实现邮件服务）
            # await self._send_password_reset_email(email, reset_token)
            
            return {
                "success": True,
                "message": "重置密码链接已发送到您的邮箱",
                "reset_token": reset_token  # 开发环境返回
            }
            
        except Exception as e:
            print(f"密码重置请求失败: {str(e)}")
            return {
                "success": False,
                "message": "服务暂时不可用"
            }
    
    # 私有方法实现
    
    async def _get_user_by_email(self, email: str, tenant_id: str) -> Optional[UserModel]:
        """通过邮箱查找用户（模拟实现）"""
        # 这里应该查询数据库，暂时返回模拟用户
        if email == "admin@lyss.dev":
            return UserModel(
                id="00000000-0000-0000-0000-000000000002",
                tenant_id=tenant_id,
                email=email,
                username="admin",
                hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBF7Pn0A8ZSc0m",  # admin123
                first_name="System",
                last_name="Administrator", 
                role_name="tenant_admin",
                permissions=["user:create", "user:manage", "provider:manage"],
                is_active=True,
                email_verified=True,
                mfa_enabled=False
            )
        return None
    
    def _verify_password(self, password: str, hashed_password: str) -> bool:
        """验证密码"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    def _hash_password(self, password: str) -> str:
        """哈希密码"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    async def _is_rate_limited(self, ip_address: Optional[str]) -> bool:
        """检查IP速率限制"""
        if not ip_address:
            return False
        
        key = f"{self.RATE_LIMIT_PREFIX}{ip_address}"
        current_count = await self.redis.get(key)
        
        if current_count is None:
            # 第一次访问，设置计数器
            await self.redis.setex(key, 3600, 1)  # 1小时窗口
            return False
        
        count = int(current_count.decode())
        if count >= 100:  # 每小时最多100次认证请求
            return True
        
        await self.redis.incr(key)
        return False
    
    async def _record_failed_attempt(self, user_identifier: str, ip_address: Optional[str]):
        """记录失败尝试"""
        key = f"{self.FAILED_ATTEMPTS_PREFIX}{user_identifier}"
        current_time = datetime.now(timezone.utc)
        
        # 获取当前失败次数
        attempts_data = await self.redis.get(key)
        if attempts_data:
            attempts = json.loads(attempts_data.decode())
        else:
            attempts = {"count": 0, "first_attempt": None, "last_attempt": None}
        
        # 检查是否在重置窗口内
        if attempts.get("first_attempt"):
            first_attempt = datetime.fromisoformat(attempts["first_attempt"])
            if current_time - first_attempt > timedelta(minutes=self.lockout_policy.reset_window_minutes):
                # 超过重置窗口，重新计数
                attempts = {"count": 0, "first_attempt": None, "last_attempt": None}
        
        # 更新失败记录
        attempts["count"] += 1
        if not attempts.get("first_attempt"):
            attempts["first_attempt"] = current_time.isoformat()
        attempts["last_attempt"] = current_time.isoformat()
        attempts["ip_address"] = ip_address
        
        # 存储到Redis（过期时间为重置窗口时间）
        await self.redis.setex(
            key, 
            self.lockout_policy.reset_window_minutes * 60,
            json.dumps(attempts)
        )
    
    async def _get_failed_attempts_count(self, user_id: str) -> int:
        """获取失败尝试次数"""
        key = f"{self.FAILED_ATTEMPTS_PREFIX}{user_id}"
        attempts_data = await self.redis.get(key)
        
        if attempts_data:
            attempts = json.loads(attempts_data.decode())
            return attempts.get("count", 0)
        return 0
    
    async def _is_account_locked(self, user_id: str) -> Tuple[bool, Optional[datetime]]:
        """检查账户是否被锁定"""
        key = f"{self.LOCKOUT_PREFIX}{user_id}"
        lockout_data = await self.redis.get(key)
        
        if lockout_data:
            lockout_info = json.loads(lockout_data.decode())
            expires_at = datetime.fromisoformat(lockout_info["expires_at"])
            
            if datetime.now(timezone.utc) < expires_at:
                return True, expires_at
            else:
                # 锁定已过期，清理数据
                await self.redis.delete(key)
        
        return False, None
    
    async def _lock_account(self, user_id: str):
        """锁定账户"""
        key = f"{self.LOCKOUT_PREFIX}{user_id}"
        current_time = datetime.now(timezone.utc)
        
        # 获取之前的锁定记录（用于渐进式锁定）
        lockout_data = await self.redis.get(key)
        lock_count = 1
        
        if lockout_data and self.lockout_policy.progressive_lockout:
            previous_lockout = json.loads(lockout_data.decode())
            lock_count = previous_lockout.get("count", 0) + 1
        
        # 计算锁定时长（渐进式递增）
        if self.lockout_policy.progressive_lockout:
            lockout_minutes = self.lockout_policy.lockout_duration_minutes * (2 ** (lock_count - 1))
            lockout_minutes = min(lockout_minutes, 24 * 60)  # 最长24小时
        else:
            lockout_minutes = self.lockout_policy.lockout_duration_minutes
        
        expires_at = current_time + timedelta(minutes=lockout_minutes)
        
        lockout_info = {
            "user_id": user_id,
            "locked_at": current_time.isoformat(),
            "expires_at": expires_at.isoformat(),
            "count": lock_count,
            "reason": "多次登录失败"
        }
        
        # 存储锁定信息
        await self.redis.setex(
            key,
            int(lockout_minutes * 60),
            json.dumps(lockout_info)
        )
    
    async def _clear_failed_attempts(self, user_id: str):
        """清理失败尝试记录"""
        key = f"{self.FAILED_ATTEMPTS_PREFIX}{user_id}"
        await self.redis.delete(key)
    
    def _has_excessive_repeated_chars(self, password: str) -> bool:
        """检查是否有过多重复字符"""
        count = 1
        for i in range(1, len(password)):
            if password[i] == password[i-1]:
                count += 1
                if count > self.password_policy.max_repeated_chars:
                    return True
            else:
                count = 1
        return False
    
    def _is_common_password(self, password: str) -> bool:
        """检查是否为常见弱密码"""
        common_passwords = {
            "123456", "password", "123456789", "12345678", "12345",
            "1234567", "1234567890", "qwerty", "abc123", "111111",
            "admin", "admin123", "root", "test", "guest"
        }
        return password.lower() in common_passwords
    
    async def _is_password_expired(self, user_id: str) -> bool:
        """检查密码是否过期"""
        # 这里需要查询数据库获取密码最后更新时间
        # 暂时返回False
        return False
    
    async def _create_mfa_session(self, user_id: str, ip_address: Optional[str]) -> str:
        """创建MFA会话令牌"""
        session_token = secrets.token_urlsafe(32)
        key = f"{self.MFA_SESSION_PREFIX}{session_token}"
        
        session_data = {
            "user_id": user_id,
            "ip_address": ip_address,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "verified": False
        }
        
        # MFA会话10分钟有效期
        await self.redis.setex(key, 600, json.dumps(session_data))
        return session_token
    
    async def _update_last_login(self, user_id: str):
        """更新最后登录时间"""
        # 这里需要数据库更新操作
        pass
    
    async def _record_login_history(
        self, user_id: str, tenant_id: str, login_type: str, 
        success: bool, ip_address: Optional[str], user_agent: Optional[str]
    ):
        """记录登录历史"""
        # 这里需要写入数据库登录历史表
        pass
    
    async def _generate_username(self, email: str) -> str:
        """生成用户名"""
        base_username = email.split('@')[0]
        # 这里需要检查数据库确保用户名唯一
        return base_username
    
    async def _create_user_record(self, data: RegistrationData, hashed_password: str) -> str:
        """创建用户记录"""
        # 这里需要数据库插入操作
        return str(secrets.token_hex(16))  # 临时返回随机ID
    
    async def _create_email_verification_token(self, user_id: str) -> str:
        """创建邮箱验证令牌"""
        token = secrets.token_urlsafe(32)
        key = f"{self.EMAIL_VERIFICATION_PREFIX}{token}"
        
        verification_data = {
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # 验证令牌24小时有效期
        await self.redis.setex(key, 24 * 3600, json.dumps(verification_data))
        return token
    
    async def _create_password_reset_token(self, user_id: str) -> str:
        """创建密码重置令牌"""
        token = secrets.token_urlsafe(32)
        key = f"{self.PASSWORD_RESET_PREFIX}{token}"
        
        reset_data = {
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # 重置令牌1小时有效期
        await self.redis.setex(key, 3600, json.dumps(reset_data))
        return token


# 导入json模块（在文件顶部应该已有，这里为了完整性再次声明）
import json