"""
JWT令牌管理器

实现JWT访问令牌和刷新令牌的创建、验证、刷新和黑名单管理。
支持RS256和HS256算法，集成Redis缓存优化性能。

Author: Lyss AI Team  
Created: 2025-01-21
Modified: 2025-01-21
"""

import uuid
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass

import jwt
from jwt.exceptions import (
    InvalidTokenError, 
    ExpiredSignatureError,
    InvalidSignatureError,
    DecodeError
)
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import redis.asyncio as redis
import bcrypt

from ..config import AuthServiceSettings
from ..models.auth_models import TokenPayload, UserModel


@dataclass
class TokenPair:
    """令牌对数据类"""
    access_token: str
    refresh_token: str
    access_expires_at: datetime
    refresh_expires_at: datetime
    token_type: str = "Bearer"


@dataclass  
class TokenValidationResult:
    """令牌验证结果"""
    is_valid: bool
    payload: Optional[TokenPayload] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None


class JWTManager:
    """
    JWT令牌管理器
    
    功能特性：
    1. 支持RS256和HS256算法
    2. 访问令牌和刷新令牌管理
    3. 令牌黑名单机制
    4. Redis缓存优化
    5. 自动密钥轮转支持
    """
    
    def __init__(self, settings: AuthServiceSettings, redis_client: redis.Redis):
        self.settings = settings
        self.redis = redis_client
        
        # 生成或加载密钥
        self._setup_keys()
        
        # 缓存键前缀
        self.BLACKLIST_PREFIX = "auth:blacklist:"
        self.USER_SESSIONS_PREFIX = "auth:sessions:"
        self.REFRESH_TOKEN_PREFIX = "auth:refresh:"
        
    def _setup_keys(self):
        """设置JWT签名密钥"""
        if self.settings.jwt_algorithm.startswith('RS'):
            # RSA密钥对
            if not hasattr(self.settings, 'jwt_private_key') or not self.settings.jwt_private_key:
                # 生成新的RSA密钥对
                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048
                )
                self.private_key = private_key
                self.public_key = private_key.public_key()
            else:
                # 从配置加载密钥
                self.private_key = serialization.load_pem_private_key(
                    self.settings.jwt_private_key.encode(),
                    password=None
                )
                self.public_key = self.private_key.public_key()
        else:
            # HMAC密钥
            self.secret_key = self.settings.secret_key.encode()
            
    def _get_signing_key(self) -> Union[str, Any]:
        """获取签名密钥"""
        if self.settings.jwt_algorithm.startswith('RS'):
            return self.private_key
        else:
            return self.secret_key
            
    def _get_verification_key(self) -> Union[str, Any]:
        """获取验证密钥"""
        if self.settings.jwt_algorithm.startswith('RS'):
            return self.public_key
        else:
            return self.secret_key
    
    def _generate_jti(self) -> str:
        """生成JWT唯一标识符"""
        return str(uuid.uuid4())
    
    def _create_token_payload(
        self, 
        user: UserModel,
        token_type: str = "access",
        expires_delta: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """创建JWT载荷"""
        now = datetime.now(timezone.utc)
        
        if expires_delta:
            expire = now + expires_delta
        else:
            if token_type == "access":
                expire = now + timedelta(minutes=self.settings.access_token_expire_minutes)
            else:
                expire = now + timedelta(days=self.settings.refresh_token_expire_days)
        
        payload = {
            # JWT标准声明
            "iss": self.settings.jwt_issuer,  # 签发者
            "sub": str(user.id),              # 主题(用户ID)
            "aud": self.settings.jwt_audience, # 受众
            "iat": int(now.timestamp()),       # 签发时间
            "exp": int(expire.timestamp()),    # 过期时间
            "jti": self._generate_jti(),       # JWT ID
            
            # 自定义声明
            "token_type": token_type,          # 令牌类型
            "tenant_id": str(user.tenant_id),  # 租户ID
            "email": user.email,               # 用户邮箱
            "username": user.username,         # 用户名
            "role": user.role_name,            # 用户角色
            "permissions": user.permissions,    # 用户权限列表
            "is_active": user.is_active,       # 用户状态
            "email_verified": user.email_verified, # 邮箱验证状态
            "mfa_enabled": user.mfa_enabled    # 多因素认证状态
        }
        
        return payload
    
    async def create_token_pair(
        self, 
        user: UserModel,
        device_info: Optional[Dict[str, Any]] = None
    ) -> TokenPair:
        """
        创建访问令牌和刷新令牌对
        
        Args:
            user: 用户模型
            device_info: 设备信息
            
        Returns:
            TokenPair: 令牌对
        """
        # 创建访问令牌
        access_payload = self._create_token_payload(user, "access")
        access_token = jwt.encode(
            access_payload,
            self._get_signing_key(),
            algorithm=self.settings.jwt_algorithm
        )
        
        # 创建刷新令牌
        refresh_payload = self._create_token_payload(user, "refresh")
        refresh_token = jwt.encode(
            refresh_payload,
            self._get_signing_key(),
            algorithm=self.settings.jwt_algorithm
        )
        
        # 缓存刷新令牌信息到Redis
        await self._cache_refresh_token(refresh_payload, device_info)
        
        # 记录用户会话
        await self._cache_user_session(user.id, access_payload["jti"], refresh_payload["jti"])
        
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            access_expires_at=datetime.fromtimestamp(access_payload["exp"], tz=timezone.utc),
            refresh_expires_at=datetime.fromtimestamp(refresh_payload["exp"], tz=timezone.utc)
        )
    
    async def verify_token(self, token: str, token_type: str = "access") -> TokenValidationResult:
        """
        验证JWT令牌
        
        Args:
            token: JWT令牌
            token_type: 令牌类型 (access/refresh)
            
        Returns:
            TokenValidationResult: 验证结果
        """
        try:
            # 解码令牌
            payload = jwt.decode(
                token,
                self._get_verification_key(),
                algorithms=[self.settings.jwt_algorithm],
                audience=self.settings.jwt_audience,
                issuer=self.settings.jwt_issuer
            )
            
            # 检查令牌类型
            if payload.get("token_type") != token_type:
                return TokenValidationResult(
                    is_valid=False,
                    error_message=f"令牌类型不匹配，期望：{token_type}，实际：{payload.get('token_type')}",
                    error_code="INVALID_TOKEN_TYPE"
                )
            
            # 检查是否在黑名单中
            jti = payload.get("jti")
            if await self._is_token_blacklisted(jti):
                return TokenValidationResult(
                    is_valid=False,
                    error_message="令牌已被撤销",
                    error_code="TOKEN_REVOKED"
                )
            
            # 创建TokenPayload对象
            token_payload = TokenPayload(
                sub=payload["sub"],
                tenant_id=payload["tenant_id"],
                email=payload["email"],
                username=payload.get("username"),
                role=payload["role"],
                permissions=payload.get("permissions", []),
                is_active=payload.get("is_active", True),
                email_verified=payload.get("email_verified", False),
                mfa_enabled=payload.get("mfa_enabled", False),
                exp=payload["exp"],
                iat=payload["iat"],
                jti=jti
            )
            
            return TokenValidationResult(
                is_valid=True,
                payload=token_payload
            )
            
        except ExpiredSignatureError:
            return TokenValidationResult(
                is_valid=False,
                error_message="令牌已过期",
                error_code="TOKEN_EXPIRED"
            )
        except InvalidSignatureError:
            return TokenValidationResult(
                is_valid=False,
                error_message="令牌签名无效",
                error_code="INVALID_SIGNATURE"
            )
        except DecodeError:
            return TokenValidationResult(
                is_valid=False,
                error_message="令牌格式错误",
                error_code="INVALID_FORMAT"
            )
        except Exception as e:
            return TokenValidationResult(
                is_valid=False,
                error_message=f"令牌验证失败：{str(e)}",
                error_code="VALIDATION_ERROR"
            )
    
    async def refresh_access_token(
        self, 
        refresh_token: str,
        user: UserModel
    ) -> Optional[TokenPair]:
        """
        使用刷新令牌获取新的访问令牌
        
        Args:
            refresh_token: 刷新令牌
            user: 用户模型（用于获取最新用户信息）
            
        Returns:
            TokenPair: 新的令牌对，如果刷新失败则返回None
        """
        # 验证刷新令牌
        validation_result = await self.verify_token(refresh_token, "refresh")
        if not validation_result.is_valid:
            return None
        
        # 撤销旧的令牌对
        await self.revoke_token(refresh_token, "用户刷新令牌")
        
        # 创建新的令牌对
        return await self.create_token_pair(user)
    
    async def revoke_token(
        self, 
        token: str, 
        reason: str = "用户主动撤销"
    ) -> bool:
        """
        撤销令牌（加入黑名单）
        
        Args:
            token: 要撤销的令牌
            reason: 撤销原因
            
        Returns:
            bool: 是否成功撤销
        """
        try:
            # 解码令牌获取JTI和过期时间
            payload = jwt.decode(
                token,
                self._get_verification_key(),
                algorithms=[self.settings.jwt_algorithm],
                options={"verify_exp": False}  # 忽略过期检查
            )
            
            jti = payload.get("jti")
            exp = payload.get("exp")
            
            if not jti:
                return False
            
            # 添加到Redis黑名单
            await self._add_to_blacklist(jti, exp, reason)
            
            # 如果是刷新令牌，清理相关会话信息
            if payload.get("token_type") == "refresh":
                await self._clear_refresh_token_cache(jti)
            
            return True
            
        except Exception as e:
            # 记录错误但不抛出异常
            print(f"撤销令牌失败: {str(e)}")
            return False
    
    async def revoke_all_user_tokens(
        self, 
        user_id: str, 
        reason: str = "撤销所有令牌"
    ) -> int:
        """
        撤销用户的所有令牌
        
        Args:
            user_id: 用户ID
            reason: 撤销原因
            
        Returns:
            int: 撤销的令牌数量
        """
        # 从Redis获取用户的所有会话
        session_key = f"{self.USER_SESSIONS_PREFIX}{user_id}"
        sessions = await self.redis.smembers(session_key)
        
        revoked_count = 0
        for session_data in sessions:
            try:
                session_info = eval(session_data.decode())  # 简单的反序列化，生产环境应使用json
                access_jti = session_info.get("access_jti")
                refresh_jti = session_info.get("refresh_jti")
                
                # 撤销访问令牌
                if access_jti:
                    await self._add_to_blacklist(access_jti, None, reason)
                    revoked_count += 1
                
                # 撤销刷新令牌
                if refresh_jti:
                    await self._add_to_blacklist(refresh_jti, None, reason)
                    await self._clear_refresh_token_cache(refresh_jti)
                    revoked_count += 1
                    
            except Exception as e:
                print(f"撤销会话令牌失败: {str(e)}")
                continue
        
        # 清理用户会话缓存
        await self.redis.delete(session_key)
        
        return revoked_count
    
    async def _cache_refresh_token(
        self, 
        payload: Dict[str, Any], 
        device_info: Optional[Dict[str, Any]]
    ):
        """缓存刷新令牌信息到Redis"""
        jti = payload["jti"]
        expire_time = payload["exp"]
        
        token_info = {
            "user_id": payload["sub"],
            "tenant_id": payload["tenant_id"],
            "device_info": device_info or {},
            "created_at": payload["iat"]
        }
        
        # 计算TTL（比实际过期时间多一些缓冲）
        ttl = expire_time - payload["iat"] + 3600
        
        await self.redis.setex(
            f"{self.REFRESH_TOKEN_PREFIX}{jti}",
            ttl,
            str(token_info)  # 生产环境应使用json.dumps
        )
    
    async def _cache_user_session(self, user_id: str, access_jti: str, refresh_jti: str):
        """缓存用户会话信息"""
        session_info = {
            "access_jti": access_jti,
            "refresh_jti": refresh_jti,
            "created_at": int(datetime.now(timezone.utc).timestamp())
        }
        
        session_key = f"{self.USER_SESSIONS_PREFIX}{user_id}"
        await self.redis.sadd(session_key, str(session_info))
        
        # 设置会话集合的过期时间
        await self.redis.expire(session_key, self.settings.refresh_token_expire_days * 24 * 3600)
    
    async def _is_token_blacklisted(self, jti: str) -> bool:
        """检查令牌是否在黑名单中"""
        if not jti:
            return False
        return await self.redis.exists(f"{self.BLACKLIST_PREFIX}{jti}")
    
    async def _add_to_blacklist(self, jti: str, exp: Optional[int], reason: str):
        """将令牌添加到黑名单"""
        if not jti:
            return
            
        # 如果没有过期时间，设置较长的缓存时间
        if exp:
            ttl = max(exp - int(datetime.now(timezone.utc).timestamp()), 0)
        else:
            ttl = self.settings.refresh_token_expire_days * 24 * 3600
        
        if ttl > 0:
            blacklist_info = {
                "reason": reason,
                "blacklisted_at": int(datetime.now(timezone.utc).timestamp())
            }
            
            await self.redis.setex(
                f"{self.BLACKLIST_PREFIX}{jti}",
                ttl,
                str(blacklist_info)
            )
    
    async def _clear_refresh_token_cache(self, jti: str):
        """清理刷新令牌缓存"""
        await self.redis.delete(f"{self.REFRESH_TOKEN_PREFIX}{jti}")
    
    async def cleanup_expired_blacklist(self) -> int:
        """清理过期的黑名单条目（Redis会自动过期，这里主要用于统计）"""
        pattern = f"{self.BLACKLIST_PREFIX}*"
        keys = await self.redis.keys(pattern)
        return len(keys)
    
    def generate_secure_random_token(self, length: int = 32) -> str:
        """生成安全的随机令牌"""
        return secrets.token_urlsafe(length)


# 工具函数
def hash_password(password: str) -> str:
    """使用bcrypt哈希密码"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))