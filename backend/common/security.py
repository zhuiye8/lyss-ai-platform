"""
Security utilities for authentication and authorization
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from .config import get_settings

settings = get_settings()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Role(str, Enum):
    """用户角色枚举"""
    SUPER_ADMIN = "super_admin"
    TENANT_ADMIN = "tenant_admin"
    END_USER = "end_user"


class Permission(str, Enum):
    """系统权限枚举"""
    # 用户管理
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    
    # 租户管理
    TENANT_CREATE = "tenant:create"
    TENANT_READ = "tenant:read"
    TENANT_UPDATE = "tenant:update"
    TENANT_DELETE = "tenant:delete"
    
    # 对话管理
    CONVERSATION_CREATE = "conversation:create"
    CONVERSATION_READ = "conversation:read"
    CONVERSATION_UPDATE = "conversation:update"
    CONVERSATION_DELETE = "conversation:delete"
    
    # AI模型管理
    AI_MODEL_CREATE = "ai_model:create"
    AI_MODEL_READ = "ai_model:read"
    AI_MODEL_UPDATE = "ai_model:update"
    AI_MODEL_DELETE = "ai_model:delete"
    
    # AI凭证管理
    AI_CREDENTIAL_CREATE = "ai_credential:create"
    AI_CREDENTIAL_READ = "ai_credential:read"
    AI_CREDENTIAL_UPDATE = "ai_credential:update"
    AI_CREDENTIAL_DELETE = "ai_credential:delete"
    
    # API密钥管理
    API_KEY_CREATE = "api_key:create"
    API_KEY_READ = "api_key:read"
    API_KEY_UPDATE = "api_key:update"
    API_KEY_DELETE = "api_key:delete"
    
    # 系统管理
    SYSTEM_CONFIG = "system:config"
    SYSTEM_MONITORING = "system:monitoring"
    SYSTEM_AUDIT = "system:audit"


# 基于角色的权限映射
ROLE_PERMISSIONS = {
    Role.SUPER_ADMIN: [p.value for p in Permission],
    Role.TENANT_ADMIN: [
        Permission.USER_CREATE.value,
        Permission.USER_READ.value,
        Permission.USER_UPDATE.value,
        Permission.USER_DELETE.value,
        Permission.TENANT_READ.value,
        Permission.TENANT_UPDATE.value,
        Permission.CONVERSATION_READ.value,
        Permission.AI_MODEL_CREATE.value,
        Permission.AI_MODEL_READ.value,
        Permission.AI_MODEL_UPDATE.value,
        Permission.AI_MODEL_DELETE.value,
        Permission.AI_CREDENTIAL_CREATE.value,
        Permission.AI_CREDENTIAL_READ.value,
        Permission.AI_CREDENTIAL_UPDATE.value,
        Permission.AI_CREDENTIAL_DELETE.value,
        Permission.API_KEY_CREATE.value,
        Permission.API_KEY_READ.value,
        Permission.API_KEY_UPDATE.value,
        Permission.API_KEY_DELETE.value,
        Permission.SYSTEM_MONITORING.value,
        Permission.SYSTEM_AUDIT.value,
    ],
    Role.END_USER: [
        Permission.USER_READ.value,
        Permission.USER_UPDATE.value,
        Permission.CONVERSATION_CREATE.value,
        Permission.CONVERSATION_READ.value,
        Permission.CONVERSATION_UPDATE.value,
        Permission.CONVERSATION_DELETE.value,
        Permission.AI_MODEL_READ.value,
        Permission.API_KEY_CREATE.value,
        Permission.API_KEY_READ.value,
        Permission.API_KEY_UPDATE.value,
        Permission.API_KEY_DELETE.value,
    ]
}


class TokenData(BaseModel):
    """令牌载荷数据"""
    user_id: str
    tenant_id: str
    email: str
    roles: List[str]
    permissions: List[str]
    exp: datetime
    iat: datetime
    jti: str  # JWT ID，用于令牌撤销


class PasswordPolicy:
    """密码策略验证器"""
    
    @staticmethod
    def validate_password(password: str) -> tuple[bool, List[str]]:
        """验证密码是否符合策略要求"""
        errors = []
        
        if len(password) < settings.security.password_min_length:
            errors.append(f"密码长度至少需要 {settings.security.password_min_length} 个字符")
        
        if not any(c.isupper() for c in password):
            errors.append("密码必须包含至少一个大写字母")
        
        if not any(c.islower() for c in password):
            errors.append("密码必须包含至少一个小写字母")
        
        if not any(c.isdigit() for c in password):
            errors.append("密码必须包含至少一个数字")
        
        if settings.security.password_require_special:
            special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
            if not any(c in special_chars for c in password):
                errors.append("密码必须包含至少一个特殊字符")
        
        return len(errors) == 0, errors


class SecurityManager:
    """安全工具管理器"""
    
    def __init__(self):
        self.password_policy = PasswordPolicy()
        # 将权限映射暴露为实例属性，方便其他模块访问
        self.ROLE_PERMISSIONS = ROLE_PERMISSIONS
    
    def hash_password(self, password: str) -> str:
        """Hash password"""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def generate_api_key(self) -> str:
        """Generate API key"""
        return secrets.token_urlsafe(32)
    
    def hash_api_key(self, api_key: str) -> str:
        """Hash API key for storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def verify_api_key(self, api_key: str, hashed_api_key: str) -> bool:
        """Verify API key"""
        return hashlib.sha256(api_key.encode()).hexdigest() == hashed_api_key
    
    def create_access_token(self, user_id: str, tenant_id: str, email: str, 
                           roles: List[str], additional_claims: Optional[Dict[str, Any]] = None) -> str:
        """Create access token"""
        now = datetime.utcnow()
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)
        
        # Get permissions for roles
        permissions = set()
        for role in roles:
            if role in ROLE_PERMISSIONS:
                permissions.update(ROLE_PERMISSIONS[role])
        
        payload = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "email": email,
            "roles": roles,
            "permissions": list(permissions),
            "exp": expire,
            "iat": now,
            "jti": secrets.token_urlsafe(16),
            "type": "access"
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    
    def create_refresh_token(self, user_id: str, tenant_id: str) -> str:
        """Create refresh token"""
        now = datetime.utcnow()
        expire = now + timedelta(days=settings.refresh_token_expire_days)
        
        payload = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "exp": expire,
            "iat": now,
            "jti": secrets.token_urlsafe(16),
            "type": "refresh"
        }
        
        return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    
    def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify and decode token"""
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            
            # Check if token is expired
            exp = datetime.fromtimestamp(payload.get("exp", 0))
            if exp < datetime.utcnow():
                return None
            
            return TokenData(
                user_id=payload["user_id"],
                tenant_id=payload["tenant_id"],
                email=payload["email"],
                roles=payload["roles"],
                permissions=payload["permissions"],
                exp=exp,
                iat=datetime.fromtimestamp(payload["iat"]),
                jti=payload["jti"]
            )
        except JWTError:
            return None
    
    def check_permission(self, user_roles: List[str], required_permission: str) -> bool:
        """Check if user has required permission"""
        user_permissions = set()
        for role in user_roles:
            if role in ROLE_PERMISSIONS:
                user_permissions.update(ROLE_PERMISSIONS[role])
        
        return required_permission in user_permissions
    
    def check_role(self, user_roles: List[str], required_role: str) -> bool:
        """Check if user has required role"""
        return required_role in user_roles
    
    def generate_csrf_token(self) -> str:
        """Generate CSRF token"""
        return secrets.token_urlsafe(32)
    
    def verify_csrf_token(self, token: str, expected_token: str) -> bool:
        """Verify CSRF token"""
        return secrets.compare_digest(token, expected_token)


class TenantSecurity:
    """Tenant-specific security utilities"""
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.security_manager = SecurityManager()
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data for tenant"""
        # Use tenant-specific encryption key
        tenant_key = hashlib.sha256(f"{settings.security.secret_key}:{self.tenant_id}".encode()).hexdigest()
        # TODO: Implement proper encryption with tenant-specific key
        return data  # Placeholder
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data for tenant"""
        # TODO: Implement proper decryption with tenant-specific key
        return encrypted_data  # Placeholder
    
    def generate_tenant_api_key(self) -> str:
        """Generate tenant-specific API key"""
        return f"lyss_{self.tenant_id}_{secrets.token_urlsafe(24)}"
    
    def validate_tenant_access(self, user_tenant_id: str) -> bool:
        """Validate if user belongs to tenant"""
        return self.tenant_id == user_tenant_id


# Global security manager instance
security_manager = SecurityManager()


def get_security_manager() -> SecurityManager:
    """Get security manager instance"""
    return security_manager


def get_tenant_security(tenant_id: str) -> TenantSecurity:
    """Get tenant-specific security manager"""
    return TenantSecurity(tenant_id)