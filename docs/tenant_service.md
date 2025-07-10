# Tenant Service 规范文档

## 🎯 服务概述

Tenant Service 是 Lyss AI Platform 的**核心业务数据管理服务**，负责租户管理、用户管理、角色分配，以及**最关键的供应商凭证管理**。本服务拥有所有用户相关的业务数据，并实现严格的多租户数据隔离。

## 📋 核心职责

### ✅ 负责的功能
1. **租户管理**: 租户的创建、配置和生命周期管理
2. **用户管理**: 用户注册、资料管理、状态控制
3. **角色和权限管理**: RBAC体系的实现和维护
4. **供应商凭证管理**: AI供应商API密钥的加密存储和管理
5. **工具配置管理**: 租户级别的EINO工具开关配置
6. **用户偏好管理**: 个性化设置和记忆开关控制

### ❌ 不负责的功能
- JWT令牌的签发和验证（由Auth Service负责）
- AI工作流的执行和编排（由EINO Service负责）
- 对话记忆的存储和检索（由Memory Service负责）

## 🏗️ 数据模型设计

### 租户相关表结构

#### tenants表
```sql
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'suspended', 'inactive'
    subscription_plan VARCHAR(50) DEFAULT 'basic',
    max_users INTEGER DEFAULT 10,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### users表 (租户隔离)
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    username VARCHAR(100),
    hashed_password VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role_id UUID NOT NULL REFERENCES roles(id),
    is_active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tenant_id, email),
    UNIQUE(tenant_id, username)
);
```

#### roles表
```sql
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE, -- 'end_user', 'tenant_admin', 'super_admin'
    display_name VARCHAR(100),
    description TEXT,
    permissions JSONB DEFAULT '[]',
    is_system_role BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 供应商凭证管理表结构

#### supplier_credentials表 (⚠️ 加密存储)
```sql
CREATE TABLE supplier_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    provider_name VARCHAR(50) NOT NULL, -- 'openai', 'anthropic', 'google'
    display_name VARCHAR(100),
    encrypted_api_key BYTEA NOT NULL, -- 使用pgcrypto加密
    base_url VARCHAR(255),
    model_configs JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tenant_id, provider_name, display_name)
);
```

### 工具配置管理表结构

#### tenant_tool_configs表
```sql
CREATE TABLE tenant_tool_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    workflow_name VARCHAR(100) NOT NULL, -- 'simple_chat', 'optimized_rag'
    tool_node_name VARCHAR(100) NOT NULL, -- 'web_search', 'database_query' 
    is_enabled BOOLEAN DEFAULT TRUE,
    config_params JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tenant_id, workflow_name, tool_node_name)
);
```

### 用户偏好管理表结构

#### user_preferences表
```sql
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    active_memory_enabled BOOLEAN DEFAULT TRUE, -- 记忆开关
    preferred_language VARCHAR(10) DEFAULT 'zh',
    theme VARCHAR(20) DEFAULT 'light',
    notification_settings JSONB DEFAULT '{}',
    ai_model_preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, tenant_id)
);
```

## 🔐 供应商凭证加密机制

### 🚨 pgcrypto加密实现

**⚠️ 重要安全声明**: 用于pgcrypto的对称加密密钥**绝不能**硬编码在代码中！

#### 推荐的密钥管理策略
1. **开发环境**: 从环境变量`PGCRYPTO_KEY`注入
2. **生产环境**: 从专用密钥管理服务(KMS)获取，如AWS KMS、HashiCorp Vault
3. **密钥轮换**: 定期轮换加密密钥并重新加密存储的凭证

#### 加密存储实现
```sql
-- 存储加密的API密钥
INSERT INTO supplier_credentials (tenant_id, provider_name, encrypted_api_key)
VALUES (
    $1, 
    $2, 
    pgp_sym_encrypt($3, $4)
);
-- 参数: $1=tenant_id, $2='openai', $3='sk-xxxxx', $4=从环境变量获取的密钥
```

#### 解密读取实现
```sql
-- 读取解密的API密钥
SELECT 
    provider_name,
    pgp_sym_decrypt(encrypted_api_key, $1) AS api_key
FROM supplier_credentials 
WHERE id = $2 AND tenant_id = $3;
-- 参数: $1=解密密钥, $2=credential_id, $3=tenant_id
```

#### Python实现示例
```python
import os
from sqlalchemy import text

class CredentialManager:
    def __init__(self):
        # 🚨 从环境变量或KMS获取加密密钥
        self.encryption_key = os.getenv('PGCRYPTO_KEY')
        if not self.encryption_key:
            raise ValueError("PGCRYPTO_KEY环境变量未设置")
    
    async def store_credential(self, tenant_id: str, provider: str, api_key: str):
        """加密存储供应商凭证"""
        query = text("""
            INSERT INTO supplier_credentials (tenant_id, provider_name, encrypted_api_key)
            VALUES (:tenant_id, :provider, pgp_sym_encrypt(:api_key, :key))
        """)
        await self.db.execute(query, {
            "tenant_id": tenant_id,
            "provider": provider, 
            "api_key": api_key,
            "key": self.encryption_key
        })
    
    async def get_credential(self, credential_id: str, tenant_id: str) -> str:
        """解密读取供应商凭证"""
        query = text("""
            SELECT pgp_sym_decrypt(encrypted_api_key, :key) AS api_key
            FROM supplier_credentials 
            WHERE id = :id AND tenant_id = :tenant_id
        """)
        result = await self.db.fetch_one(query, {
            "id": credential_id,
            "tenant_id": tenant_id,
            "key": self.encryption_key
        })
        return result["api_key"] if result else None
```

## 📡 对外API接口

### 1. 租户管理API

#### 创建租户
```http
POST /api/v1/admin/tenants
Authorization: Bearer <super_admin_token>
Content-Type: application/json
```

**请求体:**
```json
{
  "name": "Acme Corporation",
  "slug": "acme-corp",
  "subscription_plan": "enterprise",
  "max_users": 100,
  "settings": {
    "timezone": "Asia/Shanghai",
    "default_language": "zh"
  }
}
```

#### 获取租户列表
```http
GET /api/v1/admin/tenants?page=1&size=20
Authorization: Bearer <super_admin_token>
```

### 2. 用户管理API

#### 用户注册
```http
POST /api/v1/admin/users
Authorization: Bearer <tenant_admin_token>
Content-Type: application/json
```

**请求体:**
```json
{
  "email": "user@example.com",
  "username": "john_doe",
  "password": "secure_password123",
  "first_name": "John",
  "last_name": "Doe", 
  "role": "end_user"
}
```

#### 获取用户列表 (租户级)
```http
GET /api/v1/admin/users?page=1&size=20&role=end_user
Authorization: Bearer <tenant_admin_token>
```

### 3. 供应商凭证管理API

#### 添加供应商凭证
```http
POST /api/v1/admin/suppliers
Authorization: Bearer <tenant_admin_token>
Content-Type: application/json
```

**请求体:**
```json
{
  "provider_name": "openai",
  "display_name": "OpenAI Production",
  "api_key": "sk-xxxxxxxxxxxxxxxxxxxxx",
  "base_url": "https://api.openai.com/v1",
  "model_configs": {
    "gpt-4": {
      "max_tokens": 4096,
      "temperature": 0.7
    }
  }
}
```

**响应:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "provider_name": "openai", 
    "display_name": "OpenAI Production",
    "is_active": true,
    "created_at": "2025-07-10T10:30:00Z"
  },
  "message": "供应商凭证添加成功"
}
```

#### 获取供应商列表 (不返回密钥)
```http
GET /api/v1/admin/suppliers
Authorization: Bearer <tenant_admin_token>
```

#### 测试供应商连接
```http
POST /api/v1/admin/suppliers/{supplier_id}/test
Authorization: Bearer <tenant_admin_token>
```

### 4. 工具配置管理API

#### 更新工具配置
```http
PUT /api/v1/admin/tool-configs
Authorization: Bearer <tenant_admin_token>
Content-Type: application/json
```

**请求体:**
```json
{
  "workflow_name": "optimized_rag",
  "tools": [
    {
      "tool_node_name": "web_search",
      "is_enabled": true,
      "config_params": {"max_results": 5}
    },
    {
      "tool_node_name": "database_query", 
      "is_enabled": false
    }
  ]
}
```

### 5. 用户偏好管理API

#### 更新用户偏好
```http
PUT /api/v1/admin/users/{user_id}/preferences
Authorization: Bearer <token>
Content-Type: application/json
```

**请求体:**
```json
{
  "active_memory_enabled": true,
  "preferred_language": "zh",
  "theme": "dark",
  "ai_model_preferences": {
    "default_model": "gpt-4",
    "temperature": 0.7
  }
}
```

## 🔧 内部服务API

### 为Auth Service提供的验证接口

#### 用户验证
```http
POST /internal/users/verify
Content-Type: application/json
X-Request-ID: {request_id}
```

**请求体:**
```json
{
  "username": "user@example.com"
}
```

**响应:**
```json
{
  "success": true,
  "data": {
    "user_id": "uuid",
    "email": "user@example.com",
    "hashed_password": "bcrypt_hash",
    "tenant_id": "uuid",
    "role": "end_user",
    "is_active": true
  }
}
```

### 为EINO Service提供的配置接口

#### 获取工具配置
```http
GET /internal/tool-configs/{tenant_id}/{workflow_name}
X-Request-ID: {request_id}
```

#### 获取供应商凭证 (解密)
```http
GET /internal/suppliers/{tenant_id}/{provider_name}
X-Request-ID: {request_id}
```

## 📝 多租户数据隔离实现

### 查询过滤器强制执行
```python
from sqlalchemy import select, and_

class TenantAwareRepository:
    def __init__(self, session, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id
    
    async def get_users(self, **filters):
        """所有用户查询必须包含tenant_id过滤"""
        query = select(User).where(
            and_(
                User.tenant_id == self.tenant_id,  # 🚨 强制租户隔离
                User.is_active == True,
                **filters
            )
        )
        return await self.session.execute(query)
    
    async def get_supplier_credentials(self):
        """供应商凭证查询必须包含tenant_id过滤"""
        query = select(SupplierCredential).where(
            SupplierCredential.tenant_id == self.tenant_id  # 🚨 强制租户隔离
        )
        return await self.session.execute(query)
```

### 中间件级别的租户注入
```python
from fastapi import Request, Depends

async def get_current_tenant_id(request: Request) -> str:
    """从JWT中提取tenant_id"""
    tenant_id = request.headers.get("X-Tenant-ID")
    if not tenant_id:
        raise HTTPException(401, "Missing tenant information")
    return tenant_id

async def get_tenant_repository(
    tenant_id: str = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
) -> TenantAwareRepository:
    """获取租户感知的数据访问层"""
    return TenantAwareRepository(session, tenant_id)
```

## 📝 日志规范

### 业务操作日志格式
```json
{
  "timestamp": "2025-07-10T10:30:00Z",
  "level": "INFO",
  "service": "tenant_service", 
  "request_id": "req-20250710143025-a1b2c3d4",
  "tenant_id": "tenant-uuid",
  "user_id": "user-uuid",
  "operation": "create_supplier_credential",
  "resource_type": "supplier_credential",
  "resource_id": "credential-uuid",
  "provider_name": "openai",
  "success": true,
  "message": "供应商凭证创建成功"
}
```

### 安全审计日志
```json
{
  "timestamp": "2025-07-10T10:30:00Z",
  "level": "WARNING",
  "service": "tenant_service",
  "event_type": "credential_access",
  "tenant_id": "tenant-uuid", 
  "user_id": "user-uuid",
  "credential_id": "credential-uuid",
  "provider_name": "openai",
  "operation": "decrypt_api_key",
  "ip_address": "192.168.1.100",
  "message": "供应商凭证解密访问"
}
```

## 🔒 安全配置

### 环境变量配置
```bash
# 数据库连接
DB_HOST=localhost
DB_PORT=5432
DB_USERNAME=lyss_user
DB_PASSWORD=强密码
DB_DATABASE=lyss_tenant

# pgcrypto加密密钥 
PGCRYPTO_KEY="32字符以上的强加密密钥"

# 密码策略
MIN_PASSWORD_LENGTH=8
REQUIRE_SPECIAL_CHARS=true
REQUIRE_NUMBERS=true

# 速率限制
MAX_REQUESTS_PER_MINUTE=100
```

### 权限验证装饰器
```python
from functools import wraps
from fastapi import HTTPException

def require_role(required_roles: List[str]):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user_role = get_current_user_role()
            if current_user_role not in required_roles:
                raise HTTPException(403, "权限不足")
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# 使用示例
@require_role(["tenant_admin", "super_admin"])
async def create_supplier_credential():
    pass
```

## 🚀 部署和运行

### 启动命令
```bash
cd services/tenant
uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```

### 数据库初始化
```sql
-- 启用pgcrypto扩展
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 创建基础角色
INSERT INTO roles (name, display_name, is_system_role) VALUES
('super_admin', '超级管理员', true),
('tenant_admin', '租户管理员', true), 
('end_user', '终端用户', true);
```

### 健康检查
```http
GET /health
```

## ⚠️ 关键约束和限制

### 强制约束
1. **数据隔离**: 所有业务查询必须包含tenant_id过滤
2. **凭证安全**: API密钥必须使用pgcrypto加密存储
3. **权限验证**: 所有管理操作必须验证用户角色
4. **审计日志**: 所有敏感操作必须记录审计日志

### 性能要求
- **查询响应**: P95 < 200ms
- **并发处理**: 支持2000并发请求
- **数据安全**: 加密操作不得影响用户体验

### 监控指标
- 租户和用户增长统计
- 供应商凭证使用频率
- 加密解密操作性能
- 权限验证成功率
- 数据隔离违规检测

---

**🔐 安全警告**: Tenant Service管理整个平台最敏感的数据，包括用户信息和供应商凭证。任何修改都必须经过严格的安全审查和多租户隔离测试。