# 安全与权限管理文档

## 1. 安全架构概述

### 1.1 安全设计原则
- **纵深防御**: 多层安全机制保护系统
- **最小权限原则**: 用户和服务只获得必需的最小权限
- **零信任架构**: 不信任任何内部或外部连接
- **数据分类保护**: 根据数据敏感度实施不同级别的保护
- **审计跟踪**: 所有安全相关操作都有完整的审计记录

### 1.2 安全威胁模型
```
外部威胁:
├── DDoS攻击
├── SQL注入
├── XSS攻击
├── CSRF攻击
├── API滥用
└── 数据泄露

内部威胁:
├── 权限滥用
├── 数据越权访问
├── 恶意内部人员
└── 误操作

系统威胁:
├── 配置错误
├── 软件漏洞
├── 依赖组件安全问题
└── 基础设施安全问题
```

### 1.3 安全架构层次
```
┌─────────────────────────────────────┐
│           应用层安全                 │
│  RBAC | JWT认证 | API限流           │
├─────────────────────────────────────┤
│           网络层安全                 │
│  WAF | DDoS防护 | VPN             │
├─────────────────────────────────────┤
│           数据层安全                 │
│  加密 | 备份 | 访问控制            │
├─────────────────────────────────────┤
│         基础设施安全                 │
│  容器安全 | 主机安全 | 监控         │
└─────────────────────────────────────┘
```

## 2. 身份认证系统

### 2.1 JWT认证机制
```python
# auth/jwt_manager.py
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import secrets
import base64

class JWTManager:
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire = timedelta(hours=1)
        self.refresh_token_expire = timedelta(days=7)
    
    def create_access_token(self, user_data: Dict[str, Any]) -> str:
        """创建访问令牌"""
        to_encode = user_data.copy()
        expire = datetime.utcnow() + self.access_token_expire
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access",
            "jti": secrets.token_hex(16),  # JWT ID
        })
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, user_id: str, tenant_id: str) -> str:
        """创建刷新令牌"""
        to_encode = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "type": "refresh",
            "exp": datetime.utcnow() + self.refresh_token_expire,
            "iat": datetime.utcnow(),
            "jti": secrets.token_hex(16),
        }
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """验证令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # 验证令牌类型
            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="无效的令牌类型"
                )
            
            # 验证过期时间
            if datetime.utcnow() > datetime.fromtimestamp(payload.get("exp", 0)):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="令牌已过期"
                )
            
            return payload
            
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的令牌"
            )
    
    def refresh_access_token(self, refresh_token: str) -> str:
        """使用刷新令牌获取新的访问令牌"""
        payload = self.verify_token(refresh_token, "refresh")
        
        # 从数据库获取最新用户信息
        user_data = self.get_user_data(payload["user_id"], payload["tenant_id"])
        
        return self.create_access_token(user_data)

# 密码哈希管理
class PasswordManager:
    @staticmethod
    def hash_password(password: str) -> tuple[str, str]:
        """哈希密码并返回哈希值和盐"""
        salt = secrets.token_hex(32)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode(),
            iterations=100000,
        )
        hashed = base64.b64encode(kdf.derive(password.encode())).decode()
        return hashed, salt
    
    @staticmethod
    def verify_password(password: str, hashed: str, salt: str) -> bool:
        """验证密码"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode(),
            iterations=100000,
        )
        try:
            kdf.verify(password.encode(), base64.b64decode(hashed))
            return True
        except:
            return False
```

### 2.2 多因素认证(MFA)
```python
# auth/mfa.py
import pyotp
import qrcode
from io import BytesIO
import base64
from typing import Optional

class MFAManager:
    def __init__(self):
        self.issuer_name = "Lyss AI Platform"
    
    def generate_totp_secret(self, user_email: str) -> tuple[str, str]:
        """生成TOTP密钥和二维码"""
        secret = pyotp.random_base32()
        
        # 生成TOTP URI
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user_email,
            issuer_name=self.issuer_name
        )
        
        # 生成二维码
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return secret, qr_code_base64
    
    def verify_totp(self, secret: str, token: str) -> bool:
        """验证TOTP令牌"""
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=1)
    
    def generate_backup_codes(self, count: int = 10) -> list[str]:
        """生成备用恢复代码"""
        return [secrets.token_hex(8) for _ in range(count)]

# SMS/邮箱验证码
class VerificationCodeManager:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.code_expire = 300  # 5分钟
    
    def send_sms_code(self, phone: str) -> str:
        """发送SMS验证码"""
        code = f"{secrets.randbelow(900000) + 100000:06d}"
        
        # 存储验证码到Redis
        self.redis.setex(f"sms_code:{phone}", self.code_expire, code)
        
        # 调用SMS服务发送
        # self.sms_service.send(phone, f"您的验证码是: {code}")
        
        return code
    
    def verify_sms_code(self, phone: str, code: str) -> bool:
        """验证SMS验证码"""
        stored_code = self.redis.get(f"sms_code:{phone}")
        if stored_code and stored_code.decode() == code:
            self.redis.delete(f"sms_code:{phone}")
            return True
        return False
```

### 2.3 OAuth2集成
```python
# auth/oauth2.py
from authlib.integrations.fastapi_oauth2 import AuthorizationServer
from authlib.oauth2.rfc6749 import grants
from fastapi import FastAPI
import secrets

class OAuth2Provider:
    def __init__(self, app: FastAPI):
        self.app = app
        self.authorization_server = AuthorizationServer()
        
        # 注册授权类型
        self.authorization_server.register_grant(grants.AuthorizationCodeGrant)
        self.authorization_server.register_grant(grants.RefreshTokenGrant)
        self.authorization_server.register_grant(grants.ClientCredentialsGrant)
        
        # 初始化授权服务器
        self.authorization_server.init_app(app)
    
    def create_oauth_client(self, client_name: str, redirect_uris: list[str]) -> dict:
        """创建OAuth2客户端"""
        client_id = secrets.token_hex(16)
        client_secret = secrets.token_hex(32)
        
        # 存储客户端信息到数据库
        client_data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "client_name": client_name,
            "redirect_uris": redirect_uris,
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "scope": "read write",
        }
        
        return client_data
```

## 3. 角色与权限管理(RBAC)

### 3.1 RBAC模型设计
```python
# rbac/models.py
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel

class Permission(str, Enum):
    # 用户管理权限
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    
    # 对话管理权限
    CONVERSATION_CREATE = "conversation:create"
    CONVERSATION_READ = "conversation:read"
    CONVERSATION_UPDATE = "conversation:update"
    CONVERSATION_DELETE = "conversation:delete"
    
    # AI模型管理权限
    MODEL_CREATE = "model:create"
    MODEL_READ = "model:read"
    MODEL_UPDATE = "model:update"
    MODEL_DELETE = "model:delete"
    MODEL_USE = "model:use"
    
    # 系统管理权限
    SYSTEM_CONFIG = "system:config"
    SYSTEM_MONITOR = "system:monitor"
    SYSTEM_AUDIT = "system:audit"
    
    # 租户管理权限
    TENANT_CREATE = "tenant:create"
    TENANT_READ = "tenant:read"
    TENANT_UPDATE = "tenant:update"
    TENANT_DELETE = "tenant:delete"
    TENANT_MANAGE = "tenant:manage"

class Role(BaseModel):
    role_id: str
    role_name: str
    description: Optional[str]
    permissions: List[Permission]
    is_system_role: bool = False
    created_at: str
    updated_at: str

class User(BaseModel):
    user_id: str
    email: str
    username: str
    tenant_id: str
    roles: List[str]
    status: str
    created_at: str
    last_login_at: Optional[str]

# 预定义角色
SYSTEM_ROLES = {
    "super_admin": Role(
        role_id="super_admin",
        role_name="超级管理员",
        description="系统最高权限管理员",
        permissions=list(Permission),
        is_system_role=True,
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z"
    ),
    
    "tenant_admin": Role(
        role_id="tenant_admin",
        role_name="租户管理员",
        description="租户内的管理员",
        permissions=[
            Permission.USER_CREATE,
            Permission.USER_READ,
            Permission.USER_UPDATE,
            Permission.USER_DELETE,
            Permission.CONVERSATION_READ,
            Permission.MODEL_CREATE,
            Permission.MODEL_READ,
            Permission.MODEL_UPDATE,
            Permission.MODEL_DELETE,
            Permission.MODEL_USE,
            Permission.TENANT_READ,
            Permission.TENANT_UPDATE,
        ],
        is_system_role=True,
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z"
    ),
    
    "end_user": Role(
        role_id="end_user",
        role_name="终端用户",
        description="普通用户",
        permissions=[
            Permission.CONVERSATION_CREATE,
            Permission.CONVERSATION_READ,
            Permission.CONVERSATION_UPDATE,
            Permission.CONVERSATION_DELETE,
            Permission.MODEL_USE,
        ],
        is_system_role=True,
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z"
    )
}
```

### 3.2 权限检查器
```python
# rbac/checker.py
from typing import List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

class PermissionChecker:
    def __init__(self, jwt_manager, user_service, role_service):
        self.jwt_manager = jwt_manager
        self.user_service = user_service
        self.role_service = role_service
        self.security = HTTPBearer()
    
    def require_permissions(self, required_permissions: List[Permission]):
        """权限检查装饰器"""
        def permission_checker(
            credentials: HTTPAuthorizationCredentials = Depends(self.security)
        ):
            # 验证JWT令牌
            payload = self.jwt_manager.verify_token(credentials.credentials)
            
            # 获取用户信息
            user = self.user_service.get_user(payload["user_id"])
            if not user or user.status != "active":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="用户账户无效或已被禁用"
                )
            
            # 获取用户权限
            user_permissions = self.get_user_permissions(user)
            
            # 检查权限
            for required_permission in required_permissions:
                if required_permission not in user_permissions:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"缺少权限: {required_permission.value}"
                    )
            
            return user
        
        return permission_checker
    
    def get_user_permissions(self, user: User) -> List[Permission]:
        """获取用户的所有权限"""
        permissions = set()
        
        for role_id in user.roles:
            role = self.role_service.get_role(role_id)
            if role:
                permissions.update(role.permissions)
        
        return list(permissions)
    
    def require_tenant_access(self, target_tenant_id: Optional[str] = None):
        """租户访问权限检查"""
        def tenant_checker(
            credentials: HTTPAuthorizationCredentials = Depends(self.security)
        ):
            payload = self.jwt_manager.verify_token(credentials.credentials)
            user_tenant_id = payload.get("tenant_id")
            
            if target_tenant_id and user_tenant_id != target_tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权访问其他租户的资源"
                )
            
            return payload
        
        return tenant_checker

# 权限装饰器使用示例
from fastapi import APIRouter, Depends

router = APIRouter()
permission_checker = PermissionChecker(jwt_manager, user_service, role_service)

@router.post("/users")
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(
        permission_checker.require_permissions([Permission.USER_CREATE])
    )
):
    """创建用户 - 需要用户创建权限"""
    return await user_service.create_user(user_data)

@router.get("/admin/audit-logs")
async def get_audit_logs(
    current_user: User = Depends(
        permission_checker.require_permissions([Permission.SYSTEM_AUDIT])
    )
):
    """获取审计日志 - 需要系统审计权限"""
    return await audit_service.get_logs()
```

### 3.3 动态权限控制
```python
# rbac/dynamic_permissions.py
from typing import Dict, Any, Callable
from abc import ABC, abstractmethod

class ResourceAccessControl(ABC):
    """资源访问控制基类"""
    
    @abstractmethod
    def can_access(self, user: User, resource: Dict[str, Any], action: str) -> bool:
        pass

class ConversationAccessControl(ResourceAccessControl):
    """对话访问控制"""
    
    def can_access(self, user: User, conversation: Dict[str, Any], action: str) -> bool:
        # 用户只能访问自己的对话
        if action in ["read", "update", "delete"]:
            return conversation.get("user_id") == user.user_id
        
        # 创建对话需要在同一租户内
        if action == "create":
            return conversation.get("tenant_id") == user.tenant_id
        
        return False

class ModelAccessControl(ResourceAccessControl):
    """AI模型访问控制"""
    
    def can_access(self, user: User, model: Dict[str, Any], action: str) -> bool:
        # 检查模型是否属于用户的租户
        if model.get("tenant_id") != user.tenant_id:
            return False
        
        # 检查模型状态
        if model.get("status") != "active":
            return False
        
        # 检查用户的模型使用配额
        if action == "use":
            return self.check_usage_quota(user, model)
        
        return True
    
    def check_usage_quota(self, user: User, model: Dict[str, Any]) -> bool:
        """检查使用配额"""
        # 实现配额检查逻辑
        return True

class DynamicPermissionManager:
    """动态权限管理器"""
    
    def __init__(self):
        self.access_controls: Dict[str, ResourceAccessControl] = {
            "conversation": ConversationAccessControl(),
            "model": ModelAccessControl(),
        }
    
    def check_resource_access(
        self, 
        user: User, 
        resource_type: str, 
        resource: Dict[str, Any], 
        action: str
    ) -> bool:
        """检查资源访问权限"""
        access_control = self.access_controls.get(resource_type)
        if not access_control:
            return False
        
        return access_control.can_access(user, resource, action)
    
    def register_access_control(self, resource_type: str, access_control: ResourceAccessControl):
        """注册新的访问控制器"""
        self.access_controls[resource_type] = access_control
```

## 4. 数据安全

### 4.1 数据加密
```python
# security/encryption.py
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import base64
import secrets
import os

class DataEncryption:
    """数据加密工具类"""
    
    def __init__(self, master_key: str):
        self.master_key = master_key.encode()
    
    def generate_key(self, salt: bytes = None) -> bytes:
        """生成加密密钥"""
        if salt is None:
            salt = secrets.token_bytes(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(self.master_key)
    
    def encrypt_sensitive_data(self, data: str, salt: bytes = None) -> tuple[str, str]:
        """加密敏感数据"""
        if salt is None:
            salt = secrets.token_bytes(16)
        
        key = self.generate_key(salt)
        fernet = Fernet(base64.urlsafe_b64encode(key))
        
        encrypted_data = fernet.encrypt(data.encode())
        
        return (
            base64.b64encode(encrypted_data).decode(),
            base64.b64encode(salt).decode()
        )
    
    def decrypt_sensitive_data(self, encrypted_data: str, salt: str) -> str:
        """解密敏感数据"""
        salt_bytes = base64.b64decode(salt.encode())
        key = self.generate_key(salt_bytes)
        fernet = Fernet(base64.urlsafe_b64encode(key))
        
        encrypted_bytes = base64.b64decode(encrypted_data.encode())
        decrypted_data = fernet.decrypt(encrypted_bytes)
        
        return decrypted_data.decode()

# API密钥加密存储
class APIKeyManager:
    """API密钥管理器"""
    
    def __init__(self, encryption: DataEncryption):
        self.encryption = encryption
    
    def store_api_key(self, provider_name: str, api_key: str, tenant_id: str) -> dict:
        """安全存储API密钥"""
        encrypted_key, salt = self.encryption.encrypt_sensitive_data(api_key)
        
        credential_data = {
            "provider_name": provider_name,
            "encrypted_api_key": encrypted_key,
            "salt": salt,
            "tenant_id": tenant_id,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        return credential_data
    
    def retrieve_api_key(self, credential_data: dict) -> str:
        """安全检索API密钥"""
        encrypted_key = credential_data["encrypted_api_key"]
        salt = credential_data["salt"]
        
        return self.encryption.decrypt_sensitive_data(encrypted_key, salt)
```

### 4.2 数据脱敏
```python
# security/data_masking.py
import re
import hashlib
from typing import Any, Dict

class DataMasking:
    """数据脱敏工具"""
    
    @staticmethod
    def mask_email(email: str) -> str:
        """邮箱脱敏"""
        if '@' in email:
            username, domain = email.split('@', 1)
            if len(username) <= 2:
                masked_username = '*' * len(username)
            else:
                masked_username = username[0] + '*' * (len(username) - 2) + username[-1]
            return f"{masked_username}@{domain}"
        return email
    
    @staticmethod
    def mask_phone(phone: str) -> str:
        """手机号脱敏"""
        if len(phone) >= 7:
            return phone[:3] + '*' * (len(phone) - 6) + phone[-3:]
        return '*' * len(phone)
    
    @staticmethod
    def mask_api_key(api_key: str) -> str:
        """API密钥脱敏"""
        if len(api_key) <= 8:
            return '*' * len(api_key)
        return api_key[:4] + '*' * (len(api_key) - 8) + api_key[-4:]
    
    @staticmethod
    def mask_sensitive_content(content: str) -> str:
        """脱敏敏感内容"""
        # 脱敏身份证号
        content = re.sub(r'\d{15}|\d{17}[\dXx]', lambda m: m.group()[:6] + '*' * 8 + m.group()[-4:], content)
        
        # 脱敏银行卡号
        content = re.sub(r'\d{16,19}', lambda m: m.group()[:4] + '*' * (len(m.group()) - 8) + m.group()[-4:], content)
        
        # 脱敏IP地址
        content = re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '***.***.***.**', content)
        
        return content
    
    def mask_dict(self, data: Dict[str, Any], sensitive_fields: list[str]) -> Dict[str, Any]:
        """递归脱敏字典数据"""
        if not isinstance(data, dict):
            return data
        
        masked_data = {}
        for key, value in data.items():
            if key.lower() in [field.lower() for field in sensitive_fields]:
                if 'email' in key.lower():
                    masked_data[key] = self.mask_email(str(value))
                elif 'phone' in key.lower():
                    masked_data[key] = self.mask_phone(str(value))
                elif 'api_key' in key.lower() or 'token' in key.lower():
                    masked_data[key] = self.mask_api_key(str(value))
                else:
                    masked_data[key] = '*' * len(str(value))
            elif isinstance(value, dict):
                masked_data[key] = self.mask_dict(value, sensitive_fields)
            elif isinstance(value, list):
                masked_data[key] = [
                    self.mask_dict(item, sensitive_fields) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                masked_data[key] = value
        
        return masked_data
```

### 4.3 数据分类与标记
```python
# security/data_classification.py
from enum import Enum
from typing import Dict, Any, List

class DataClassification(str, Enum):
    """数据分类级别"""
    PUBLIC = "public"           # 公开数据
    INTERNAL = "internal"       # 内部数据
    CONFIDENTIAL = "confidential"  # 机密数据
    RESTRICTED = "restricted"   # 限制数据

class DataLabel:
    """数据标签"""
    def __init__(self, classification: DataClassification, tags: List[str] = None):
        self.classification = classification
        self.tags = tags or []
        self.retention_period = self._get_retention_period()
        self.encryption_required = self._requires_encryption()
    
    def _get_retention_period(self) -> int:
        """获取数据保留期（天）"""
        retention_map = {
            DataClassification.PUBLIC: 365 * 5,      # 5年
            DataClassification.INTERNAL: 365 * 3,    # 3年
            DataClassification.CONFIDENTIAL: 365 * 7, # 7年
            DataClassification.RESTRICTED: 365 * 10,  # 10年
        }
        return retention_map.get(self.classification, 365)
    
    def _requires_encryption(self) -> bool:
        """是否需要加密"""
        return self.classification in [
            DataClassification.CONFIDENTIAL,
            DataClassification.RESTRICTED
        ]

class DataClassifier:
    """数据分类器"""
    
    def __init__(self):
        # 预定义字段分类规则
        self.field_classification_rules = {
            # 限制级数据
            "password": DataClassification.RESTRICTED,
            "api_key": DataClassification.RESTRICTED,
            "private_key": DataClassification.RESTRICTED,
            "secret": DataClassification.RESTRICTED,
            
            # 机密数据
            "email": DataClassification.CONFIDENTIAL,
            "phone": DataClassification.CONFIDENTIAL,
            "address": DataClassification.CONFIDENTIAL,
            "payment_info": DataClassification.CONFIDENTIAL,
            
            # 内部数据
            "user_id": DataClassification.INTERNAL,
            "tenant_id": DataClassification.INTERNAL,
            "session_id": DataClassification.INTERNAL,
            
            # 公开数据
            "username": DataClassification.PUBLIC,
            "display_name": DataClassification.PUBLIC,
        }
    
    def classify_field(self, field_name: str, field_value: Any) -> DataLabel:
        """分类单个字段"""
        field_lower = field_name.lower()
        
        # 检查预定义规则
        for pattern, classification in self.field_classification_rules.items():
            if pattern in field_lower:
                return DataLabel(classification, [pattern])
        
        # 基于值内容的分类
        if isinstance(field_value, str):
            if self._is_email(field_value):
                return DataLabel(DataClassification.CONFIDENTIAL, ["email"])
            elif self._is_phone(field_value):
                return DataLabel(DataClassification.CONFIDENTIAL, ["phone"])
            elif self._is_api_key(field_value):
                return DataLabel(DataClassification.RESTRICTED, ["api_key"])
        
        # 默认为内部数据
        return DataLabel(DataClassification.INTERNAL)
    
    def classify_record(self, record: Dict[str, Any]) -> Dict[str, DataLabel]:
        """分类整个记录"""
        classification_result = {}
        
        for field_name, field_value in record.items():
            classification_result[field_name] = self.classify_field(field_name, field_value)
        
        return classification_result
    
    def _is_email(self, value: str) -> bool:
        """检查是否为邮箱"""
        return '@' in value and '.' in value.split('@')[-1]
    
    def _is_phone(self, value: str) -> bool:
        """检查是否为手机号"""
        return re.match(r'^\+?[\d\s\-\(\)]{10,}$', value) is not None
    
    def _is_api_key(self, value: str) -> bool:
        """检查是否为API密钥"""
        return (len(value) > 20 and 
                any(c.isalpha() for c in value) and 
                any(c.isdigit() for c in value))
```

## 5. 安全审计

### 5.1 审计日志系统
```python
# security/audit.py
from typing import Dict, Any, Optional
from datetime import datetime
import json
import hashlib

class AuditLogger:
    """安全审计日志记录器"""
    
    def __init__(self, audit_service):
        self.audit_service = audit_service
    
    def log_authentication(self, user_id: str, tenant_id: str, 
                          action: str, result: str, details: Dict[str, Any] = None):
        """记录认证相关事件"""
        self._log_event(
            event_type="authentication",
            event_category="auth",
            user_id=user_id,
            tenant_id=tenant_id,
            action=action,
            result=result,
            details=details
        )
    
    def log_authorization(self, user_id: str, tenant_id: str,
                         resource_type: str, resource_id: str,
                         action: str, result: str, details: Dict[str, Any] = None):
        """记录授权相关事件"""
        self._log_event(
            event_type="authorization",
            event_category="auth",
            user_id=user_id,
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            result=result,
            details=details
        )
    
    def log_data_access(self, user_id: str, tenant_id: str,
                       resource_type: str, resource_id: str,
                       action: str, result: str, details: Dict[str, Any] = None):
        """记录数据访问事件"""
        self._log_event(
            event_type="data_access",
            event_category="data",
            user_id=user_id,
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            result=result,
            details=details
        )
    
    def log_admin_operation(self, user_id: str, tenant_id: str,
                           operation: str, target: str,
                           result: str, details: Dict[str, Any] = None):
        """记录管理员操作"""
        self._log_event(
            event_type="admin_operation",
            event_category="admin",
            user_id=user_id,
            tenant_id=tenant_id,
            action=operation,
            result=result,
            details={
                "target": target,
                **(details or {})
            }
        )
    
    def log_security_event(self, event_type: str, severity: str,
                          description: str, details: Dict[str, Any] = None):
        """记录安全事件"""
        self._log_event(
            event_type=event_type,
            event_category="security",
            action="security_alert",
            result=severity,
            details={
                "description": description,
                "severity": severity,
                **(details or {})
            }
        )
    
    def _log_event(self, **kwargs):
        """内部日志记录方法"""
        log_entry = {
            "log_id": self._generate_log_id(),
            "timestamp": datetime.utcnow().isoformat(),
            "event_id": self._generate_event_id(kwargs),
            **kwargs
        }
        
        # 添加完整性校验
        log_entry["checksum"] = self._calculate_checksum(log_entry)
        
        # 异步写入审计日志
        self.audit_service.write_log(log_entry)
    
    def _generate_log_id(self) -> str:
        """生成日志ID"""
        return f"audit_{int(datetime.utcnow().timestamp() * 1000000)}"
    
    def _generate_event_id(self, event_data: Dict[str, Any]) -> str:
        """生成事件ID"""
        content = json.dumps(event_data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _calculate_checksum(self, log_entry: Dict[str, Any]) -> str:
        """计算日志完整性校验和"""
        # 排除checksum字段本身
        data = {k: v for k, v in log_entry.items() if k != "checksum"}
        content = json.dumps(data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

# 审计装饰器
def audit_action(action: str, resource_type: str = None):
    """审计装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 获取当前用户信息
            current_user = kwargs.get('current_user')
            request = kwargs.get('request')
            
            start_time = datetime.utcnow()
            result = "success"
            error_details = None
            
            try:
                response = await func(*args, **kwargs)
                return response
            except Exception as e:
                result = "failure"
                error_details = {"error": str(e), "type": type(e).__name__}
                raise
            finally:
                # 记录审计日志
                if current_user:
                    duration = (datetime.utcnow() - start_time).total_seconds() * 1000
                    
                    audit_logger.log_data_access(
                        user_id=current_user.user_id,
                        tenant_id=current_user.tenant_id,
                        resource_type=resource_type or func.__name__,
                        resource_id=kwargs.get('resource_id', 'unknown'),
                        action=action,
                        result=result,
                        details={
                            "function": func.__name__,
                            "duration_ms": duration,
                            "ip_address": getattr(request, 'client', {}).get('host') if request else None,
                            "user_agent": getattr(request, 'headers', {}).get('user-agent') if request else None,
                            **(error_details or {})
                        }
                    )
        
        return wrapper
    return decorator
```

### 5.2 安全监控
```python
# security/monitoring.py
from typing import Dict, Any, List
import time
from collections import defaultdict, deque
import asyncio

class SecurityMonitor:
    """安全监控系统"""
    
    def __init__(self, redis_client, alert_service):
        self.redis = redis_client
        self.alert_service = alert_service
        
        # 监控规则配置
        self.rules = {
            "failed_login_attempts": {
                "threshold": 5,
                "window": 300,  # 5分钟
                "action": "lock_account"
            },
            "api_rate_limit": {
                "threshold": 1000,
                "window": 60,   # 1分钟
                "action": "rate_limit"
            },
            "suspicious_ip": {
                "threshold": 3,
                "window": 3600, # 1小时
                "action": "block_ip"
            },
            "privilege_escalation": {
                "threshold": 1,
                "window": 0,    # 立即
                "action": "security_alert"
            }
        }
    
    async def monitor_failed_login(self, user_id: str, ip_address: str):
        """监控登录失败"""
        key = f"failed_login:{user_id}"
        current_count = await self.redis.incr(key)
        
        if current_count == 1:
            await self.redis.expire(key, self.rules["failed_login_attempts"]["window"])
        
        if current_count >= self.rules["failed_login_attempts"]["threshold"]:
            await self._trigger_action("failed_login_attempts", {
                "user_id": user_id,
                "ip_address": ip_address,
                "attempt_count": current_count
            })
    
    async def monitor_api_usage(self, user_id: str, endpoint: str):
        """监控API使用频率"""
        key = f"api_usage:{user_id}:{endpoint}"
        current_count = await self.redis.incr(key)
        
        if current_count == 1:
            await self.redis.expire(key, self.rules["api_rate_limit"]["window"])
        
        if current_count >= self.rules["api_rate_limit"]["threshold"]:
            await self._trigger_action("api_rate_limit", {
                "user_id": user_id,
                "endpoint": endpoint,
                "request_count": current_count
            })
    
    async def monitor_ip_activity(self, ip_address: str, user_count: int):
        """监控IP地址活动"""
        if user_count >= self.rules["suspicious_ip"]["threshold"]:
            await self._trigger_action("suspicious_ip", {
                "ip_address": ip_address,
                "user_count": user_count
            })
    
    async def monitor_privilege_escalation(self, user_id: str, 
                                         old_roles: List[str], 
                                         new_roles: List[str]):
        """监控权限提升"""
        # 检查是否有权限提升
        privilege_increase = any(
            role in new_roles and role not in old_roles 
            for role in ["super_admin", "tenant_admin"]
        )
        
        if privilege_increase:
            await self._trigger_action("privilege_escalation", {
                "user_id": user_id,
                "old_roles": old_roles,
                "new_roles": new_roles
            })
    
    async def _trigger_action(self, rule_name: str, details: Dict[str, Any]):
        """触发安全动作"""
        rule = self.rules[rule_name]
        action = rule["action"]
        
        if action == "lock_account":
            await self._lock_user_account(details["user_id"])
        elif action == "rate_limit":
            await self._apply_rate_limit(details["user_id"], details["endpoint"])
        elif action == "block_ip":
            await self._block_ip_address(details["ip_address"])
        elif action == "security_alert":
            await self._send_security_alert(rule_name, details)
    
    async def _lock_user_account(self, user_id: str):
        """锁定用户账户"""
        # 实现账户锁定逻辑
        await self.redis.setex(f"locked_account:{user_id}", 3600, "1")
        
        await self.alert_service.send_alert({
            "type": "account_locked",
            "user_id": user_id,
            "timestamp": time.time()
        })
    
    async def _apply_rate_limit(self, user_id: str, endpoint: str):
        """应用速率限制"""
        # 实现速率限制逻辑
        await self.redis.setex(f"rate_limited:{user_id}:{endpoint}", 300, "1")
    
    async def _block_ip_address(self, ip_address: str):
        """阻止IP地址"""
        # 实现IP阻止逻辑
        await self.redis.setex(f"blocked_ip:{ip_address}", 3600, "1")
        
        await self.alert_service.send_alert({
            "type": "ip_blocked",
            "ip_address": ip_address,
            "timestamp": time.time()
        })
    
    async def _send_security_alert(self, rule_name: str, details: Dict[str, Any]):
        """发送安全警报"""
        await self.alert_service.send_alert({
            "type": "security_alert",
            "rule": rule_name,
            "details": details,
            "timestamp": time.time(),
            "severity": "high"
        })

# 实时威胁检测
class ThreatDetector:
    """威胁检测器"""
    
    def __init__(self):
        self.patterns = {
            "sql_injection": [
                r"union\s+select",
                r"'.*or.*'.*'",
                r"drop\s+table",
                r"insert\s+into",
                r"delete\s+from"
            ],
            "xss_attack": [
                r"<script.*?>",
                r"javascript:",
                r"onload\s*=",
                r"onerror\s*="
            ],
            "command_injection": [
                r";\s*rm\s+",
                r";\s*cat\s+",
                r";\s*ls\s+",
                r"\|\s*nc\s+"
            ]
        }
    
    def detect_threats(self, request_data: Dict[str, Any]) -> List[str]:
        """检测请求中的威胁"""
        threats = []
        
        # 检查所有字符串值
        for key, value in self._flatten_dict(request_data).items():
            if isinstance(value, str):
                for threat_type, patterns in self.patterns.items():
                    for pattern in patterns:
                        if re.search(pattern, value, re.IGNORECASE):
                            threats.append(f"{threat_type}:{pattern}")
        
        return threats
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '') -> Dict[str, Any]:
        """递归展平字典"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key).items())
            else:
                items.append((new_key, v))
        return dict(items)
```

这个安全与权限管理文档提供了完整的安全架构设计，包括身份认证、权限控制、数据加密、审计监控等核心安全功能的详细实现方案。