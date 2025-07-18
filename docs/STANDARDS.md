# Lyss AI Platform 开发规范总纲

## 📋 文档概述

本文档是 **Lyss AI Platform** 项目的开发规范总纲，作为所有团队成员（包括AI编程助手）必须遵守的"根本大法"。严格遵循本规范将确保代码质量、提升开发效率、降低维护成本。

**适用范围**: 所有Lyss AI Platform相关的代码、文档、配置和部署

**更新日期**: 2025-07-10

---

## 1. 全局命名规范 (Global Naming Conventions)

### 1.1. 服务与仓库 (Services & Repositories)

**格式**: 采用小写kebab-case（短横线连接）

**规则**:
- 服务名必须以 `lyss-` 为前缀
- 使用描述性的英文单词
- 避免缩写，保持语义清晰

**示例**:
```
✅ 正确
lyss-api-gateway
lyss-auth-service
lyss-tenant-service
lyss-eino-service
lyss-memory-service

❌ 错误
LyssAPI
auth_svc
tenantService
EINO-Service
```

### 1.2. 数据库 (Database)

#### 表名 (Tables)
**格式**: 小写snake_case（下划线连接），使用复数形式

**示例**:
```sql
✅ 正确
users
supplier_credentials
tenant_tool_configs
memory_access_logs

❌ 错误
User
supplierCredential
TenantToolConfig
memoryAccessLog
```

#### 列名 (Columns)
**格式**: 小写snake_case

**标准字段命名**:
```sql
-- 主键
id UUID PRIMARY KEY

-- 外键 (表名单数_id)
user_id UUID
tenant_id UUID
role_id UUID

-- 时间戳
created_at TIMESTAMP
updated_at TIMESTAMP
deleted_at TIMESTAMP

-- 状态字段
is_active BOOLEAN
is_enabled BOOLEAN
status VARCHAR(20)

-- 通用字段
name VARCHAR(255)
email VARCHAR(255)
description TEXT
```

#### 索引名 (Indexes)
**格式**: `idx_<table_name>_<column_names>`

**示例**:
```sql
idx_users_email
idx_users_tenant_id
idx_supplier_credentials_tenant_id_provider
idx_memory_metadata_user_accessed
```

#### 约束名 (Constraints)
**格式**:
- 外键: `fk_<table>_<column>_<ref_table>`
- 唯一约束: `uk_<table>_<columns>`
- 检查约束: `ck_<table>_<column>_<condition>`

**示例**:
```sql
fk_users_role_id_roles
uk_users_tenant_id_email
ck_users_status_valid
```

### 1.3. API设计

#### 路径 (Paths)
**格式**: 小写kebab-case，资源名用复数

**规则**:
- 所有API路径必须以 `/api/v1/` 开头
- 使用名词表示资源，动词通过HTTP方法表达
- 嵌套资源最多不超过3层

**示例**:
```
✅ 正确
/api/v1/users
/api/v1/tenant-users
/api/v1/supplier-credentials
/api/v1/users/{user_id}/preferences
/api/v1/tenants/{tenant_id}/tool-configs

❌ 错误
/api/v1/getUsers
/api/v1/user
/api/v1/users/getTenantUsers
/api/v1/tenant/{id}/user/{uid}/config/{cid}/setting
```

#### 查询参数 (Query Parameters)
**格式**: 小写snake_case

**标准参数命名**:
```
✅ 正确
?user_id=123
?page_size=10
?sort_by=created_at
?filter_status=active
?include_deleted=false

❌ 错误
?userId=123
?pageSize=10
?sortBy=created_at
?filterStatus=active
```

### 1.4. 代码变量 (Code Variables)

#### Python (snake_case)
```python
✅ 正确
user_id = "uuid"
api_response = {}
tenant_service_client = TenantServiceClient()
get_user_preferences()

❌ 错误
userId = "uuid"
apiResponse = {}
TenantServiceClient = TenantServiceClient()
getUserPreferences()
```

#### Go (camelCase)
```go
✅ 正确
userID := "uuid"
apiResponse := map[string]interface{}{}
tenantServiceClient := NewTenantServiceClient()
getUserPreferences()

❌ 错误
user_id := "uuid"
api_response := map[string]interface{}{}
tenant_service_client := NewTenantServiceClient()
get_user_preferences()
```

#### TypeScript/JavaScript (camelCase)
```typescript
✅ 正确
const userId = "uuid";
const apiResponse = {};
const tenantServiceClient = new TenantServiceClient();
function getUserPreferences() {}

❌ 错误
const user_id = "uuid";
const api_response = {};
const tenant_service_client = new TenantServiceClient();
function get_user_preferences() {}
```

### 1.5. 环境变量 (Environment Variables)

**格式**: 大写 `SCREAMING_SNAKE_CASE`，并以服务名作为前缀

**规则**:
- 使用服务名简写作为前缀（不包含lyss-）
- 按功能分组，使用下划线分隔
- 敏感信息必须包含 `KEY`、`SECRET`、`PASSWORD` 等关键词

**示例**:
```bash
# API Gateway
API_GATEWAY_PORT=8000
API_GATEWAY_SECRET_KEY="jwt-signing-key"
API_GATEWAY_CORS_ORIGINS="http://localhost:3000"

# Auth Service  
AUTH_SERVICE_PORT=8001
AUTH_SERVICE_TOKEN_EXPIRE_MINUTES=30
AUTH_SERVICE_REFRESH_TOKEN_EXPIRE_DAYS=7

# Tenant Service
TENANT_SERVICE_PORT=8002
TENANT_SERVICE_DB_HOST=localhost
TENANT_SERVICE_PGCRYPTO_KEY="encryption-key"

# EINO Service
EINO_SERVICE_PORT=8003
EINO_SERVICE_REQUEST_TIMEOUT=30s
EINO_SERVICE_MAX_CONCURRENT_EXECUTIONS=100

# Memory Service
MEMORY_SERVICE_PORT=8004
MEMORY_SERVICE_MEM0_LLM_PROVIDER=openai
MEMORY_SERVICE_MEM0_LLM_API_KEY="backend-openai-key"
```

---

## 2. API 设计与响应规范 (API Design & Response Standards)

### 2.1. 通用原则

#### 协议要求
- **HTTPS强制**: 所有API必须使用HTTPS，开发环境可临时使用HTTP
- **版本控制**: API版本必须在URL路径中体现，如 `/api/v1/`
- **内容类型**: 请求体和响应体必须使用 `application/json`

#### 认证要求
- **JWT认证**: 所有需要认证的接口，必须通过 `Authorization: Bearer <JWT>` 请求头进行
- **请求追踪**: 所有请求必须包含或生成 `X-Request-ID` 头部
- **租户标识**: 认证后的请求必须包含 `X-Tenant-ID` 和 `X-User-ID` 头部

#### HTTP方法使用规范
```
GET    - 查询资源，必须是幂等和安全的
POST   - 创建资源或执行操作
PUT    - 完整更新资源（幂等）
PATCH  - 部分更新资源
DELETE - 删除资源（幂等）
```

### 2.2. 成功响应结构 (Success Response)

所有 `2xx` 状态码的响应体，必须遵循以下结构：

```json
{
  "success": true,
  "data": "<any>",
  "message": "操作成功描述",
  "request_id": "req-20250710143025-a1b2c3d4",
  "timestamp": "2025-07-10T10:30:00Z"
}
```

**字段说明**:
- `success`: 固定为 `true`
- `data`: 业务数据，类型根据接口而定
- `message`: 可选，操作成功的中文描述
- `request_id`: 全链路追踪ID
- `timestamp`: 响应生成时间，ISO 8601格式

**不同HTTP状态码的数据结构**:

```json
// 200 OK - 查询成功
{
  "success": true,
  "data": {"id": "uuid", "name": "用户名"},
  "request_id": "req-xxx",
  "timestamp": "2025-07-10T10:30:00Z"
}

// 201 Created - 创建成功
{
  "success": true, 
  "data": {"id": "uuid", "name": "新用户"},
  "message": "用户创建成功",
  "request_id": "req-xxx",
  "timestamp": "2025-07-10T10:30:00Z"
}

// 204 No Content - 删除成功
// 无响应体
```

### 2.3. 失败响应结构 (Error Response)

所有 `4xx` 和 `5xx` 状态码的响应体，必须遵循以下结构：

```json
{
  "success": false,
  "error": {
    "code": "2001",
    "message": "用户未认证，请先登录",
    "details": {
      "field": "authorization",
      "reason": "JWT令牌已过期"
    }
  },
  "request_id": "req-20250710143025-a1b2c3d4",
  "timestamp": "2025-07-10T10:30:00Z"
}
```

**字段说明**:
- `success`: 固定为 `false`
- `error.code`: 标准错误代码（见第3节）
- `error.message`: 用户友好的中文错误描述
- `error.details`: 可选，详细错误信息
- `request_id`: 全链路追踪ID
- `timestamp`: 响应生成时间

### 2.4. 分页规范 (Pagination)

对于返回列表的GET请求，必须支持分页。

#### 请求参数
```
page=1          # 页码，从1开始
page_size=20    # 每页数量，默认20，最大100
sort_by=created_at     # 排序字段
sort_order=desc        # 排序方向：asc/desc
```

#### 响应结构
```json
{
  "success": true,
  "data": {
    "items": [
      {"id": "uuid1", "name": "项目1"},
      {"id": "uuid2", "name": "项目2"}
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total_items": 150,
      "total_pages": 8,
      "has_next": true,
      "has_prev": false
    }
  },
  "request_id": "req-xxx",
  "timestamp": "2025-07-10T10:30:00Z"
}
```

### 2.5. 流式响应 (Streaming Response)

对于AI聊天等需要流式响应的接口，使用Server-Sent Events格式：

```http
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

data: {"type":"start","execution_id":"exec-uuid","request_id":"req-xxx"}

data: {"type":"chunk","content":"机器学习","delta":"机器学习"}

data: {"type":"chunk","content":"机器学习是","delta":"是"}

data: {"type":"end","usage":{"total_tokens":357},"execution_time_ms":1250}
```

---

## 3. 统一错误代码规范 (Unified Error Code Standards)

### 3.1. 错误代码分类

**错误代码采用4位数字，按类别分组**:

#### 1000-1999: 通用错误
```
1001 - INVALID_INPUT          # 输入参数无效
1002 - MISSING_REQUIRED_FIELD # 缺少必需字段
1003 - INVALID_FORMAT         # 格式不正确
1004 - REQUEST_TOO_LARGE      # 请求体过大
1005 - RATE_LIMIT_EXCEEDED    # 请求频率超限
```

#### 2000-2999: 认证与授权错误
```
2001 - UNAUTHORIZED           # 未认证
2002 - TOKEN_EXPIRED          # 令牌已过期
2003 - TOKEN_INVALID          # 令牌无效
2004 - INSUFFICIENT_PERMISSIONS # 权限不足
2005 - ACCOUNT_LOCKED         # 账户被锁定
2006 - PASSWORD_INCORRECT     # 密码错误
```

#### 3000-3999: 业务逻辑错误
```
3001 - TENANT_NOT_FOUND       # 租户不存在
3002 - USER_ALREADY_EXISTS    # 用户已存在
3003 - USER_NOT_FOUND         # 用户不存在
3004 - INVALID_CREDENTIALS    # 凭证无效
3005 - RESOURCE_CONFLICT      # 资源冲突
3006 - OPERATION_NOT_ALLOWED  # 操作不被允许
```

#### 4000-4999: 外部服务错误
```
4001 - AI_PROVIDER_ERROR      # AI供应商服务错误
4002 - MEMORY_SERVICE_UNAVAILABLE # 记忆服务不可用
4003 - EXTERNAL_API_TIMEOUT   # 外部API超时
4004 - THIRD_PARTY_ERROR      # 第三方服务错误
4005 - NETWORK_ERROR          # 网络错误
```

#### 5000-5999: 内部系统与数据错误
```
5001 - DATABASE_ERROR         # 数据库错误
5002 - CACHE_ERROR            # 缓存错误
5003 - INTERNAL_SERVER_ERROR  # 内部服务器错误
5004 - SERVICE_UNAVAILABLE    # 服务不可用
5005 - CONFIGURATION_ERROR    # 配置错误
```

### 3.2. 错误代码使用示例

#### Python (FastAPI)
```python
from fastapi import HTTPException

class LyssException(HTTPException):
    def __init__(self, error_code: str, message: str, details: dict = None):
        self.error_code = error_code
        self.error_message = message
        self.error_details = details
        super().__init__(status_code=400)

# 使用示例
if not user:
    raise LyssException("3003", "用户不存在", {"user_id": user_id})
```

#### Go
```go
type LyssError struct {
    Code    string      `json:"code"`
    Message string      `json:"message"`
    Details interface{} `json:"details,omitempty"`
}

func NewUserNotFoundError(userID string) *LyssError {
    return &LyssError{
        Code:    "3003",
        Message: "用户不存在",
        Details: map[string]string{"user_id": userID},
    }
}
```

---

## 4. 数据库设计规范 (Database Design Standards)

### 4.1. 表设计 (Table Design)

#### 主键规范
```sql
-- ✅ 正确：使用UUID作为主键
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- 其他字段
);

-- ❌ 错误：使用自增整数
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    -- 其他字段
);
```

#### 必需字段
每个表必须包含以下标准字段：

```sql
CREATE TABLE example_table (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 业务字段
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- 多租户隔离（共享表必需）
    tenant_id UUID NOT NULL,
    
    -- 时间戳（必需）
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- 软删除（推荐）
    deleted_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);
```

#### 外键约束
```sql
-- ✅ 正确：明确定义外键约束和级联操作
ALTER TABLE users 
ADD CONSTRAINT fk_users_role_id_roles 
FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE SET NULL;

ALTER TABLE supplier_credentials 
ADD CONSTRAINT fk_supplier_credentials_tenant_id_tenants 
FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;
```

#### 多租户隔离
**强制要求**: 任何存储在**共享数据库**中的表，**必须**包含一个非空的 `tenant_id` 字段。

```sql
-- ✅ 正确：共享表包含tenant_id
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,  -- 必需的租户隔离字段
    user_id UUID NOT NULL,
    operation VARCHAR(100) NOT NULL,
    -- 其他字段
);

-- 所有查询必须包含tenant_id过滤
SELECT * FROM audit_logs 
WHERE tenant_id = $1 AND user_id = $2;
```

### 4.2. 索引规范 (Indexing)

#### 必需索引
```sql
-- 1. 外键字段必须建立索引
CREATE INDEX idx_users_role_id ON users(role_id);
CREATE INDEX idx_users_tenant_id ON users(tenant_id);

-- 2. 常用查询字段必须建立索引
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);

-- 3. 多租户共享表的复合索引
CREATE INDEX idx_audit_logs_tenant_user ON audit_logs(tenant_id, user_id);
CREATE INDEX idx_audit_logs_tenant_created ON audit_logs(tenant_id, created_at);

-- 4. 唯一约束索引
CREATE UNIQUE INDEX uk_users_tenant_email ON users(tenant_id, email);
```

#### 索引命名规范
```sql
-- 普通索引: idx_<table>_<columns>
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_messages_conversation_created ON messages(conversation_id, created_at);

-- 唯一索引: uk_<table>_<columns>  
CREATE UNIQUE INDEX uk_users_tenant_email ON users(tenant_id, email);

-- 部分索引: idx_<table>_<columns>_<condition>
CREATE INDEX idx_users_active ON users(email) WHERE is_active = true;
```

### 4.3. 数据类型规范

#### 推荐类型映射
```sql
-- ID字段
id UUID DEFAULT gen_random_uuid()

-- 字符串
name VARCHAR(255)           -- 短文本
description TEXT            -- 长文本
email VARCHAR(255)          -- 邮箱
slug VARCHAR(100)           -- URL slug

-- 数值
price DECIMAL(10,2)         -- 货币
percentage DECIMAL(5,2)     -- 百分比
count INTEGER               -- 计数

-- 时间
created_at TIMESTAMP DEFAULT NOW()
updated_at TIMESTAMP DEFAULT NOW()
scheduled_at TIMESTAMP
expires_at TIMESTAMP

-- 布尔
is_active BOOLEAN DEFAULT TRUE
is_enabled BOOLEAN DEFAULT FALSE

-- JSON
settings JSONB DEFAULT '{}'
metadata JSONB
```

### 4.4. 数据迁移规范

#### 迁移文件命名
```
migrations/
├── 001_create_initial_tables.sql
├── 002_add_user_preferences.sql
├── 003_create_supplier_credentials.sql
├── 004_add_tool_configs.sql
```

#### 迁移脚本模板
```sql
-- Migration: 002_add_user_preferences.sql
-- Description: 添加用户偏好设置表
-- Date: 2025-07-10

BEGIN;

-- 创建新表
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    active_memory_enabled BOOLEAN DEFAULT TRUE,
    preferred_language VARCHAR(10) DEFAULT 'zh',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 创建索引
CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);
CREATE INDEX idx_user_preferences_tenant_id ON user_preferences(tenant_id);

-- 添加唯一约束
CREATE UNIQUE INDEX uk_user_preferences_user_tenant 
ON user_preferences(user_id, tenant_id);

COMMIT;
```

---

## 5. 日志与追踪规范 (Logging & Tracing Standards)

### 5.1. 日志格式

**强制要求**: 所有服务的所有日志输出，**必须**为**结构化JSON**格式。

#### 标准JSON日志结构
```json
{
  "timestamp": "2025-07-10T10:30:00.123Z",
  "level": "INFO",
  "service": "lyss-auth-service",
  "request_id": "req-20250710143025-a1b2c3d4",
  "tenant_id": "tenant-uuid",
  "user_id": "user-uuid",
  "operation": "user_login",
  "message": "用户登录成功",
  "data": {
    "email": "user@example.com",
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0..."
  },
  "duration_ms": 245,
  "success": true
}
```

### 5.2. 必需字段

每一条日志记录，**必须**包含以下字段：

#### 核心字段
- `timestamp`: 日志时间，ISO 8601格式，包含毫秒
- `level`: 日志级别（DEBUG, INFO, WARN, ERROR, FATAL）
- `service`: 服务名称（如 lyss-api-gateway）
- `message`: 日志核心信息，必须为中文

#### 追踪字段  
- `request_id`: 全链路追踪ID（从 X-Request-ID 请求头获取）
- `tenant_id`: 租户ID（如果有上下文）
- `user_id`: 用户ID（如果有上下文）

#### 可选字段
- `operation`: 操作类型（如 user_login, memory_search）
- `data`: 包含附加上下文信息的对象
- `duration_ms`: 操作耗时（毫秒）
- `success`: 操作是否成功
- `error_code`: 错误代码（如果失败）

### 5.3. 日志级别使用规范

#### DEBUG
- 详细的调试信息
- 变量值、方法参数
- 仅在开发环境使用

```json
{
  "level": "DEBUG",
  "message": "开始验证用户凭证",
  "data": {
    "username": "user@example.com",
    "method": "password_check"
  }
}
```

#### INFO  
- 关键业务流程节点
- 用户操作记录
- 系统状态变更

```json
{
  "level": "INFO",
  "operation": "user_registration",
  "message": "用户注册成功",
  "data": {
    "user_id": "uuid",
    "email": "user@example.com"
  }
}
```

#### WARN
- 潜在问题警告
- 降级处理
- 重试操作

```json
{
  "level": "WARN",
  "message": "AI服务响应缓慢，启用缓存降级",
  "data": {
    "response_time_ms": 5000,
    "threshold_ms": 3000
  }
}
```

#### ERROR
- 捕获到的异常
- 业务逻辑错误
- 外部服务失败

```json
{
  "level": "ERROR",
  "operation": "memory_search",
  "message": "记忆服务查询失败",
  "error_code": "4002",
  "data": {
    "error": "Connection timeout",
    "retry_count": 3
  }
}
```

#### FATAL
- 系统致命错误
- 服务无法启动
- 关键依赖失败

### 5.4. 安全规范

#### 敏感信息禁止记录
**严禁**在日志中以明文形式记录任何敏感信息：

```json
// ❌ 错误：泄露敏感信息
{
  "message": "用户登录",
  "data": {
    "password": "user_password",
    "api_key": "sk-xxxxxxxxxxxxx",
    "credit_card": "4111-1111-1111-1111"
  }
}

// ✅ 正确：脱敏处理
{
  "message": "用户登录",
  "data": {
    "password": "***masked***",
    "api_key": "sk-***...***",
    "credit_card": "4111-****-****-1111"
  }
}
```

#### 敏感信息识别清单
- 密码和密钥
- API密钥和令牌
- 个人身份信息（PII）
- 信用卡和银行信息
- 内部系统路径
- 详细错误堆栈（生产环境）

### 5.5. 各语言实现示例

#### Python (结构化日志)
```python
import logging
import json
from datetime import datetime

class LyssJSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": "lyss-auth-service",
            "message": record.getMessage(),
            "request_id": getattr(record, 'request_id', None),
            "tenant_id": getattr(record, 'tenant_id', None),
            "user_id": getattr(record, 'user_id', None),
        }
        
        # 添加额外数据
        if hasattr(record, 'data'):
            log_entry["data"] = record.data
            
        return json.dumps(log_entry, ensure_ascii=False)

# 使用示例
logger = logging.getLogger(__name__)
logger.info(
    "用户登录成功",
    extra={
        "request_id": "req-xxx",
        "user_id": "uuid",
        "operation": "user_login",
        "data": {"email": "user@example.com"}
    }
)
```

#### Go (结构化日志)
```go
package logging

import (
    "encoding/json"
    "log"
    "time"
)

type LogEntry struct {
    Timestamp string      `json:"timestamp"`
    Level     string      `json:"level"`
    Service   string      `json:"service"`
    RequestID string      `json:"request_id,omitempty"`
    TenantID  string      `json:"tenant_id,omitempty"`
    UserID    string      `json:"user_id,omitempty"`
    Operation string      `json:"operation,omitempty"`
    Message   string      `json:"message"`
    Data      interface{} `json:"data,omitempty"`
    Success   bool        `json:"success"`
}

func LogInfo(message string, requestID, userID string, data interface{}) {
    entry := LogEntry{
        Timestamp: time.Now().UTC().Format(time.RFC3339Nano),
        Level:     "INFO",
        Service:   "lyss-eino-service",
        RequestID: requestID,
        UserID:    userID,
        Message:   message,
        Data:      data,
        Success:   true,
    }
    
    jsonData, _ := json.Marshal(entry)
    log.Println(string(jsonData))
}
```
**文档版本**: 1.0.0  
**最后更新**: 2025-07-10  
**下次审查**: 2025-08-10