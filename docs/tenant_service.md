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
    provider_name VARCHAR(50) NOT NULL, -- 'openai', 'anthropic', 'google', 'deepseek', 'custom'
    display_name VARCHAR(100) NOT NULL,
    encrypted_api_key BYTEA NOT NULL, -- 使用pgcrypto加密
    base_url VARCHAR(255),
    model_configs JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tenant_id, provider_name, display_name)
);
```

#### 支持的供应商配置 (SUPPORTED_PROVIDERS)
```python
SUPPORTED_PROVIDERS = {
    "openai": {
        "display_name": "OpenAI",
        "base_url": "https://api.openai.com/v1", 
        "models": {
            "gpt-4": {
                "display_name": "GPT-4",
                "description": "最强大的GPT-4模型，适用于复杂任务",
                "type": "chat",
                "context_window": 8192,
                "max_tokens": 4096,
                "price_per_1k_tokens": {"input": 0.03, "output": 0.06}
            },
            "gpt-4-turbo": {
                "display_name": "GPT-4 Turbo",
                "description": "更快的GPT-4版本，性价比更高",
                "type": "chat",
                "context_window": 32768,
                "max_tokens": 4096,
                "price_per_1k_tokens": {"input": 0.01, "output": 0.03}
            },
            "gpt-3.5-turbo": {
                "display_name": "GPT-3.5 Turbo",
                "description": "快速且经济的对话模型",
                "type": "chat",
                "context_window": 4096,
                "max_tokens": 2048,
                "price_per_1k_tokens": {"input": 0.001, "output": 0.002}
            }
        },
        "api_key_pattern": r"^sk-[A-Za-z0-9]{48}$",
        "test_endpoint": "/models",
        "test_method": "model_list"
    },
    "anthropic": {
        "display_name": "Anthropic",
        "base_url": "https://api.anthropic.com",
        "models": {
            "claude-3-opus-20240229": {
                "display_name": "Claude 3 Opus",
                "description": "Anthropic最强大的模型，适用于复杂推理",
                "type": "chat",
                "context_window": 200000,
                "max_tokens": 4096,
                "price_per_1k_tokens": {"input": 0.015, "output": 0.075}
            },
            "claude-3-sonnet-20240229": {
                "display_name": "Claude 3 Sonnet",
                "description": "平衡性能和成本的模型",
                "type": "chat",
                "context_window": 200000,
                "max_tokens": 4096,
                "price_per_1k_tokens": {"input": 0.003, "output": 0.015}
            },
            "claude-3-haiku-20240307": {
                "display_name": "Claude 3 Haiku",
                "description": "快速且经济的对话模型",
                "type": "chat",
                "context_window": 200000,
                "max_tokens": 4096,
                "price_per_1k_tokens": {"input": 0.0008, "output": 0.004}
            }
        },
        "api_key_pattern": r"^sk-ant-[A-Za-z0-9\-_]{95}$",
        "test_endpoint": "/v1/messages",
        "test_method": "simple_message"
    },
    "deepseek": {
        "display_name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "models": {
            "deepseek-chat": {
                "display_name": "DeepSeek Chat",
                "description": "DeepSeek通用对话模型",
                "type": "chat",
                "context_window": 32768,
                "max_tokens": 4096,
                "price_per_1k_tokens": {"input": 0.0014, "output": 0.0028}
            },
            "deepseek-coder": {
                "display_name": "DeepSeek Coder",
                "description": "专门用于代码生成和编程任务",
                "type": "chat",
                "context_window": 32768,
                "max_tokens": 4096,
                "price_per_1k_tokens": {"input": 0.0014, "output": 0.0028}
            }
        },
        "api_key_pattern": r"^sk-[A-Za-z0-9]{48}$",
        "test_endpoint": "/v1/models",
        "test_method": "model_list"
    },
    "google": {
        "display_name": "Google AI",
        "base_url": "https://generativelanguage.googleapis.com",
        "models": {
            "gemini-pro": {
                "display_name": "Gemini Pro",
                "description": "Google的先进多模态模型",
                "type": "chat",
                "context_window": 30720,
                "max_tokens": 2048,
                "price_per_1k_tokens": {"input": 0.0005, "output": 0.0015}
            },
            "gemini-pro-vision": {
                "display_name": "Gemini Pro Vision",
                "description": "支持图像理解的多模态模型",
                "type": "multimodal",
                "context_window": 30720,
                "max_tokens": 2048,
                "price_per_1k_tokens": {"input": 0.0005, "output": 0.0015}
            }
        },
        "api_key_pattern": r"^[A-Za-z0-9\-_]{39}$",
        "test_endpoint": "/v1/models",
        "test_method": "model_list"
    },
    "azure": {
        "display_name": "Azure OpenAI",
        "base_url": None,  # 需要自定义
        "models": {
            "gpt-4": {
                "display_name": "GPT-4 (Azure)",
                "description": "Azure托管的GPT-4模型",
                "type": "chat",
                "context_window": 8192,
                "max_tokens": 4096,
                "price_per_1k_tokens": {"input": 0.03, "output": 0.06}
            },
            "gpt-35-turbo": {
                "display_name": "GPT-3.5 Turbo (Azure)",
                "description": "Azure托管的GPT-3.5模型",
                "type": "chat",
                "context_window": 4096,
                "max_tokens": 2048,
                "price_per_1k_tokens": {"input": 0.001, "output": 0.002}
            }
        },
        "api_key_pattern": r"^[A-Za-z0-9]{32}$",
        "test_endpoint": "/openai/deployments",
        "test_method": "deployment_list"
    },
    "custom": {
        "display_name": "自定义供应商",
        "base_url": None,  # 需要自定义
        "models": {},  # 动态获取
        "api_key_pattern": None,  # 不验证格式
        "test_endpoint": "/v1/models",
        "test_method": "model_list"
    }
}
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

## 🧪 供应商凭证测试架构

### 🎯 设计原则
1. **保存前测试**: 所有凭证在保存前必须通过连接测试
2. **双重接口**: 提供独立的测试接口和保存接口 
3. **错误详情**: 返回详细的错误信息帮助用户排查问题
4. **超时控制**: 所有测试请求都有合理的超时限制
5. **安全第一**: 测试过程中API密钥不记录到日志

### 🔧 技术实现策略

#### 阶段1: Python原生实现（当前实施）
```python
# 位置: tenant-service/tenant_service/services/supplier_testing.py
class SupplierTester:
    def __init__(self):
        self.timeout = 10  # 10秒超时
        self.test_methods = {
            "openai": self._test_openai,
            "anthropic": self._test_anthropic,
            "google": self._test_google_ai,
            "azure": self._test_azure_openai,
            "cohere": self._test_cohere
        }
    
    async def test_supplier_connection(self, provider: str, api_key: str, base_url: str = None) -> TestResult:
        """统一的供应商连接测试接口"""
        if provider not in self.test_methods:
            raise ValueError(f"不支持的供应商: {provider}")
        
        start_time = time.time()
        try:
            result = await self.test_methods[provider](api_key, base_url)
            response_time = int((time.time() - start_time) * 1000)
            return TestResult(
                success=True,
                provider=provider,
                response_time_ms=response_time,
                **result
            )
        except Exception as e:
            return TestResult(
                success=False,
                provider=provider,
                error_message=str(e),
                error_type=self._categorize_error(e)
            )
```

#### 阶段2: EINO框架集成（长期规划）
```go
// 位置: eino-service/internal/supplier/tester.go
type SupplierTester struct {
    config *Config
    logger *log.Logger
}

func (t *SupplierTester) TestConnection(ctx context.Context, req *TestRequest) (*TestResult, error) {
    // 使用EINO的ChatModel抽象进行测试
    model, err := t.createChatModel(req.Provider, req.APIKey, req.BaseURL)
    if err != nil {
        return nil, err
    }
    
    // 发送测试消息
    result, err := model.Generate(ctx, []*Message{
        SystemMessage("You are a test assistant."),
        UserMessage("Reply with 'OK' if you received this message."),
    })
    
    return &TestResult{
        Success: err == nil,
        Provider: req.Provider,
        ResponseTime: time.Since(start),
        TestMethod: "simple_chat",
    }, nil
}
```

### 📋 具体测试方法

#### OpenAI API 测试
```python
async def _test_openai(self, api_key: str, base_url: str = None) -> dict:
    """测试OpenAI API连接"""
    base_url = base_url or "https://api.openai.com/v1"
    
    async with httpx.AsyncClient(timeout=self.timeout) as client:
        # 方法1: 获取模型列表（推荐）
        response = await client.get(
            f"{base_url}/models",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        
        if response.status_code == 200:
            models_data = response.json()
            models = [model["id"] for model in models_data.get("data", [])]
            return {
                "test_method": "model_list",
                "available_models": models[:10],  # 返回前10个模型
                "endpoint_tested": f"{base_url}/models",
                "status_code": 200
            }
        else:
            self._handle_error_response(response, "openai")
```

#### Anthropic API 测试  
```python
async def _test_anthropic(self, api_key: str, base_url: str = None) -> dict:
    """测试Anthropic API连接"""
    base_url = base_url or "https://api.anthropic.com"
    
    async with httpx.AsyncClient(timeout=self.timeout) as client:
        # 发送简单消息测试
        response = await client.post(
            f"{base_url}/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-3-haiku-20240307",
                "max_tokens": 10,
                "messages": [{"role": "user", "content": "Hello"}]
            }
        )
        
        if response.status_code == 200:
            return {
                "test_method": "simple_message",
                "model_tested": "claude-3-haiku-20240307",
                "endpoint_tested": f"{base_url}/v1/messages",
                "status_code": 200
            }
        else:
            self._handle_error_response(response, "anthropic")
```

#### Google AI API 测试
```python
async def _test_google_ai(self, api_key: str, base_url: str = None) -> dict:
    """测试Google AI API连接"""
    base_url = base_url or "https://generativelanguage.googleapis.com"
    
    async with httpx.AsyncClient(timeout=self.timeout) as client:
        # 获取模型列表
        response = await client.get(
            f"{base_url}/v1/models",
            params={"key": api_key}
        )
        
        if response.status_code == 200:
            models_data = response.json()
            models = [model["name"] for model in models_data.get("models", [])]
            return {
                "test_method": "model_list",
                "available_models": models[:10],
                "endpoint_tested": f"{base_url}/v1/models", 
                "status_code": 200
            }
        else:
            self._handle_error_response(response, "google")
```

#### DeepSeek API 测试
```python
async def _test_deepseek(self, api_key: str, base_url: str = None) -> dict:
    """测试DeepSeek API连接"""
    base_url = base_url or "https://api.deepseek.com"
    
    async with httpx.AsyncClient(timeout=self.timeout) as client:
        # 方法1: 获取模型列表（推荐）
        response = await client.get(
            f"{base_url}/v1/models",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        
        if response.status_code == 200:
            models_data = response.json()
            models = [model["id"] for model in models_data.get("data", [])]
            return {
                "test_method": "model_list",
                "available_models": models,
                "default_model": "deepseek-chat",
                "endpoint_tested": f"{base_url}/v1/models",
                "status_code": 200
            }
        
        # 方法2: 简单对话测试（如果模型列表失败）
        response = await client.post(
            f"{base_url}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10
            }
        )
        
        if response.status_code == 200:
            return {
                "test_method": "simple_chat",
                "model_tested": "deepseek-chat",
                "endpoint_tested": f"{base_url}/v1/chat/completions",
                "status_code": 200
            }
        else:
            self._handle_error_response(response, "deepseek")
```

### 🚨 错误处理和分类

#### 错误分类逻辑
```python
def _categorize_error(self, error: Exception) -> str:
    """错误分类，帮助用户快速定位问题"""
    if isinstance(error, httpx.TimeoutException):
        return "timeout"
    elif isinstance(error, httpx.ConnectError):
        return "connection_failed"
    elif hasattr(error, 'response'):
        status_code = error.response.status_code
        if status_code == 401:
            return "authentication_failed"
        elif status_code == 403:
            return "permission_denied"
        elif status_code == 404:
            return "endpoint_not_found"
        elif status_code == 429:
            return "rate_limited"
        elif status_code >= 500:
            return "server_error"
    return "unknown_error"

def _handle_error_response(self, response: httpx.Response, provider: str):
    """统一的错误处理"""
    try:
        error_data = response.json()
        error_message = error_data.get('error', {}).get('message', 'Unknown error')
    except:
        error_message = response.text or f"HTTP {response.status_code}"
    
    raise SupplierTestError(
        provider=provider,
        status_code=response.status_code,
        message=error_message,
        error_type=self._categorize_error_by_code(response.status_code)
    )
```

### 🔒 安全实施要点

#### API密钥安全处理
```python
def _sanitize_for_logging(self, data: dict) -> dict:
    """清理日志数据，确保API密钥不被记录"""
    sanitized = data.copy()
    for key in ["api_key", "key", "token", "secret"]:
        if key in sanitized:
            if isinstance(sanitized[key], str) and len(sanitized[key]) > 8:
                sanitized[key] = sanitized[key][:4] + "***" + sanitized[key][-4:]
            else:
                sanitized[key] = "***masked***"
    return sanitized

async def test_with_audit_log(self, provider: str, api_key: str, tenant_id: str, user_id: str):
    """带审计日志的测试方法"""
    # 记录测试开始（不包含API密钥）
    logger.info(
        "开始供应商连接测试",
        extra={
            "operation": "supplier_test_start",
            "provider": provider,
            "tenant_id": tenant_id,
            "user_id": user_id,
        }
    )
    
    try:
        result = await self.test_supplier_connection(provider, api_key)
        
        # 记录测试结果（不包含API密钥）
        logger.info(
            "供应商连接测试完成",
            extra={
                "operation": "supplier_test_complete",
                "provider": provider,
                "success": result.success,
                "response_time_ms": result.response_time_ms,
                "tenant_id": tenant_id,
                "user_id": user_id,
            }
        )
        
        return result
    except Exception as e:
        logger.error(
            "供应商连接测试失败",
            extra={
                "operation": "supplier_test_failed",
                "provider": provider,
                "error": str(e),
                "tenant_id": tenant_id,
                "user_id": user_id,
            }
        )
        raise
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

## 📋 字段标准化（前后端统一）

### 供应商凭证创建请求 (SupplierCredentialCreateRequest)
```json
{
  "provider_name": "deepseek",           // 供应商标识符（必填）
  "display_name": "DeepSeek开发测试",    // 显示名称（必填）
  "api_key": "sk-cc6f618f...",          // API密钥（必填）
  "base_url": "https://api.deepseek.com", // 可选，默认使用供应商配置
  "model_configs": {                     // 模型配置（可选）
    "default_model": "deepseek-chat",
    "supported_models": ["deepseek-chat", "deepseek-coder"],
    "max_tokens": 4096,
    "temperature": 0.7
  }
}
```

### 前端字段映射规则
- 前端 `name` → 后端 `display_name`
- 前端 `provider` → 后端 `provider_name`
- 前端 `api_url` → 后端 `base_url`
- 前端 `model_config` → 后端 `model_configs`

### 支持的provider_name值
- `openai` - OpenAI GPT系列
- `anthropic` - Anthropic Claude系列
- `google` - Google AI (Gemini)
- `deepseek` - DeepSeek对话和代码模型
- `azure` - Azure OpenAI服务
- `custom` - 自定义供应商

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

#### 🧪 测试供应商凭证（保存前测试）
```http
POST /api/v1/admin/suppliers/test
Authorization: Bearer <tenant_admin_token>
Content-Type: application/json
```

**请求体:**
```json
{
  "provider_name": "openai",
  "api_key": "sk-xxxxxxxxxxxxxxxxxxxxx",
  "base_url": "https://api.openai.com/v1",
  "test_config": {
    "timeout": 10,
    "test_message": "Hello, this is a test message."
  }
}
```

**响应 (成功):**
```json
{
  "success": true,
  "data": {
    "connection_status": "success",
    "provider_name": "openai",
    "test_method": "model_list",
    "response_time_ms": 456,
    "available_models": [
      "gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"
    ],
    "test_details": {
      "endpoint_tested": "https://api.openai.com/v1/models",
      "status_code": 200
    }
  },
  "message": "OpenAI连接测试成功，发现3个可用模型"
}
```

**响应 (失败):**
```json
{
  "success": false,
  "error": {
    "code": "4001",
    "message": "API密钥无效或已过期",
    "details": {
      "provider_name": "openai",
      "error_type": "authentication_failed",
      "status_code": 401,
      "provider_error": "Invalid API key provided"
    }
  }
}
```

#### 添加供应商凭证（测试通过后保存）
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

**响应:**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "provider_name": "deepseek",
      "display_name": "DeepSeek开发测试",
      "is_active": true,
      "created_at": "2025-07-15T10:30:00Z",
      "model_configs": {
        "default_model": "deepseek-chat",
        "supported_models": ["deepseek-chat", "deepseek-coder"]
      }
    }
  ]
}
```

#### 获取支持的供应商和模型树形结构
```http
GET /api/v1/admin/suppliers/available
Authorization: Bearer <tenant_admin_token>
```

**响应:**
```json
{
  "success": true,
  "data": {
    "providers": [
      {
        "provider_name": "deepseek",
        "display_name": "DeepSeek",
        "logo_url": "/images/providers/deepseek.png",
        "description": "DeepSeek是一家专注于AI大模型技术的公司",
        "base_url": "https://api.deepseek.com",
        "models": [
          {
            "model_id": "deepseek-chat",
            "display_name": "DeepSeek Chat",
            "description": "DeepSeek通用对话模型",
            "type": "chat",
            "context_window": 32768,
            "max_tokens": 4096,
            "price_per_1k_tokens": {
              "input": 0.0014,
              "output": 0.0028
            },
            "features": ["对话", "推理", "多语言"]
          },
          {
            "model_id": "deepseek-coder",
            "display_name": "DeepSeek Coder",
            "description": "专门用于代码生成和编程任务",
            "type": "chat",
            "context_window": 32768,
            "max_tokens": 4096,
            "price_per_1k_tokens": {
              "input": 0.0014,
              "output": 0.0028
            },
            "features": ["代码生成", "代码解释", "编程问答"]
          }
        ]
      },
      {
        "provider_name": "openai",
        "display_name": "OpenAI",
        "logo_url": "/images/providers/openai.png",
        "description": "OpenAI是人工智能研究公司",
        "base_url": "https://api.openai.com/v1",
        "models": [
          {
            "model_id": "gpt-4",
            "display_name": "GPT-4",
            "description": "最强大的GPT-4模型，适用于复杂任务",
            "type": "chat",
            "context_window": 8192,
            "max_tokens": 4096,
            "price_per_1k_tokens": {
              "input": 0.03,
              "output": 0.06
            },
            "features": ["复杂推理", "创意写作", "多语言"]
          }
        ]
      }
    ]
  }
}
```

#### 获取特定供应商的模型列表
```http
GET /api/v1/admin/suppliers/providers/{provider_name}/models
Authorization: Bearer <tenant_admin_token>
```

**响应:**
```json
{
  "success": true,
  "data": {
    "provider_name": "deepseek",
    "display_name": "DeepSeek",
    "models": [
      {
        "model_id": "deepseek-chat",
        "display_name": "DeepSeek Chat",
        "description": "DeepSeek通用对话模型",
        "type": "chat",
        "context_window": 32768,
        "max_tokens": 4096,
        "price_per_1k_tokens": {
          "input": 0.0014,
          "output": 0.0028
        },
        "features": ["对话", "推理", "多语言"],
        "is_available": true
      },
      {
        "model_id": "deepseek-coder",
        "display_name": "DeepSeek Coder",
        "description": "专门用于代码生成和编程任务",
        "type": "chat",
        "context_window": 32768,
        "max_tokens": 4096,
        "price_per_1k_tokens": {
          "input": 0.0014,
          "output": 0.0028
        },
        "features": ["代码生成", "代码解释", "编程问答"],
        "is_available": true
      }
    ]
  }
}
```

#### 测试已保存的供应商连接
```http
POST /api/v1/admin/suppliers/{supplier_id}/test
Authorization: Bearer <tenant_admin_token>
```

#### 更新供应商凭证
```http
PUT /api/v1/admin/suppliers/{supplier_id}
Authorization: Bearer <tenant_admin_token>
Content-Type: application/json
```

**请求体:**
```json
{
  "display_name": "DeepSeek生产环境",
  "api_key": "sk-new-key-here",
  "base_url": "https://api.deepseek.com",
  "is_active": true,
  "model_configs": {
    "default_model": "deepseek-chat",
    "supported_models": ["deepseek-chat", "deepseek-coder"]
  }
}
```

#### 删除供应商凭证
```http
DELETE /api/v1/admin/suppliers/{supplier_id}
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