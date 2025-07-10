

## 6. 代码提交与版本控制规范 (Code Submission & Version Control Standards)

### 6.1. 分支模型 (Branching Model)

采用简化的GitFlow模型：

#### 分支类型和用途
```
main
├─ develop
│  ├─ feature/auth-jwt-refresh
│  ├─ feature/memory-search-optimization  
│  └─ feature/eino-tool-config
├─ hotfix/fix-memory-leak
└─ release/v1.2.0
```

#### 分支规则
- **main**: 生产环境分支，受保护，只接受合并请求
- **develop**: 开发主分支，所有功能分支的合并目标
- **feature/<feature-name>**: 功能开发分支，从develop创建
- **hotfix/<fix-name>**: 紧急生产修复分支，从main创建
- **release/<version>**: 发布准备分支，从develop创建

#### 分支命名规范
```
✅ 正确
feature/user-authentication
feature/memory-service-optimization
hotfix/jwt-token-validation
release/v1.2.0

❌ 错误
feature/userAuth
feature/MemoryOptimization
hotfix/fix
release/1.2
```

### 6.2. 提交信息 (Commit Messages)

**必须**遵循**Conventional Commits**规范。

#### 格式规范
```
<type>(<scope>): <subject>

[可选的 body]

[可选的 footer]
```

#### Type类型
```
feat     - 新功能
fix      - 错误修复
docs     - 文档变更
style    - 代码格式调整（不影响代码运行的变动）
refactor - 代码重构（既不是新增功能，也不是修复bug）
perf     - 性能优化
test     - 增加测试
chore    - 构建过程或辅助工具的变动
ci       - CI配置文件和脚本的变更
revert   - 撤销之前的commit
```

#### Scope范围
```
auth     - 认证服务
tenant   - 租户服务
eino     - EINO服务
memory   - 记忆服务
gateway  - API网关
frontend - 前端
db       - 数据库
docs     - 文档
config   - 配置
```

#### 提交信息示例
```
✅ 正确
feat(auth): add JWT refresh token endpoint
fix(eino): correct tool node execution order in RAG workflow
docs(standards): update database naming conventions
refactor(tenant): simplify user creation logic
perf(memory): optimize vector search with caching
test(auth): add unit tests for password validation

❌ 错误
added new feature
fix bug
update docs
changes
```

#### 完整提交信息示例
```
feat(memory): add user memory preference toggle

添加用户记忆偏好开关功能，允许用户启用或禁用AI记忆功能。

- 在user_preferences表中添加active_memory_enabled字段
- 实现Memory Service的开关检查逻辑
- 添加相关API端点和前端界面
- 更新相关文档和测试

Closes #123
```

### 6.3. 代码审查规范 (Code Review Standards)

#### 必需审查项
1. **功能正确性**: 代码是否实现了预期功能
2. **安全性**: 是否存在安全漏洞或敏感信息泄露
3. **性能**: 是否存在明显的性能问题
4. **多租户隔离**: 是否正确实现租户数据隔离
5. **错误处理**: 是否有适当的错误处理和日志记录
6. **测试覆盖**: 是否包含足够的单元测试

#### 代码审查检查清单
```markdown
## 功能性
- [ ] 代码实现了需求中描述的功能
- [ ] 边界条件处理正确
- [ ] 错误情况处理适当

## 安全性  
- [ ] 所有用户输入都经过验证
- [ ] 敏感信息不会泄露到日志
- [ ] 多租户数据隔离正确实现
- [ ] API权限检查到位

## 性能
- [ ] 数据库查询有适当的索引
- [ ] 避免N+1查询问题
- [ ] 大数据量操作有分页处理

## 代码质量
- [ ] 遵循项目命名规范
- [ ] 有足够的注释说明
- [ ] 无明显的代码重复
- [ ] 遵循服务职责边界

## 测试
- [ ] 包含单元测试
- [ ] 测试覆盖主要逻辑路径
- [ ] 测试数据不包含敏感信息
```

### 6.4. 合并请求规范 (Pull Request Standards)

#### PR标题格式
```
[Type] Service: Brief description

feat(auth): Add JWT refresh token support
fix(memory): Resolve memory leak in search cache
docs(standards): Update API response format
```

#### PR描述模板
```markdown
## 变更描述
简要描述本次变更的内容和目的。

## 变更类型
- [ ] 新功能
- [ ] 错误修复
- [ ] 重构
- [ ] 文档更新
- [ ] 性能优化

## 影响范围
- [ ] API接口变更
- [ ] 数据库schema变更
- [ ] 配置文件变更
- [ ] 依赖包变更

## 测试情况
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 手动测试完成

## 检查清单
- [ ] 遵循代码规范
- [ ] 包含适当的日志记录
- [ ] 更新相关文档
- [ ] 多租户隔离正确
```

---
## 7. 环境与配置管理规范 (Environment & Configuration Management Standards)

### 7.1. 环境定义

#### 环境分类
```
local       - 本地开发环境
development - 共享的开发/测试环境  
staging     - 预生产环境
production  - 生产环境
```

#### 环境特性对比
| 特性 | Local | Development | Staging | Production |
|------|-------|-------------|---------|------------|
| 数据库 | 本地PostgreSQL | 共享测试DB | 生产级DB | 生产DB |
| 日志级别 | DEBUG | INFO | INFO | WARN |
| 缓存 | 本地Redis | 共享Redis | 生产级Redis | 生产Redis |
| HTTPS | 可选 | 可选 | 必需 | 必需 |
| 监控 | 无 | 基础监控 | 完整监控 | 完整监控 |

### 7.2. 配置与密钥管理

#### 配置层次结构
```
1. 默认配置（代码中）
2. 环境配置文件
3. 环境变量
4. 外部配置服务（生产环境）
```

#### 密钥管理策略

**严禁**将任何包含密钥或敏感配置的文件（如 `.env`）提交到Git仓库。

##### 本地开发环境 (local)
```bash
# .env.local (不提交到Git)
API_GATEWAY_SECRET_KEY="local-development-key"
TENANT_SERVICE_PGCRYPTO_KEY="local-encryption-key"
MEMORY_SERVICE_MEM0_LLM_API_KEY="local-openai-key"
```

##### 开发环境 (development)
```bash
# 通过环境变量注入
export API_GATEWAY_SECRET_KEY="dev-jwt-signing-key"
export TENANT_SERVICE_PGCRYPTO_KEY="dev-encryption-key"
```

##### 生产环境 (production)
```bash
# 从密钥管理服务获取
API_GATEWAY_SECRET_KEY=$(aws kms decrypt --query Plaintext --ciphertext-blob fileb://jwt-key.encrypted)
TENANT_SERVICE_PGCRYPTO_KEY=$(vault kv get -field=key secret/pgcrypto)
```

### 7.3. 配置文件规范

#### 配置文件结构
```
config/
├── default.yaml          # 默认配置
├── local.yaml            # 本地开发配置
├── development.yaml      # 开发环境配置
├── staging.yaml          # 预生产配置
├── production.yaml       # 生产配置（不含密钥）
└── .env.example          # 环境变量示例
```

#### 配置文件示例
```yaml
# config/default.yaml
server:
  port: 8000
  timeout: 30s
  
database:
  host: localhost
  port: 5432
  database: lyss_platform
  max_connections: 100
  
logging:
  level: INFO
  format: json
  
security:
  jwt_expire_minutes: 30
  password_min_length: 8
```

```yaml
# config/production.yaml
server:
  timeout: 60s
  
database:
  max_connections: 200
  connection_timeout: 10s
  
logging:
  level: WARN
  
security:
  jwt_expire_minutes: 15
  password_min_length: 12
  require_mfa: true
```

### 7.4. 环境变量规范

#### 环境变量分类
```bash
# 服务配置
SERVICE_NAME=lyss-auth-service
SERVICE_PORT=8001
SERVICE_ENVIRONMENT=production

# 数据库配置  
DB_HOST=db.lyss.internal
DB_PORT=5432
DB_USERNAME=lyss_auth
DB_PASSWORD=${SECRET_DB_PASSWORD}
DB_DATABASE=lyss_auth
DB_MAX_CONNECTIONS=50

# 缓存配置
REDIS_HOST=redis.lyss.internal
REDIS_PORT=6379
REDIS_PASSWORD=${SECRET_REDIS_PASSWORD}
REDIS_DB=0

# 安全配置
JWT_SECRET_KEY=${SECRET_JWT_KEY}
ENCRYPTION_KEY=${SECRET_ENCRYPTION_KEY}

# 外部服务
TENANT_SERVICE_URL=https://tenant.lyss.internal
MEMORY_SERVICE_URL=https://memory.lyss.internal

# 监控配置
LOG_LEVEL=WARN
METRICS_ENABLED=true
TRACING_ENABLED=true
```

#### 密钥注入示例
```bash
# 开发环境：直接设置
export JWT_SECRET_KEY="development-jwt-key"

# 生产环境：从密钥管理服务获取
export JWT_SECRET_KEY=$(aws ssm get-parameter --name "/lyss/prod/jwt-secret" --with-decryption --query 'Parameter.Value' --output text)

export ENCRYPTION_KEY=$(vault kv get -field=key secret/lyss/prod/encryption)
```

### 7.5. 配置验证

#### 启动时配置检查
```python
# Python配置验证示例
import os
from typing import Optional

class Config:
    def __init__(self):
        self.service_port = int(os.getenv("SERVICE_PORT", 8000))
        self.jwt_secret = os.getenv("JWT_SECRET_KEY")
        self.db_host = os.getenv("DB_HOST", "localhost")
        
        # 验证必需配置
        self._validate()
    
    def _validate(self):
        if not self.jwt_secret:
            raise ValueError("JWT_SECRET_KEY环境变量未设置")
        
        if len(self.jwt_secret) < 32:
            raise ValueError("JWT_SECRET_KEY长度不足，至少需要32字符")
            
        if self.service_port < 1 or self.service_port > 65535:
            raise ValueError(f"SERVICE_PORT无效: {self.service_port}")
```

```go
// Go配置验证示例
package config

import (
    "fmt"
    "os"
    "strconv"
)

type Config struct {
    ServicePort int
    JWTSecret   string
    DBHost      string
}

func LoadConfig() (*Config, error) {
    config := &Config{
        ServicePort: 8000,
        DBHost:     "localhost",
    }
    
    if port := os.Getenv("SERVICE_PORT"); port != "" {
        if p, err := strconv.Atoi(port); err == nil {
            config.ServicePort = p
        }
    }
    
    config.JWTSecret = os.Getenv("JWT_SECRET_KEY")
    if config.JWTSecret == "" {
        return nil, fmt.Errorf("JWT_SECRET_KEY环境变量未设置")
    }
    
    if len(config.JWTSecret) < 32 {
        return nil, fmt.Errorf("JWT_SECRET_KEY长度不足，至少需要32字符")
    }
    
    return config, nil
}
```

---

## 8. 测试规范 (Testing Standards)

### 8.1. 测试分类

#### 测试金字塔
```
       /\
      /  \     E2E Tests (端到端测试)
     /____\    Integration Tests (集成测试)  
    /      \   Unit Tests (单元测试)
   /________\  
```

#### 测试类型定义
- **单元测试**: 测试单个函数或方法
- **集成测试**: 测试服务间交互
- **端到端测试**: 测试完整用户流程
- **性能测试**: 测试系统性能和负载
- **安全测试**: 测试安全漏洞和权限

### 8.2. 测试覆盖率要求

#### 覆盖率目标
```
单元测试覆盖率    >= 80%
集成测试覆盖率    >= 60%
关键路径覆盖率    = 100%
```

#### 关键路径定义
- 用户认证和授权
- 多租户数据隔离
- AI工作流执行
- 供应商凭证管理
- 记忆数据处理

### 8.3. 测试命名规范

#### 测试文件命名
```
Python:
├── test_auth_service.py
├── test_user_management.py
├── test_integration_auth_tenant.py

Go:
├── auth_service_test.go
├── user_management_test.go
├── integration_auth_tenant_test.go

TypeScript:
├── auth.service.test.ts
├── user-management.test.ts
├── integration.auth-tenant.test.ts
```

#### 测试函数命名
```python
# Python测试命名
def test_create_user_with_valid_data_should_succeed():
    pass

def test_create_user_with_duplicate_email_should_fail():
    pass

def test_authenticate_user_with_invalid_password_should_return_unauthorized():
    pass
```

```go
// Go测试命名
func TestCreateUserWithValidDataShouldSucceed(t *testing.T) {
    // 测试逻辑
}

func TestCreateUserWithDuplicateEmailShouldFail(t *testing.T) {
    // 测试逻辑
}
```

### 8.4. 测试数据管理

#### 测试数据原则
- 使用faker生成随机测试数据
- 避免依赖外部数据源
- 每个测试独立，不共享状态
- 测试完成后清理数据

#### 测试数据示例
```python
# Python测试数据工厂
import factory
from faker import Faker

fake = Faker('zh_CN')

class TenantFactory(factory.Factory):
    class Meta:
        model = Tenant
    
    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    name = factory.LazyAttribute(lambda _: fake.company())
    slug = factory.LazyAttribute(lambda obj: obj.name.lower().replace(' ', '-'))
    
class UserFactory(factory.Factory):
    class Meta:
        model = User
    
    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    email = factory.LazyAttribute(lambda _: fake.email())
    username = factory.LazyAttribute(lambda obj: obj.email.split('@')[0])
    tenant = factory.SubFactory(TenantFactory)
```

### 8.5. 多租户测试

#### 租户隔离测试
```python
def test_user_query_should_filter_by_tenant():
    # 创建两个租户的用户
    tenant1 = TenantFactory()
    tenant2 = TenantFactory()
    
    user1 = UserFactory(tenant=tenant1)
    user2 = UserFactory(tenant=tenant2)
    
    # 查询tenant1的用户，应该只返回user1
    users = get_users_by_tenant(tenant1.id)
    
    assert len(users) == 1
    assert users[0].id == user1.id
    assert users[0].tenant_id == tenant1.id
```

---

## 9. 安全规范 (Security Standards)

### 9.1. 认证与授权

#### JWT安全要求
```python
# JWT配置安全要求
JWT_CONFIG = {
    "algorithm": "HS256",                    # 强签名算法
    "secret_key_min_length": 32,            # 密钥最小长度
    "access_token_expire_minutes": 30,      # 访问令牌短期有效
    "refresh_token_expire_days": 7,         # 刷新令牌适中有效期
    "issuer": "lyss-auth-service",          # 明确签发者
    "audience": "lyss-platform",            # 明确受众
}
```

#### 权限验证示例
```python
from functools import wraps
from flask import request, jsonify

def require_permission(permission: str):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # 验证JWT令牌
            token = extract_jwt_token(request)
            payload = verify_jwt_token(token)
            
            # 检查权限
            user_permissions = get_user_permissions(payload['user_id'])
            if permission not in user_permissions:
                return jsonify({
                    "success": false,
                    "error": {
                        "code": "2004",
                        "message": "权限不足"
                    }
                }), 403
            
            return f(*args, **kwargs)
        return wrapper
    return decorator

# 使用示例
@require_permission("user:create")
def create_user():
    pass
```

### 9.2. 数据加密

#### 敏感数据加密存储
```sql
-- pgcrypto列级加密示例
CREATE TABLE supplier_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    provider_name VARCHAR(50) NOT NULL,
    encrypted_api_key BYTEA NOT NULL,  -- 加密存储
    created_at TIMESTAMP DEFAULT NOW()
);

-- 加密存储
INSERT INTO supplier_credentials (tenant_id, provider_name, encrypted_api_key)
VALUES ($1, $2, pgp_sym_encrypt($3, $4));

-- 解密读取
SELECT provider_name, pgp_sym_decrypt(encrypted_api_key, $1) AS api_key
FROM supplier_credentials 
WHERE tenant_id = $2;
```

#### 传输加密
- 所有API通信必须使用HTTPS/TLS 1.3
- WebSocket连接必须使用WSS
- 数据库连接必须启用SSL
- 服务间通信推荐使用mTLS

### 9.3. 输入验证

#### API输入验证
```python
from pydantic import BaseModel, validator, Field
from typing import Optional

class CreateUserRequest(BaseModel):
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    first_name: Optional[str] = Field(None, max_length=100)
    
    @validator('password')
    def validate_password(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('密码必须包含大写字母')
        if not re.search(r'[a-z]', v):
            raise ValueError('密码必须包含小写字母')
        if not re.search(r'\d', v):
            raise ValueError('密码必须包含数字')
        return v
    
    @validator('email')
    def validate_email_domain(cls, v):
        # 企业邮箱域名白名单验证
        allowed_domains = ['company.com', 'partner.com']
        domain = v.split('@')[1]
        if domain not in allowed_domains:
            raise ValueError(f'不支持的邮箱域名: {domain}')
        return v
```

#### SQL注入防护
```python
# ✅ 正确：使用参数化查询
async def get_user_by_email(email: str, tenant_id: str):
    query = """
        SELECT id, email, username, role_id
        FROM users 
        WHERE email = $1 AND tenant_id = $2 AND is_active = true
    """
    return await db.fetch_one(query, email, tenant_id)

# ❌ 错误：直接字符串拼接
async def get_user_by_email_unsafe(email: str, tenant_id: str):
    query = f"""
        SELECT * FROM users 
        WHERE email = '{email}' AND tenant_id = '{tenant_id}'
    """
    return await db.fetch_one(query)
```

### 9.4. 审计日志

#### 安全事件记录
```python
def log_security_event(event_type: str, user_id: str = None, **data):
    """记录安全相关事件"""
    security_log = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "user_id": user_id,
        "ip_address": get_client_ip(),
        "user_agent": get_user_agent(),
        "data": sanitize_log_data(data)
    }
    
    # 发送到安全日志收集系统
    security_logger.warning(json.dumps(security_log))

# 使用示例
log_security_event("failed_login_attempt", 
                  user_id=user_id,
                  email=email,
                  failure_count=3)

log_security_event("api_key_accessed",
                  user_id=user_id, 
                  provider="openai",
                  credential_id=cred_id)
```

#### 必须记录的安全事件
- 登录成功/失败
- 权限变更
- 密钥访问
- 数据导出
- 系统配置变更
- 异常访问模式

---

## 10. 性能与监控规范 (Performance & Monitoring Standards)

### 10.1. 性能要求

#### API响应时间要求
```
API类型          P95延迟    P99延迟    可用性
认证接口         < 200ms    < 500ms    99.9%
查询接口         < 300ms    < 800ms    99.5%
AI工作流         < 3000ms   < 8000ms   99.0%
文件上传         < 5000ms   < 15000ms  99.0%
```

#### 数据库性能要求
```
查询类型          最大执行时间
简单查询         < 10ms
复杂查询         < 100ms
聚合查询         < 500ms
全文搜索         < 200ms
```

### 10.2. 监控指标

#### 应用指标
```python
# 自定义监控指标示例
from prometheus_client import Counter, Histogram, Gauge

# 请求计数器
request_count = Counter(
    'lyss_http_requests_total',
    'Total HTTP requests',
    ['service', 'method', 'endpoint', 'status']
)

# 响应时间直方图
request_duration = Histogram(
    'lyss_http_request_duration_seconds',
    'HTTP request duration',
    ['service', 'method', 'endpoint']
)

# 活跃用户数
active_users = Gauge(
    'lyss_active_users_total',
    'Number of active users',
    ['tenant_id']
)

# AI工作流执行指标
workflow_executions = Counter(
    'lyss_workflow_executions_total',
    'Total workflow executions',
    ['workflow_type', 'status']
)
```

#### 业务指标
- 用户注册和登录数量
- AI工作流执行成功率
- 供应商API调用统计
- 记忆存储和检索次数
- 错误率和异常分布

### 10.3. 健康检查

#### 健康检查端点
```python
from fastapi import FastAPI
from typing import Dict, Any

app = FastAPI()

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """综合健康检查"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "checks": {}
    }
    
    # 数据库健康检查
    try:
        await db.execute("SELECT 1")
        health_status["checks"]["database"] = "healthy"
    except Exception as e:
        health_status["checks"]["database"] = "unhealthy"
        health_status["status"] = "degraded"
    
    # Redis健康检查
    try:
        await redis.ping()
        health_status["checks"]["redis"] = "healthy"
    except Exception as e:
        health_status["checks"]["redis"] = "unhealthy"
        health_status["status"] = "degraded"
    
    # 依赖服务健康检查
    for service_name, service_url in DEPENDENT_SERVICES.items():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{service_url}/health", timeout=5)
                if response.status_code == 200:
                    health_status["checks"][service_name] = "healthy"
                else:
                    health_status["checks"][service_name] = "unhealthy"
                    health_status["status"] = "degraded"
        except Exception:
            health_status["checks"][service_name] = "unreachable"
            health_status["status"] = "unhealthy"
    
    return health_status

@app.get("/health/live")
async def liveness_check():
    """存活检查（Kubernetes）"""
    return {"status": "alive"}

@app.get("/health/ready")  
async def readiness_check():
    """就绪检查（Kubernetes）"""
    # 检查关键依赖是否就绪
    if await check_database_ready() and await check_redis_ready():
        return {"status": "ready"}
    else:
        raise HTTPException(503, "Service not ready")
```

### 10.4. 性能优化

#### 数据库优化
```sql
-- 查询优化示例
-- ✅ 正确：使用索引和分页
SELECT u.id, u.email, u.username, r.name as role_name
FROM users u
JOIN roles r ON u.role_id = r.id
WHERE u.tenant_id = $1 
  AND u.is_active = true
  AND u.created_at >= $2
ORDER BY u.created_at DESC
LIMIT $3 OFFSET $4;

-- 创建复合索引
CREATE INDEX idx_users_tenant_active_created 
ON users(tenant_id, is_active, created_at DESC);
```

#### 缓存策略
```python
import redis
from functools import wraps

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def cache_result(expire_seconds: int = 300):
    """结果缓存装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # 尝试从缓存获取
            cached_result = redis_client.get(cache_key)
            if cached_result:
                return json.loads(cached_result)
            
            # 执行函数并缓存结果
            result = await func(*args, **kwargs)
            redis_client.setex(
                cache_key, 
                expire_seconds, 
                json.dumps(result, default=str)
            )
            
            return result
        return wrapper
    return decorator

# 使用示例
@cache_result(expire_seconds=600)
async def get_user_permissions(user_id: str) -> List[str]:
    # 耗时的权限查询
    pass
```

---

## 11. 部署与运维规范 (Deployment & Operations Standards)

### 11.1. 容器化规范

#### Dockerfile最佳实践
```dockerfile
# Python服务Dockerfile示例
FROM python:3.11-slim as builder

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 生产阶段
FROM python:3.11-slim

WORKDIR /app

# 创建非root用户
RUN groupadd -r lyss && useradd -r -g lyss lyss

# 从builder阶段复制依赖
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# 复制应用代码
COPY . .

# 设置权限
RUN chown -R lyss:lyss /app

# 切换到非root用户
USER lyss

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Go服务Dockerfile示例
```dockerfile
# Go服务Dockerfile示例
FROM golang:1.21-alpine AS builder

WORKDIR /app

# 复制go mod文件
COPY go.mod go.sum ./
RUN go mod download

# 复制源代码
COPY . .

# 构建应用
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o main ./cmd/server

# 生产阶段
FROM alpine:latest

# 安装ca证书
RUN apk --no-cache add ca-certificates

WORKDIR /root/

# 从builder阶段复制可执行文件
COPY --from=builder /app/main .

# 创建非root用户
RUN adduser -D -s /bin/sh lyss

# 切换到非root用户
USER lyss

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:8003/health || exit 1

# 暴露端口
EXPOSE 8003

# 启动命令
CMD ["./main"]
```

### 11.2. Docker Compose配置

#### 开发环境Docker Compose
```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: lyss_platform
      POSTGRES_USER: lyss_user
      POSTGRES_PASSWORD: dev_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./sql/init.sql:/docker-entrypoint-initdb.d/init.sql

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --requirepass dev_password

  api-gateway:
    build: 
      context: ./services/gateway
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
    environment:
      - API_GATEWAY_SECRET_KEY=dev-jwt-key
      - DB_HOST=postgres
      - REDIS_HOST=redis
    depends_on:
      - postgres
      - redis
    volumes:
      - ./services/gateway:/app
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  auth-service:
    build:
      context: ./services/auth
      dockerfile: Dockerfile.dev
    ports:
      - "8001:8001"
    environment:
      - AUTH_SERVICE_SECRET_KEY=dev-jwt-key
      - DB_HOST=postgres
    depends_on:
      - postgres
    volumes:
      - ./services/auth:/app

volumes:
  postgres_data:
```

### 11.3. Kubernetes部署

#### Deployment配置示例
```yaml
# k8s/auth-service-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lyss-auth-service
  namespace: lyss-platform
  labels:
    app: lyss-auth-service
    version: v1.0.0
spec:
  replicas: 3
  selector:
    matchLabels:
      app: lyss-auth-service
  template:
    metadata:
      labels:
        app: lyss-auth-service
        version: v1.0.0
    spec:
      containers:
      - name: auth-service
        image: lyss/auth-service:v1.0.0
        ports:
        - containerPort: 8001
        env:
        - name: AUTH_SERVICE_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: lyss-secrets
              key: jwt-secret-key
        - name: DB_HOST
          value: "postgres-service"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8001
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8001
          initialDelaySeconds: 5
          periodSeconds: 5
```

#### Service配置示例
```yaml
# k8s/auth-service-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: lyss-auth-service
  namespace: lyss-platform
spec:
  selector:
    app: lyss-auth-service
  ports:
  - port: 8001
    targetPort: 8001
  type: ClusterIP
```

### 11.4. 监控和日志收集

#### Prometheus监控配置
```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'lyss-api-gateway'
    static_configs:
      - targets: ['api-gateway:8000']
    metrics_path: /metrics

  - job_name: 'lyss-auth-service'
    static_configs:
      - targets: ['auth-service:8001']
    metrics_path: /metrics

  - job_name: 'lyss-eino-service'
    static_configs:
      - targets: ['eino-service:8003']
    metrics_path: /metrics
```

#### 日志收集配置
```yaml
# logging/fluentd.conf
<source>
  @type forward
  port 24224
  bind 0.0.0.0
</source>

<filter lyss.**>
  @type parser
  key_name log
  <parse>
    @type json
  </parse>
</filter>

<match lyss.**>
  @type elasticsearch
  host elasticsearch
  port 9200
  index_name lyss-logs
  type_name _doc
</match>
```

---

## 12. 文档规范 (Documentation Standards)

### 12.1. 文档分类

#### 文档类型和用途
```
docs/
├── README.md              # 项目概述和快速开始
├── STANDARDS.md           # 开发规范（本文档）
├── API.md                 # API接口文档
├── DEPLOYMENT.md          # 部署指南
├── TROUBLESHOOTING.md     # 故障排查指南
├── CONTRIBUTING.md        # 贡献指南
├── services/              # 服务文档
│   ├── api_gateway.md
│   ├── auth_service.md
│   ├── tenant_service.md
│   ├── eino_service.md
│   └── memory_service.md
└── architecture/          # 架构文档
    ├── overview.md
    ├── database_design.md
    └── security_model.md
```

### 12.2. 文档编写规范

#### Markdown格式规范
```markdown
# 一级标题（页面主标题）

## 二级标题（主要章节）

### 三级标题（子章节）

#### 四级标题（详细说明）

**强调文本**
*斜体文本*
`代码片段`

```语言名称
代码块
```

> 重要提示或引用

- 列表项1
- 列表项2

1. 有序列表项1
2. 有序列表项2

[链接文本](URL)

![图片描述](图片URL)
```

#### API文档模板
```markdown
## POST /api/v1/auth/token

### 描述
用户登录认证接口，验证用户凭证并返回JWT令牌。

### 请求参数

| 参数名 | 类型 | 必需 | 描述 |
|--------|------|------|------|
| username | string | 是 | 用户名或邮箱 |
| password | string | 是 | 用户密码 |

### 请求示例
```http
POST /api/v1/auth/token
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=userpassword
```

### 响应示例

#### 成功响应 (200)
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 1800
  },
  "request_id": "req-20250710143025-a1b2c3d4",
  "timestamp": "2025-07-10T10:30:00Z"
}
```

#### 错误响应 (401)
```json
{
  "success": false,
  "error": {
    "code": "2006",
    "message": "用户名或密码错误"
  },
  "request_id": "req-20250710143025-a1b2c3d4",
  "timestamp": "2025-07-10T10:30:00Z"
}
```

### 错误代码
- `2001`: 未认证
- `2006`: 密码错误
- `1001`: 输入参数无效
```

### 12.3. 代码注释规范

#### Python注释规范
```python
class UserService:
    """用户服务类
    
    负责用户的创建、更新、查询和删除操作。
    支持多租户数据隔离和权限控制。
    
    Attributes:
        db_session: 数据库会话
        cache_manager: 缓存管理器
    """
    
    def __init__(self, db_session: AsyncSession, cache_manager: CacheManager):
        """初始化用户服务
        
        Args:
            db_session: 异步数据库会话
            cache_manager: Redis缓存管理器
        """
        self.db_session = db_session
        self.cache_manager = cache_manager
    
    async def create_user(self, user_data: CreateUserRequest, tenant_id: str) -> User:
        """创建新用户
        
        在指定租户下创建新用户，包括密码哈希、邮箱验证等处理。
        
        Args:
            user_data: 用户创建请求数据
            tenant_id: 租户ID，用于多租户隔离
            
        Returns:
            User: 创建成功的用户对象
            
        Raises:
            UserAlreadyExistsError: 当用户邮箱已存在时
            ValidationError: 当输入数据验证失败时
            
        Example:
            ```python
            user_service = UserService(db_session, cache_manager)
            user_data = CreateUserRequest(
                email="user@example.com",
                password="securepassword"
            )
            new_user = await user_service.create_user(user_data, tenant_id)
            ```
        """
        # 检查用户是否已存在
        existing_user = await self._get_user_by_email(user_data.email, tenant_id)
        if existing_user:
            raise UserAlreadyExistsError(f"用户邮箱已存在: {user_data.email}")
        
        # 创建用户逻辑...
```

#### Go注释规范
```go
// UserService 用户服务结构体
// 负责用户的创建、更新、查询和删除操作
// 支持多租户数据隔离和权限控制
type UserService struct {
    db    *sql.DB
    cache *redis.Client
}

// NewUserService 创建新的用户服务实例
// 
// 参数:
//   db: 数据库连接
//   cache: Redis缓存连接
//
// 返回:
//   *UserService: 用户服务实例
func NewUserService(db *sql.DB, cache *redis.Client) *UserService {
    return &UserService{
        db:    db,
        cache: cache,
    }
}

// CreateUser 创建新用户
//
// 在指定租户下创建新用户，包括密码哈希、邮箱验证等处理。
//
// 参数:
//   ctx: 上下文，用于超时控制和取消操作
//   userData: 用户创建请求数据
//   tenantID: 租户ID，用于多租户隔离
//
// 返回:
//   *User: 创建成功的用户对象
//   error: 错误信息，如果操作失败
//
// 错误类型:
//   ErrUserAlreadyExists: 当用户邮箱已存在时
//   ErrValidationFailed: 当输入数据验证失败时
//
// 示例:
//   userService := NewUserService(db, cache)
//   userData := &CreateUserRequest{
//       Email:    "user@example.com",
//       Password: "securepassword",
//   }
//   newUser, err := userService.CreateUser(ctx, userData, tenantID)
//   if err != nil {
//       return err
//   }
func (s *UserService) CreateUser(ctx context.Context, userData *CreateUserRequest, tenantID string) (*User, error) {
    // 检查用户是否已存在
    existingUser, err := s.getUserByEmail(ctx, userData.Email, tenantID)
    if err != nil && !errors.Is(err, ErrUserNotFound) {
        return nil, fmt.Errorf("检查用户存在性失败: %w", err)
    }
    
    if existingUser != nil {
        return nil, ErrUserAlreadyExists
    }
    
    // 创建用户逻辑...
}
```

### 12.4. 文档更新流程

#### 文档版本控制
- 文档变更必须与代码变更同步提交
- 重要文档变更需要代码审查
- API文档自动生成（使用OpenAPI/Swagger）
- 定期检查文档的准确性和完整性

#### 文档审查检查清单
```markdown
## 文档审查检查清单

### 内容准确性
- [ ] 文档内容与实际代码实现一致
- [ ] API示例可以正常运行
- [ ] 错误代码和错误信息正确
- [ ] 配置参数和环境变量准确

### 完整性
- [ ] 包含所有必需的章节
- [ ] API文档覆盖所有公开接口
- [ ] 包含错误处理说明
- [ ] 包含配置和部署说明

### 可读性
- [ ] 使用清晰的中文表达
- [ ] 代码示例格式正确
- [ ] 章节结构逻辑清晰
- [ ] 包含必要的图表和示意图

### 维护性
- [ ] 使用标准的Markdown格式
- [ ] 链接有效且指向正确位置
- [ ] 版本信息及时更新
- [ ] 包含文档的更新历史
```

---

## 结语

本规范文档是 Lyss AI Platform 项目的技术基石，所有团队成员都必须严格遵循。规范的执行将直接影响项目的代码质量、开发效率和维护成本。

### 规范执行
- 所有代码提交都必须通过规范检查
- 定期进行代码审查和规范合规性检查
- 持续完善和更新规范内容

### 规范更新
- 规范文档本身也需要版本控制
- 重大规范变更需要团队讨论和批准
- 及时根据项目发展调整和优化规范

### 联系方式
如有规范相关问题或建议，请通过以下方式联系：
- 项目Issue: 提交到项目GitHub仓库
- 团队讨论: 在团队会议中讨论
- 文档更新: 通过Pull Request提交规范改进

---
