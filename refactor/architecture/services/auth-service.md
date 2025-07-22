# Lyss Auth Service - 认证授权服务

## 📋 服务概述

**lyss-auth-service** 是平台的认证授权核心服务，负责用户身份验证、JWT令牌管理、权限控制和会话管理。基于现有的80%完成度基础上，进一步完善OAuth2/OIDC联邦认证、RBAC权限体系和多租户安全隔离机制。

---

## 🎯 核心功能

### **1. 身份认证管理**
- **本地认证**: 用户名密码登录，支持密码复杂度策略
- **联邦认证**: OAuth2/OIDC集成（Google、GitHub、企业SSO）
- **多因素认证**: TOTP、SMS验证码等二次验证
- **生物识别**: 支持WebAuthn/FIDO2标准

### **2. JWT令牌管理**
- **令牌签发**: 基于RSA/ECDSA的安全JWT令牌
- **令牌刷新**: 无缝的令牌刷新机制
- **令牌撤销**: 实时的令牌黑名单管理
- **令牌验证**: 高性能的令牌验证和解析

### **3. 权限控制系统**
- **RBAC模型**: 基于角色的访问控制
- **资源权限**: 细粒度的资源和操作权限
- **动态权限**: 支持运行时权限变更
- **权限继承**: 租户、角色、用户的权限继承链

### **4. 会话管理**
- **Redis会话**: 分布式会话存储和管理
- **会话策略**: 单点登录、并发会话控制
- **会话安全**: 会话固定、劫持等安全防护
- **活跃监控**: 用户活动监控和异常检测

### **5. 多租户安全**
- **租户隔离**: 完全的租户数据隔离
- **跨租户访问**: 安全的跨租户权限管理
- **租户策略**: 每租户的安全策略配置
- **审计日志**: 完整的认证授权审计

---

## 🏗️ 技术架构

### **架构设计图**
```
┌─────────────────────────────────────────────────────────┐
│                    API Gateway                          │
│              (认证中间件/JWT验证)                         │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│                Auth Service                             │
│  ┌─────────────────┬─────────────────┬─────────────────┐ │
│  │  Auth Manager   │ Permission Mgr  │ Session Manager │ │
│  │   ·用户认证      │   ·RBAC权限     │   ·会话管理      │ │
│  │   ·JWT管理      │   ·资源控制     │   ·Redis缓存     │ │
│  │   ·OAuth2集成   │   ·动态权限     │   ·SSO支持      │ │
│  └─────────────────┼─────────────────┼─────────────────┘ │
└──────────────────┬─┴─────────────────┴─┬─────────────────┘
                   │                     │
    ┌──────────────▼──────────────┐ ┌───▼──────────────┐
    │      User Database          │ │   Redis Cache    │
    │  ·用户基本信息               │ │  ·JWT黑名单      │
    │  ·密码哈希                  │ │  ·会话数据       │
    │  ·角色权限                  │ │  ·权限缓存       │
    │  ·登录历史                  │ │  ·验证码缓存     │
    └─────────────────────────────┘ └─────────────────┘
```

### **核心模块架构**

```python
# 服务架构概览
lyss-auth-service/
├── main.py                     # FastAPI应用入口
├── app/
│   ├── __init__.py
│   ├── core/                   # 核心配置
│   │   ├── config.py          # 服务配置
│   │   ├── security.py        # 安全配置
│   │   ├── jwt.py            # JWT配置
│   │   └── database.py        # 数据库配置
│   ├── auth/                   # 认证模块
│   │   ├── __init__.py
│   │   ├── manager.py         # 认证管理器
│   │   ├── local.py           # 本地认证
│   │   ├── oauth2.py          # OAuth2认证
│   │   ├── mfa.py             # 多因素认证
│   │   └── webauthn.py        # WebAuthn认证
│   ├── jwt/                    # JWT令牌模块
│   │   ├── __init__.py
│   │   ├── manager.py         # JWT管理器
│   │   ├── generator.py       # 令牌生成器
│   │   ├── validator.py       # 令牌验证器
│   │   └── blacklist.py       # 令牌黑名单
│   ├── permissions/            # 权限模块
│   │   ├── __init__.py
│   │   ├── rbac.py           # RBAC实现
│   │   ├── manager.py         # 权限管理器
│   │   ├── decorators.py      # 权限装饰器
│   │   └── policies.py        # 权限策略
│   ├── sessions/               # 会话模块
│   │   ├── __init__.py
│   │   ├── manager.py         # 会话管理器
│   │   ├── store.py           # 会话存储
│   │   └── security.py        # 会话安全
│   ├── models/                 # 数据模型
│   │   ├── __init__.py
│   │   ├── user.py           # 用户模型
│   │   ├── role.py           # 角色模型
│   │   ├── permission.py      # 权限模型
│   │   └── session.py         # 会话模型
│   ├── api/                   # API接口
│   │   ├── __init__.py
│   │   ├── v1/               # V1版本API
│   │   │   ├── auth.py       # 认证API
│   │   │   ├── users.py      # 用户API
│   │   │   ├── roles.py      # 角色API
│   │   │   └── sessions.py   # 会话API
│   │   └── middleware.py      # 中间件
│   ├── services/              # 业务服务
│   │   ├── __init__.py
│   │   ├── auth_service.py   # 认证服务
│   │   ├── user_service.py   # 用户服务
│   │   └── permission_service.py # 权限服务
│   └── utils/                 # 工具类
│       ├── __init__.py
│       ├── password.py       # 密码工具
│       ├── crypto.py         # 加密工具
│       └── validators.py     # 验证工具
├── config/                    # 配置文件
│   ├── oauth2_providers.yaml  # OAuth2提供商配置
│   └── security_policies.yaml # 安全策略配置
├── tests/                     # 测试
│   ├── test_auth.py
│   ├── test_jwt.py
│   ├── test_permissions.py
│   └── test_sessions.py
├── requirements.txt           # 依赖
├── Dockerfile                # Docker配置
└── README.md                 # 服务文档
```

---

## 💻 核心实现

### **1. 认证管理器**

```python
# app/auth/manager.py
from typing import Optional, Dict, Any, List
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from ..core.security import pwd_context
from ..jwt.manager import jwt_manager
from ..sessions.manager import session_manager
from ..models.user import User, UserCreate, LoginRequest
from ..services.user_service import user_service
from ..utils.validators import validate_password_strength

logger = logging.getLogger(__name__)

class AuthenticationManager:
    """认证管理器 - 核心认证逻辑"""
    
    def __init__(self):
        self.max_failed_attempts = 5
        self.lockout_duration = timedelta(minutes=30)
        
    async def authenticate_user(
        self, 
        login_request: LoginRequest,
        tenant_id: str,
        user_agent: str = None,
        ip_address: str = None
    ) -> Dict[str, Any]:
        """用户认证主流程"""
        try:
            # 1. 基础验证
            if not login_request.email or not login_request.password:
                raise ValueError("邮箱和密码不能为空")
            
            # 2. 查找用户
            user = await user_service.get_user_by_email(
                login_request.email, tenant_id
            )
            
            if not user:
                # 记录认证失败
                await self._record_auth_failure(
                    login_request.email, tenant_id, "用户不存在", ip_address
                )
                raise ValueError("用户名或密码错误")
            
            # 3. 检查账户状态
            await self._check_account_status(user)
            
            # 4. 检查账户锁定
            await self._check_account_lockout(user.id, ip_address)
            
            # 5. 验证密码
            if not self._verify_password(login_request.password, user.password_hash):
                # 记录失败尝试
                await self._record_failed_attempt(user.id, ip_address)
                raise ValueError("用户名或密码错误")
            
            # 6. 检查多因素认证
            if user.mfa_enabled:
                mfa_token = await self._handle_mfa_challenge(user, login_request)
                if not mfa_token:
                    return {
                        "success": False,
                        "requires_mfa": True,
                        "challenge_id": await self._create_mfa_challenge(user.id)
                    }
            
            # 7. 生成JWT令牌
            tokens = await jwt_manager.create_tokens(user, tenant_id)
            
            # 8. 创建会话
            session_id = await session_manager.create_session(
                user.id, tenant_id, user_agent, ip_address
            )
            
            # 9. 记录成功登录
            await self._record_successful_login(
                user.id, session_id, ip_address, user_agent
            )
            
            # 10. 清除失败尝试记录
            await self._clear_failed_attempts(user.id)
            
            return {
                "success": True,
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
                "token_type": "Bearer",
                "expires_in": tokens["expires_in"],
                "session_id": session_id,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "roles": await self._get_user_roles(user.id),
                    "permissions": await self._get_user_permissions(user.id)
                }
            }
            
        except Exception as e:
            logger.error(f"用户认证失败: {e}")
            raise
    
    async def refresh_access_token(
        self, 
        refresh_token: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """刷新访问令牌"""
        try:
            # 1. 验证刷新令牌
            payload = await jwt_manager.verify_refresh_token(refresh_token)
            
            user_id = payload.get("sub")
            session_id = payload.get("session_id")
            
            # 2. 检查会话有效性
            session = await session_manager.get_session(session_id)
            if not session or not session.is_active:
                raise ValueError("会话已过期")
            
            # 3. 获取用户信息
            user = await user_service.get_user_by_id(user_id)
            if not user or not user.is_active:
                raise ValueError("用户账户异常")
            
            # 4. 生成新的访问令牌
            new_tokens = await jwt_manager.refresh_tokens(
                refresh_token, user, tenant_id
            )
            
            # 5. 更新会话活跃时间
            await session_manager.update_session_activity(session_id)
            
            return {
                "success": True,
                "access_token": new_tokens["access_token"],
                "refresh_token": new_tokens["refresh_token"],
                "token_type": "Bearer",
                "expires_in": new_tokens["expires_in"]
            }
            
        except Exception as e:
            logger.error(f"令牌刷新失败: {e}")
            raise ValueError("令牌刷新失败")
    
    async def logout_user(
        self, 
        access_token: str,
        session_id: str = None
    ) -> bool:
        """用户登出"""
        try:
            # 1. 将访问令牌加入黑名单
            await jwt_manager.blacklist_token(access_token)
            
            # 2. 销毁会话
            if session_id:
                await session_manager.destroy_session(session_id)
            
            # 3. 记录登出日志
            payload = await jwt_manager.decode_token(access_token, verify=False)
            user_id = payload.get("sub")
            
            if user_id:
                await self._record_logout(user_id, session_id)
            
            return True
            
        except Exception as e:
            logger.error(f"用户登出失败: {e}")
            return False
    
    async def change_password(
        self,
        user_id: str,
        old_password: str,
        new_password: str,
        tenant_id: str
    ) -> bool:
        """修改密码"""
        try:
            # 1. 获取用户信息
            user = await user_service.get_user_by_id(user_id)
            if not user:
                raise ValueError("用户不存在")
            
            # 2. 验证旧密码
            if not self._verify_password(old_password, user.password_hash):
                raise ValueError("原密码错误")
            
            # 3. 验证新密码强度
            password_validation = validate_password_strength(new_password)
            if not password_validation["valid"]:
                raise ValueError(f"密码强度不足: {password_validation['message']}")
            
            # 4. 检查密码历史
            await self._check_password_history(user_id, new_password)
            
            # 5. 更新密码
            new_password_hash = self._hash_password(new_password)
            success = await user_service.update_password(
                user_id, new_password_hash, tenant_id
            )
            
            if success:
                # 6. 记录密码变更
                await self._record_password_change(user_id)
                
                # 7. 失效所有现有会话（可选）
                await self._invalidate_user_sessions(user_id)
            
            return success
            
        except Exception as e:
            logger.error(f"密码修改失败: {e}")
            raise
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """验证密码"""
        return pwd_context.verify(password, password_hash)
    
    def _hash_password(self, password: str) -> str:
        """哈希密码"""
        return pwd_context.hash(password)
    
    async def _check_account_status(self, user: User):
        """检查账户状态"""
        if not user.is_active:
            raise ValueError("账户已被禁用")
        
        if user.is_locked:
            raise ValueError("账户已被锁定")
        
        if user.email_verified_at is None:
            raise ValueError("邮箱尚未验证")
        
        # 检查账户过期
        if user.expires_at and user.expires_at < datetime.utcnow():
            raise ValueError("账户已过期")
    
    async def _check_account_lockout(self, user_id: str, ip_address: str):
        """检查账户锁定状态"""
        # 检查用户级锁定
        failed_attempts = await self._get_failed_attempts(user_id)
        if failed_attempts >= self.max_failed_attempts:
            last_attempt = await self._get_last_failed_attempt(user_id)
            if last_attempt and (datetime.utcnow() - last_attempt) < self.lockout_duration:
                raise ValueError(f"账户已锁定，请在{self.lockout_duration.total_seconds()/60}分钟后重试")
        
        # 检查IP级锁定
        if ip_address:
            ip_failed_attempts = await self._get_ip_failed_attempts(ip_address)
            if ip_failed_attempts >= self.max_failed_attempts * 3:  # IP锁定阈值更高
                raise ValueError("该IP地址尝试次数过多，请稍后重试")
    
    async def _handle_mfa_challenge(self, user: User, login_request: LoginRequest):
        """处理多因素认证挑战"""
        if not login_request.mfa_code:
            return None
        
        # 验证TOTP码
        if user.mfa_method == "totp":
            return await self._verify_totp(user.mfa_secret, login_request.mfa_code)
        
        # 验证SMS码
        elif user.mfa_method == "sms":
            return await self._verify_sms_code(user.phone, login_request.mfa_code)
        
        return False
    
    async def _record_successful_login(
        self, 
        user_id: str, 
        session_id: str,
        ip_address: str,
        user_agent: str
    ):
        """记录成功登录"""
        # 实现登录记录逻辑
        pass
    
    async def _record_failed_attempt(self, user_id: str, ip_address: str):
        """记录失败尝试"""
        # 实现失败尝试记录逻辑
        pass

# 全局认证管理器实例
auth_manager = AuthenticationManager()
```

### **2. JWT管理器**

```python
# app/jwt/manager.py
from typing import Dict, Any, Optional, List
import jwt
import uuid
from datetime import datetime, timedelta
from ..core.config import settings
from ..models.user import User
from ..utils.crypto import get_private_key, get_public_key

class JWTManager:
    """JWT令牌管理器"""
    
    def __init__(self):
        self.algorithm = "RS256"
        self.access_token_expire = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        self.refresh_token_expire = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        self.private_key = get_private_key()
        self.public_key = get_public_key()
    
    async def create_tokens(
        self, 
        user: User, 
        tenant_id: str,
        session_id: str = None
    ) -> Dict[str, Any]:
        """创建JWT令牌对"""
        try:
            now = datetime.utcnow()
            jti = str(uuid.uuid4())  # JWT ID，用于令牌撤销
            
            # 访问令牌载荷
            access_payload = {
                "sub": str(user.id),               # 用户ID
                "tenant_id": tenant_id,            # 租户ID  
                "email": user.email,               # 用户邮箱
                "name": user.name,                 # 用户名称
                "roles": await self._get_user_roles(user.id),  # 用户角色
                "permissions": await self._get_user_permissions(user.id),  # 用户权限
                "session_id": session_id,          # 会话ID
                "iat": now,                        # 签发时间
                "exp": now + self.access_token_expire,  # 过期时间
                "jti": jti,                        # JWT ID
                "type": "access"                   # 令牌类型
            }
            
            # 刷新令牌载荷（信息较少）
            refresh_payload = {
                "sub": str(user.id),
                "tenant_id": tenant_id,
                "session_id": session_id,
                "iat": now,
                "exp": now + self.refresh_token_expire,
                "jti": f"refresh_{jti}",
                "type": "refresh"
            }
            
            # 生成令牌
            access_token = jwt.encode(
                access_payload, 
                self.private_key, 
                algorithm=self.algorithm
            )
            
            refresh_token = jwt.encode(
                refresh_payload,
                self.private_key,
                algorithm=self.algorithm
            )
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "Bearer",
                "expires_in": int(self.access_token_expire.total_seconds())
            }
            
        except Exception as e:
            logger.error(f"JWT令牌创建失败: {e}")
            raise
    
    async def verify_access_token(self, token: str) -> Dict[str, Any]:
        """验证访问令牌"""
        try:
            # 1. 解码令牌
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.algorithm]
            )
            
            # 2. 检查令牌类型
            if payload.get("type") != "access":
                raise ValueError("令牌类型错误")
            
            # 3. 检查黑名单
            jti = payload.get("jti")
            if jti and await self._is_token_blacklisted(jti):
                raise ValueError("令牌已被撤销")
            
            # 4. 检查会话状态
            session_id = payload.get("session_id")
            if session_id:
                session = await session_manager.get_session(session_id)
                if not session or not session.is_active:
                    raise ValueError("会话已过期")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise ValueError("令牌已过期")
        except jwt.InvalidTokenError:
            raise ValueError("无效令牌")
        except Exception as e:
            logger.error(f"令牌验证失败: {e}")
            raise ValueError("令牌验证失败")
    
    async def verify_refresh_token(self, token: str) -> Dict[str, Any]:
        """验证刷新令牌"""
        try:
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.algorithm]
            )
            
            if payload.get("type") != "refresh":
                raise ValueError("令牌类型错误")
            
            # 检查黑名单
            jti = payload.get("jti")
            if jti and await self._is_token_blacklisted(jti):
                raise ValueError("令牌已被撤销")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise ValueError("刷新令牌已过期")
        except jwt.InvalidTokenError:
            raise ValueError("无效刷新令牌")
        except Exception as e:
            logger.error(f"刷新令牌验证失败: {e}")
            raise ValueError("刷新令牌验证失败")
    
    async def refresh_tokens(
        self,
        refresh_token: str,
        user: User,
        tenant_id: str
    ) -> Dict[str, Any]:
        """刷新令牌"""
        try:
            # 1. 验证刷新令牌
            refresh_payload = await self.verify_refresh_token(refresh_token)
            
            # 2. 将旧的刷新令牌加入黑名单
            old_jti = refresh_payload.get("jti")
            if old_jti:
                await self._blacklist_token(old_jti)
            
            # 3. 创建新的令牌对
            session_id = refresh_payload.get("session_id")
            new_tokens = await self.create_tokens(user, tenant_id, session_id)
            
            return new_tokens
            
        except Exception as e:
            logger.error(f"令牌刷新失败: {e}")
            raise
    
    async def blacklist_token(self, token: str):
        """将令牌加入黑名单"""
        try:
            # 解码获取JTI（不验证过期时间）
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False}
            )
            
            jti = payload.get("jti")
            exp = payload.get("exp")
            
            if jti and exp:
                # 计算令牌剩余有效期
                expire_time = datetime.fromtimestamp(exp)
                ttl = max(0, int((expire_time - datetime.utcnow()).total_seconds()))
                
                # 加入Redis黑名单
                await self._add_to_blacklist(jti, ttl)
                
        except Exception as e:
            logger.error(f"令牌黑名单添加失败: {e}")
    
    async def decode_token(self, token: str, verify: bool = True) -> Dict[str, Any]:
        """解码令牌（用于调试和日志）"""
        try:
            options = {"verify_exp": verify, "verify_signature": verify}
            
            payload = jwt.decode(
                token,
                self.public_key if verify else None,
                algorithms=[self.algorithm] if verify else None,
                options=options
            )
            
            return payload
            
        except Exception as e:
            logger.error(f"令牌解码失败: {e}")
            return {}
    
    async def _get_user_roles(self, user_id: str) -> List[str]:
        """获取用户角色列表"""
        # 实现用户角色查询逻辑
        from ..services.permission_service import permission_service
        return await permission_service.get_user_roles(user_id)
    
    async def _get_user_permissions(self, user_id: str) -> List[str]:
        """获取用户权限列表"""
        # 实现用户权限查询逻辑
        from ..services.permission_service import permission_service
        return await permission_service.get_user_permissions(user_id)
    
    async def _is_token_blacklisted(self, jti: str) -> bool:
        """检查令牌是否在黑名单中"""
        from ..core.redis import redis_client
        
        result = await redis_client.get(f"blacklist:{jti}")
        return result is not None
    
    async def _add_to_blacklist(self, jti: str, ttl: int):
        """添加令牌到黑名单"""
        from ..core.redis import redis_client
        
        await redis_client.setex(f"blacklist:{jti}", ttl, "1")

# 全局JWT管理器实例
jwt_manager = JWTManager()
```

### **3. RBAC权限系统**

```python
# app/permissions/rbac.py
from typing import Dict, List, Optional, Set
from enum import Enum
import logging
from ..models.permission import Permission, Role, RolePermission
from ..models.user import UserRole
from ..core.redis import redis_client

logger = logging.getLogger(__name__)

class ResourceType(Enum):
    """资源类型枚举"""
    USER = "user"
    TENANT = "tenant"
    PROVIDER = "provider"
    CHANNEL = "channel"
    CONVERSATION = "conversation"
    MODEL = "model"
    SYSTEM = "system"

class PermissionAction(Enum):
    """权限动作枚举"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    MANAGE = "manage"
    EXECUTE = "execute"

class RBACManager:
    """RBAC权限管理器"""
    
    def __init__(self):
        self.cache_prefix = "rbac"
        self.cache_ttl = 3600  # 1小时缓存
    
    async def check_permission(
        self,
        user_id: str,
        resource_type: str,
        action: str,
        tenant_id: str = None,
        resource_id: str = None
    ) -> bool:
        """检查用户权限"""
        try:
            # 1. 从缓存获取用户权限
            user_permissions = await self._get_cached_user_permissions(user_id)
            
            if not user_permissions:
                # 2. 从数据库加载权限
                user_permissions = await self._load_user_permissions(user_id)
                await self._cache_user_permissions(user_id, user_permissions)
            
            # 3. 构建权限标识符
            permission_key = self._build_permission_key(
                resource_type, action, tenant_id, resource_id
            )
            
            # 4. 检查直接权限
            if permission_key in user_permissions:
                return True
            
            # 5. 检查通配符权限
            wildcard_permissions = [
                f"{resource_type}:*",           # 资源类型通配
                f"{resource_type}:{action}:*",  # 租户通配
                "*:*:*"                        # 超级管理员
            ]
            
            for wildcard in wildcard_permissions:
                if wildcard in user_permissions:
                    return True
            
            # 6. 检查租户级权限
            if tenant_id:
                tenant_permission = f"{resource_type}:{action}:{tenant_id}"
                if tenant_permission in user_permissions:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"权限检查失败: {e}")
            return False
    
    async def get_user_roles(self, user_id: str, tenant_id: str = None) -> List[Dict]:
        """获取用户角色"""
        try:
            cache_key = f"{self.cache_prefix}:roles:{user_id}"
            if tenant_id:
                cache_key += f":{tenant_id}"
            
            # 尝试从缓存获取
            cached_roles = await redis_client.get(cache_key)
            if cached_roles:
                return json.loads(cached_roles)
            
            # 从数据库查询
            query = """
                SELECT r.id, r.name, r.description, r.scope, ur.tenant_id
                FROM roles r
                JOIN user_roles ur ON r.id = ur.role_id
                WHERE ur.user_id = %s
            """
            
            params = [user_id]
            if tenant_id:
                query += " AND (ur.tenant_id = %s OR r.scope = 'global')"
                params.append(tenant_id)
            
            # 执行查询（这里需要实际的数据库连接）
            roles = await self._execute_query(query, params)
            
            # 缓存结果
            await redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(roles, default=str)
            )
            
            return roles
            
        except Exception as e:
            logger.error(f"获取用户角色失败: {e}")
            return []
    
    async def assign_role_to_user(
        self,
        user_id: str,
        role_id: str,
        tenant_id: str = None,
        assigned_by: str = None
    ) -> bool:
        """为用户分配角色"""
        try:
            # 1. 检查角色是否存在
            role = await self._get_role_by_id(role_id)
            if not role:
                raise ValueError(f"角色 {role_id} 不存在")
            
            # 2. 检查用户是否已有该角色
            existing_assignment = await self._check_user_role_assignment(
                user_id, role_id, tenant_id
            )
            
            if existing_assignment:
                return True  # 已经分配过
            
            # 3. 创建角色分配记录
            assignment_data = {
                "user_id": user_id,
                "role_id": role_id,
                "tenant_id": tenant_id,
                "assigned_by": assigned_by,
                "assigned_at": datetime.utcnow()
            }
            
            success = await self._create_user_role_assignment(assignment_data)
            
            if success:
                # 4. 清除用户权限缓存
                await self._clear_user_permission_cache(user_id)
                
                logger.info(f"成功为用户 {user_id} 分配角色 {role_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"角色分配失败: {e}")
            raise
    
    async def revoke_role_from_user(
        self,
        user_id: str,
        role_id: str,
        tenant_id: str = None
    ) -> bool:
        """撤销用户角色"""
        try:
            # 删除角色分配
            success = await self._delete_user_role_assignment(
                user_id, role_id, tenant_id
            )
            
            if success:
                # 清除权限缓存
                await self._clear_user_permission_cache(user_id)
                
                logger.info(f"成功撤销用户 {user_id} 的角色 {role_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"角色撤销失败: {e}")
            return False
    
    async def create_role(
        self,
        role_data: Dict,
        created_by: str = None
    ) -> Optional[str]:
        """创建新角色"""
        try:
            # 1. 验证角色数据
            if not role_data.get("name"):
                raise ValueError("角色名称不能为空")
            
            # 2. 检查角色名称唯一性
            existing_role = await self._get_role_by_name(
                role_data["name"], role_data.get("tenant_id")
            )
            
            if existing_role:
                raise ValueError(f"角色名称 {role_data['name']} 已存在")
            
            # 3. 创建角色
            role_id = await self._create_role_record(role_data, created_by)
            
            # 4. 分配权限（如果提供）
            permissions = role_data.get("permissions", [])
            if permissions:
                await self._assign_permissions_to_role(role_id, permissions)
            
            logger.info(f"成功创建角色: {role_data['name']} (ID: {role_id})")
            return role_id
            
        except Exception as e:
            logger.error(f"角色创建失败: {e}")
            raise
    
    async def get_available_permissions(
        self,
        resource_type: str = None,
        tenant_id: str = None
    ) -> List[Dict]:
        """获取可用权限列表"""
        try:
            cache_key = f"{self.cache_prefix}:permissions"
            if resource_type:
                cache_key += f":{resource_type}"
            if tenant_id:
                cache_key += f":{tenant_id}"
            
            # 尝试从缓存获取
            cached_permissions = await redis_client.get(cache_key)
            if cached_permissions:
                return json.loads(cached_permissions)
            
            # 构建查询
            query = """
                SELECT id, name, resource_type, action, description, scope
                FROM permissions
                WHERE 1=1
            """
            
            params = []
            if resource_type:
                query += " AND resource_type = %s"
                params.append(resource_type)
            
            # 执行查询
            permissions = await self._execute_query(query, params)
            
            # 缓存结果
            await redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(permissions, default=str)
            )
            
            return permissions
            
        except Exception as e:
            logger.error(f"获取权限列表失败: {e}")
            return []
    
    def _build_permission_key(
        self,
        resource_type: str,
        action: str,
        tenant_id: str = None,
        resource_id: str = None
    ) -> str:
        """构建权限标识符"""
        key_parts = [resource_type, action]
        
        if tenant_id:
            key_parts.append(tenant_id)
        
        if resource_id:
            key_parts.append(resource_id)
        
        return ":".join(key_parts)
    
    async def _load_user_permissions(self, user_id: str) -> Set[str]:
        """加载用户所有权限"""
        try:
            query = """
                SELECT DISTINCT p.resource_type, p.action, ur.tenant_id, p.scope
                FROM permissions p
                JOIN role_permissions rp ON p.id = rp.permission_id
                JOIN roles r ON rp.role_id = r.id
                JOIN user_roles ur ON r.id = ur.role_id
                WHERE ur.user_id = %s
            """
            
            permission_records = await self._execute_query(query, [user_id])
            
            permissions = set()
            for record in permission_records:
                # 构建权限键
                permission_key = self._build_permission_key(
                    record["resource_type"],
                    record["action"],
                    record.get("tenant_id"),
                    None  # 暂不支持资源级权限
                )
                permissions.add(permission_key)
            
            return permissions
            
        except Exception as e:
            logger.error(f"加载用户权限失败: {e}")
            return set()
    
    async def _cache_user_permissions(self, user_id: str, permissions: Set[str]):
        """缓存用户权限"""
        cache_key = f"{self.cache_prefix}:user_permissions:{user_id}"
        await redis_client.setex(
            cache_key,
            self.cache_ttl,
            json.dumps(list(permissions))
        )
    
    async def _clear_user_permission_cache(self, user_id: str):
        """清除用户权限缓存"""
        cache_keys = [
            f"{self.cache_prefix}:user_permissions:{user_id}",
            f"{self.cache_prefix}:roles:{user_id}*"
        ]
        
        for key in cache_keys:
            if "*" in key:
                # 删除匹配的键
                keys_to_delete = await redis_client.keys(key)
                if keys_to_delete:
                    await redis_client.delete(*keys_to_delete)
            else:
                await redis_client.delete(key)

# 全局RBAC管理器实例
rbac_manager = RBACManager()
```

---

## 🌐 API接口设计

### **1. 认证API**

```python
# app/api/v1/auth.py
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from ...models.auth import LoginRequest, LoginResponse, RefreshRequest
from ...services.auth_service import auth_service
from ...core.rate_limit import rate_limit

router = APIRouter(prefix="/auth", tags=["认证"])
security = HTTPBearer(auto_error=False)

@router.post("/login", response_model=LoginResponse)
@rate_limit(max_calls=5, time_window=300)  # 5次/5分钟
async def login(
    request: Request,
    login_data: LoginRequest
):
    """用户登录"""
    try:
        # 获取客户端信息
        client_ip = request.client.host
        user_agent = request.headers.get("user-agent", "")
        
        # 执行认证
        result = await auth_service.authenticate_user(
            login_data=login_data,
            tenant_id=login_data.tenant_id,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        if not result["success"]:
            if result.get("requires_mfa"):
                return LoginResponse(
                    success=False,
                    requires_mfa=True,
                    challenge_id=result["challenge_id"],
                    message="需要多因素认证"
                )
            else:
                raise HTTPException(
                    status_code=401,
                    detail=result.get("message", "认证失败")
                )
        
        return LoginResponse(**result)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"登录处理失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")

@router.post("/refresh")
async def refresh_token(
    refresh_data: RefreshRequest
):
    """刷新访问令牌"""
    try:
        result = await auth_service.refresh_access_token(
            refresh_token=refresh_data.refresh_token,
            tenant_id=refresh_data.tenant_id
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"令牌刷新失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")

@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session_id: Optional[str] = None
):
    """用户登出"""
    if not credentials:
        raise HTTPException(status_code=401, detail="未提供认证令牌")
    
    try:
        success = await auth_service.logout_user(
            access_token=credentials.credentials,
            session_id=session_id
        )
        
        if success:
            return {"message": "登出成功"}
        else:
            raise HTTPException(status_code=400, detail="登出失败")
            
    except Exception as e:
        logger.error(f"登出处理失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")

@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """修改密码"""
    try:
        success = await auth_service.change_password(
            user_id=current_user["sub"],
            old_password=password_data.old_password,
            new_password=password_data.new_password,
            tenant_id=current_user["tenant_id"]
        )
        
        if success:
            return {"message": "密码修改成功"}
        else:
            raise HTTPException(status_code=400, detail="密码修改失败")
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"密码修改失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")

@router.get("/me")
async def get_current_user_info(
    current_user: dict = Depends(get_current_user)
):
    """获取当前用户信息"""
    return {
        "id": current_user["sub"],
        "email": current_user["email"],
        "name": current_user["name"],
        "tenant_id": current_user["tenant_id"],
        "roles": current_user.get("roles", []),
        "permissions": current_user.get("permissions", [])
    }

@router.post("/verify-token")
async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """验证令牌有效性"""
    if not credentials:
        raise HTTPException(status_code=401, detail="未提供认证令牌")
    
    try:
        payload = await jwt_manager.verify_access_token(credentials.credentials)
        
        return {
            "valid": True,
            "user_id": payload["sub"],
            "tenant_id": payload["tenant_id"],
            "expires_at": payload["exp"]
        }
        
    except ValueError:
        return {"valid": False}
    except Exception as e:
        logger.error(f"令牌验证失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")
```

### **2. OAuth2集成API**

```python
# app/api/v1/oauth2.py
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from ...services.oauth2_service import oauth2_service

router = APIRouter(prefix="/oauth2", tags=["OAuth2认证"])

@router.get("/providers")
async def list_oauth_providers():
    """获取可用的OAuth2提供商"""
    providers = await oauth2_service.get_available_providers()
    return {"providers": providers}

@router.get("/authorize/{provider}")
async def oauth_authorize(
    provider: str,
    request: Request,
    tenant_id: str = None,
    redirect_uri: str = None
):
    """OAuth2授权跳转"""
    try:
        # 生成状态码防CSRF
        state = await oauth2_service.generate_state(
            tenant_id=tenant_id,
            redirect_uri=redirect_uri,
            ip_address=request.client.host
        )
        
        # 构建授权URL
        auth_url = await oauth2_service.build_authorization_url(
            provider=provider,
            state=state,
            redirect_uri=redirect_uri
        )
        
        return RedirectResponse(url=auth_url)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"OAuth2授权失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")

@router.get("/callback/{provider}")
async def oauth_callback(
    provider: str,
    request: Request,
    code: str = None,
    state: str = None,
    error: str = None
):
    """OAuth2回调处理"""
    try:
        if error:
            raise ValueError(f"OAuth2授权失败: {error}")
        
        if not code or not state:
            raise ValueError("缺少必要的回调参数")
        
        # 验证状态码
        state_data = await oauth2_service.verify_state(state)
        if not state_data:
            raise ValueError("无效的状态码")
        
        # 获取访问令牌
        token_data = await oauth2_service.exchange_code_for_token(
            provider=provider,
            code=code,
            state_data=state_data
        )
        
        # 获取用户信息
        user_info = await oauth2_service.get_user_info(
            provider=provider,
            access_token=token_data["access_token"]
        )
        
        # 执行OAuth2登录
        login_result = await oauth2_service.oauth_login(
            provider=provider,
            user_info=user_info,
            tenant_id=state_data.get("tenant_id"),
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent", "")
        )
        
        # 重定向到前端
        redirect_uri = state_data.get("redirect_uri", "/dashboard")
        if login_result["success"]:
            # 成功登录，在URL中包含token
            return RedirectResponse(
                url=f"{redirect_uri}?access_token={login_result['access_token']}"
                    f"&refresh_token={login_result['refresh_token']}"
            )
        else:
            return RedirectResponse(
                url=f"{redirect_uri}?error=oauth_login_failed"
            )
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"OAuth2回调处理失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")

@router.post("/bind/{provider}")
async def bind_oauth_account(
    provider: str,
    bind_data: Dict,
    current_user: dict = Depends(get_current_user)
):
    """绑定OAuth2账户"""
    try:
        success = await oauth2_service.bind_oauth_account(
            user_id=current_user["sub"],
            provider=provider,
            oauth_data=bind_data,
            tenant_id=current_user["tenant_id"]
        )
        
        if success:
            return {"message": f"成功绑定{provider}账户"}
        else:
            raise HTTPException(status_code=400, detail="账户绑定失败")
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"OAuth2账户绑定失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")
```

---

## 🗄️ 数据模型

### **数据库表设计**

```sql
-- 用户基本信息表（从user-service同步）
CREATE TABLE auth_users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    email_verified_at TIMESTAMP,
    password_hash VARCHAR(255),
    name VARCHAR(100),
    phone VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    is_locked BOOLEAN DEFAULT FALSE,
    mfa_enabled BOOLEAN DEFAULT FALSE,
    mfa_method VARCHAR(20),
    mfa_secret TEXT,
    last_login_at TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_email (email),
    INDEX idx_active_status (is_active, is_locked)
);

-- 角色表
CREATE TABLE auth_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    scope VARCHAR(20) DEFAULT 'tenant', -- 'global', 'tenant'
    tenant_id UUID,
    is_system BOOLEAN DEFAULT FALSE,
    created_by UUID,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE INDEX idx_role_name_tenant (name, tenant_id),
    INDEX idx_scope (scope)
);

-- 权限表
CREATE TABLE auth_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    description TEXT,
    scope VARCHAR(20) DEFAULT 'tenant',
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE INDEX idx_permission_unique (resource_type, action, scope),
    INDEX idx_resource_type (resource_type)
);

-- 角色权限关联表
CREATE TABLE auth_role_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id UUID NOT NULL,
    permission_id UUID NOT NULL,
    granted_by UUID,
    granted_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE INDEX idx_role_permission (role_id, permission_id),
    FOREIGN KEY (role_id) REFERENCES auth_roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES auth_permissions(id) ON DELETE CASCADE
);

-- 用户角色关联表
CREATE TABLE auth_user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    role_id UUID NOT NULL,
    tenant_id UUID,
    assigned_by UUID,
    assigned_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    
    UNIQUE INDEX idx_user_role_tenant (user_id, role_id, tenant_id),
    FOREIGN KEY (role_id) REFERENCES auth_roles(id) ON DELETE CASCADE,
    INDEX idx_user_tenant (user_id, tenant_id)
);

-- 登录会话表
CREATE TABLE auth_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    ip_address INET,
    user_agent TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    last_activity TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_user_active (user_id, is_active),
    INDEX idx_session_token (session_token),
    INDEX idx_expires_at (expires_at)
);

-- 登录历史表
CREATE TABLE auth_login_history (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID,
    email VARCHAR(255),
    tenant_id UUID,
    login_method VARCHAR(20), -- 'local', 'oauth2', 'sso'
    provider VARCHAR(50),     -- OAuth2提供商
    ip_address INET,
    user_agent TEXT,
    status VARCHAR(20),       -- 'success', 'failed', 'blocked'
    failure_reason TEXT,
    session_id UUID,
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_user_date (user_id, created_at),
    INDEX idx_status_date (status, created_at),
    INDEX idx_tenant_date (tenant_id, created_at)
);

-- 失败尝试记录表
CREATE TABLE auth_failed_attempts (
    id BIGSERIAL PRIMARY KEY,
    identifier VARCHAR(255) NOT NULL, -- 可以是用户ID或IP地址
    identifier_type VARCHAR(20) NOT NULL, -- 'user', 'ip'
    attempt_count INTEGER DEFAULT 1,
    last_attempt TIMESTAMP DEFAULT NOW(),
    locked_until TIMESTAMP,
    
    UNIQUE INDEX idx_identifier_type (identifier, identifier_type),
    INDEX idx_last_attempt (last_attempt)
);

-- OAuth2账户绑定表
CREATE TABLE auth_oauth_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    provider VARCHAR(50) NOT NULL,
    provider_user_id VARCHAR(255) NOT NULL,
    provider_username VARCHAR(255),
    provider_email VARCHAR(255),
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMP,
    profile_data JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE INDEX idx_provider_user (provider, provider_user_id),
    INDEX idx_user_provider (user_id, provider)
);

-- 密码历史表（用于防止重复密码）
CREATE TABLE auth_password_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_user_created (user_id, created_at),
    FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE
);
```

---

## 🔧 配置文件

### **OAuth2提供商配置**

```yaml
# config/oauth2_providers.yaml
providers:
  google:
    name: "Google"
    client_id: "${GOOGLE_CLIENT_ID}"
    client_secret: "${GOOGLE_CLIENT_SECRET}"
    authorization_url: "https://accounts.google.com/o/oauth2/auth"
    token_url: "https://oauth2.googleapis.com/token"
    user_info_url: "https://www.googleapis.com/oauth2/v2/userinfo"
    scopes: ["openid", "email", "profile"]
    redirect_uri: "${BASE_URL}/api/v1/oauth2/callback/google"
    
  github:
    name: "GitHub"
    client_id: "${GITHUB_CLIENT_ID}"
    client_secret: "${GITHUB_CLIENT_SECRET}"
    authorization_url: "https://github.com/login/oauth/authorize"
    token_url: "https://github.com/login/oauth/access_token"
    user_info_url: "https://api.github.com/user"
    scopes: ["user:email"]
    redirect_uri: "${BASE_URL}/api/v1/oauth2/callback/github"
    
  microsoft:
    name: "Microsoft"
    client_id: "${MICROSOFT_CLIENT_ID}"
    client_secret: "${MICROSOFT_CLIENT_SECRET}"
    authorization_url: "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    token_url: "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    user_info_url: "https://graph.microsoft.com/v1.0/me"
    scopes: ["openid", "email", "profile"]
    redirect_uri: "${BASE_URL}/api/v1/oauth2/callback/microsoft"
```

### **安全策略配置**

```yaml
# config/security_policies.yaml
password_policy:
  min_length: 8
  max_length: 128
  require_uppercase: true
  require_lowercase: true
  require_numbers: true
  require_symbols: true
  forbidden_patterns:
    - "password"
    - "123456"
    - "qwerty"
  history_count: 5  # 记住最近5个密码

session_policy:
  max_concurrent_sessions: 5
  session_timeout_minutes: 480  # 8小时
  idle_timeout_minutes: 60     # 1小时无活动自动登出
  refresh_activity_threshold: 300  # 5分钟内活动刷新会话

lockout_policy:
  max_failed_attempts: 5
  lockout_duration_minutes: 30
  ip_lockout_threshold: 15
  ip_lockout_duration_minutes: 60

jwt_policy:
  access_token_expire_minutes: 15
  refresh_token_expire_days: 30
  algorithm: "RS256"
  issuer: "lyss-auth-service"
  
mfa_policy:
  totp_window: 1           # TOTP时间窗口
  sms_expire_minutes: 5    # SMS验证码过期时间
  backup_codes_count: 10   # 备份码数量

audit_policy:
  log_successful_logins: true
  log_failed_attempts: true
  log_password_changes: true
  log_permission_changes: true
  retention_days: 90
```

---

## 🚀 部署配置

### **Docker配置**

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建非root用户
RUN useradd -m -u 1001 authuser && chown -R authuser:authuser /app
USER authuser

# 暴露端口
EXPOSE 8001

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### **环境变量配置**

```bash
# .env
# 数据库配置
DATABASE_URL=postgresql://lyss:lyss123@postgres:5432/lyss_auth

# Redis配置
REDIS_URL=redis://redis:6379/0

# JWT配置
JWT_SECRET_KEY=your-super-secret-jwt-key-here
JWT_PRIVATE_KEY_PATH=/app/config/keys/jwt-private.pem
JWT_PUBLIC_KEY_PATH=/app/config/keys/jwt-public.pem

# OAuth2配置
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret

MICROSOFT_CLIENT_ID=your-microsoft-client-id
MICROSOFT_CLIENT_SECRET=your-microsoft-client-secret

# 安全配置
ENCRYPTION_KEY=your-32-char-encryption-key-here
BCRYPT_ROUNDS=12

# 基础配置
BASE_URL=https://yourdomain.com
ENVIRONMENT=production
LOG_LEVEL=INFO
```

---

## 📊 监控和日志

### **监控指标**

```python
# app/utils/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time

# 认证指标
auth_requests_total = Counter(
    'auth_requests_total',
    '认证请求总数',
    ['method', 'status', 'tenant_id']
)

auth_duration_seconds = Histogram(
    'auth_duration_seconds',
    '认证处理时间',
    ['method', 'tenant_id']
)

# 会话指标
active_sessions_gauge = Gauge(
    'active_sessions',
    '活跃会话数',
    ['tenant_id']
)

# JWT指标
jwt_tokens_issued_total = Counter(
    'jwt_tokens_issued_total',
    'JWT令牌签发总数',
    ['token_type', 'tenant_id']
)

jwt_tokens_verified_total = Counter(
    'jwt_tokens_verified_total',
    'JWT令牌验证总数',
    ['status', 'tenant_id']
)

# 失败尝试指标
failed_attempts_total = Counter(
    'failed_attempts_total',
    '失败尝试总数',
    ['type', 'reason']
)

# OAuth2指标
oauth2_requests_total = Counter(
    'oauth2_requests_total',
    'OAuth2请求总数',
    ['provider', 'status']
)
```

---

## 🎯 总结

**lyss-auth-service** 在现有80%基础上进一步完善，提供了：

### **核心增强功能**
1. **OAuth2/OIDC集成** - 支持Google、GitHub、Microsoft等主流提供商
2. **完善的RBAC系统** - 细粒度权限控制和动态权限管理
3. **多因素认证** - TOTP、SMS、WebAuthn等多种MFA方式
4. **会话安全管理** - 分布式会话、并发控制、异常检测
5. **审计和监控** - 完整的认证日志和实时监控指标

### **技术特性**
1. **高安全性** - JWT RSA签名、密码策略、防爆破机制
2. **高性能** - Redis缓存、异步处理、连接池优化
3. **高可用** - 无状态设计、故障隔离、优雅降级
4. **可扩展** - 插件化OAuth2、动态权限、多租户支持

### **开发优先级**
- ⚡ **补充完善**: 基于现有80%代码基础快速完善
- 🔒 **安全关键**: 整个平台的安全基础服务
- 🎯 **用户体验**: 统一的认证和权限管理体验

该服务完善后，将为整个平台提供企业级的身份认证和权限管理能力！

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "\u8bc4\u4f30refactor\u6587\u6863\u5b8c\u5584\u7a0b\u5ea6\uff0c\u786e\u5b9a\u5f00\u53d1\u7b56\u7565", "status": "completed", "priority": "high", "id": "evaluate-docs-readiness"}, {"content": "\u8c03\u7814\u53c2\u8003\u9879\u76ee\uff1aDify\u3001One-API\u3001OpenWebUI\u67b6\u6784\u8bbe\u8ba1", "status": "completed", "priority": "high", "id": "research-reference-projects"}, {"content": "\u5efa\u7acb\u6280\u672f\u6587\u6863\u77e5\u8bc6\u5e93\uff0c\u56fa\u5316Context7\u8c03\u7814\u6210\u679c", "status": "completed", "priority": "medium", "id": "create-tech-knowledge-base"}, {"content": "\u5236\u5b9a\u5fae\u670d\u52a1\u5f00\u53d1\u987a\u5e8f\u548c\u7b56\u7565", "status": "completed", "priority": "high", "id": "plan-microservice-development"}, {"content": "\u8865\u5145lyss-provider-service\u67b6\u6784\u6587\u6863", "status": "completed", "priority": "high", "id": "create-provider-service-doc"}, {"content": "\u8865\u5145lyss-auth-service\u67b6\u6784\u6587\u6863", "status": "completed", "priority": "high", "id": "create-auth-service-doc"}, {"content": "\u8865\u5145lyss-user-service\u67b6\u6784\u6587\u6863", "status": "in_progress", "priority": "high", "id": "create-user-service-doc"}]