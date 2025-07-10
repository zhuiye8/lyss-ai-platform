# API Gateway Service 规范文档

## 🎯 服务概述

API Gateway 是整个 Lyss AI Platform 的**唯一公开入口**，负责统一的请求路由、认证委托和分布式追踪。本服务**不包含任何业务逻辑**，纯粹作为智能代理层存在。

## 📋 核心职责

### ✅ 负责的功能
1. **统一入口管理**: 作为所有客户端请求的唯一接入点
2. **认证委托**: 验证JWT令牌并提取用户身份信息
3. **请求路由**: 根据API路径将请求转发到对应的微服务
4. **分布式追踪**: 生成和传递X-Request-ID，实现全链路追踪
5. **请求/响应标准化**: 确保统一的API格式和错误处理
6. **CORS和安全头管理**: 处理跨域请求和安全策略

### ❌ 不负责的功能
- 任何业务数据的存储和处理
- 用户认证逻辑的实现（仅验证JWT）
- AI工作流的执行和管理
- 供应商凭证的管理和加密

## 🛣️ API路由规则

### 路由映射表

| 路径前缀 | 目标服务 | 端口 | 描述 | 是否需要认证 |
|---------|---------|------|------|-------------|
| `/api/v1/auth/*` | Auth Service | 8001 | 用户认证、JWT管理 | ❌ |
| `/api/v1/admin/*` | Tenant Service | 8002 | 租户和用户管理 | ✅ |
| `/api/v1/chat/*` | EINO Service | 8003 | AI对话和工作流 | ✅ |
| `/api/v1/memory/*` | Memory Service | 8004 | 对话记忆管理 | ✅ |
| `/health` | API Gateway | 8000 | 健康检查 | ❌ |

### 路由实现逻辑
```python
# 路由规则配置
ROUTE_CONFIG = {
    "/api/v1/auth": {
        "target": "http://localhost:8001",
        "require_auth": False,
        "service_name": "auth_service"
    },
    "/api/v1/admin": {
        "target": "http://localhost:8002", 
        "require_auth": True,
        "service_name": "tenant_service"
    },
    "/api/v1/chat": {
        "target": "http://localhost:8003",
        "require_auth": True,
        "service_name": "eino_service"
    },
    "/api/v1/memory": {
        "target": "http://localhost:8004",
        "require_auth": True,
        "service_name": "memory_service"
    }
}
```

## 🔐 认证和授权机制

### JWT验证流程
1. **提取JWT**: 从`Authorization: Bearer <token>`头部提取JWT
2. **验证签名**: 使用`SECRET_KEY`验证JWT签名有效性
3. **提取身份**: 从JWT payload中提取`user_id`、`tenant_id`、`role`
4. **注入头部**: 将身份信息注入到下游请求头中

### JWT Payload 结构
```json
{
  "user_id": "uuid",
  "tenant_id": "uuid", 
  "role": "end_user|tenant_admin|super_admin",
  "email": "user@example.com",
  "exp": 1234567890,
  "iat": 1234567890
}
```

### 认证头部注入
经过认证后，API Gateway会向下游服务注入以下头部：
```http
X-User-ID: {user_id}
X-Tenant-ID: {tenant_id}
X-User-Role: {role}
X-Request-ID: {生成的唯一追踪ID}
Authorization: Bearer {原始JWT}
```

## 🔍 分布式追踪机制

### X-Request-ID 生成规则
```python
import uuid
from datetime import datetime

def generate_request_id() -> str:
    """生成唯一的请求追踪ID"""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"req-{timestamp}-{unique_id}"
    
# 示例: req-20250710143025-a1b2c3d4
```

### 追踪头部传递
- **入口处理**: 为每个外部请求生成`X-Request-ID`
- **下游传递**: 所有转发请求必须携带此ID
- **日志关联**: 所有日志记录必须包含此ID用于链路追踪

## 📡 对外API接口

### 健康检查
```http
GET /health
```

**响应格式:**
```json
{
  "status": "healthy",
  "timestamp": "2025-07-10T10:30:00Z",
  "version": "1.0.0",
  "services": {
    "auth_service": "healthy",
    "tenant_service": "healthy", 
    "eino_service": "healthy",
    "memory_service": "healthy"
  }
}
```

### 通用代理接口
所有其他接口都是透明代理，API Gateway不改变请求和响应的业务内容，只添加认证和追踪信息。

## 🔧 核心技术实现

### 依赖组件
```python
# requirements.txt
fastapi==0.104.1
uvicorn==0.24.0
python-jose[cryptography]==3.3.0
httpx==0.25.0
pydantic==2.5.0
```

### 中间件栈
```python
# 中间件执行顺序（从外到内）
app.add_middleware(CORSMiddleware)           # CORS处理
app.add_middleware(RequestTracingMiddleware) # 生成X-Request-ID  
app.add_middleware(AuthMiddleware)           # JWT验证和身份注入
app.add_middleware(ProxyMiddleware)          # 请求转发
```

### 核心配置项
```python
# 环境变量配置
SECRET_KEY: str = "JWT签名密钥"
CORS_ORIGINS: List[str] = ["http://localhost:3000"]  
REQUEST_TIMEOUT: int = 30
MAX_REQUEST_SIZE: int = 10 * 1024 * 1024  # 10MB

# 服务发现配置
SERVICE_REGISTRY = {
    "auth_service": "http://localhost:8001",
    "tenant_service": "http://localhost:8002",
    "eino_service": "http://localhost:8003", 
    "memory_service": "http://localhost:8004"
}
```

## 📊 错误处理规范

### 统一错误响应格式
```json
{
  "success": false,
  "message": "错误描述信息",
  "error_code": "SPECIFIC_ERROR_CODE",
  "request_id": "req-20250710143025-a1b2c3d4",
  "timestamp": "2025-07-10T10:30:00Z",
  "details": {
    "field": "具体错误字段",
    "reason": "详细错误原因"
  }
}
```

### 常见错误代码
| 错误代码 | HTTP状态码 | 描述 |
|---------|-----------|------|
| `AUTH_TOKEN_MISSING` | 401 | 缺少认证令牌 |
| `AUTH_TOKEN_INVALID` | 401 | 无效的认证令牌 |
| `AUTH_TOKEN_EXPIRED` | 401 | 认证令牌已过期 |
| `INSUFFICIENT_PERMISSIONS` | 403 | 权限不足 |
| `SERVICE_UNAVAILABLE` | 503 | 下游服务不可用 |
| `REQUEST_TIMEOUT` | 504 | 请求超时 |

## 📝 日志规范

### 日志格式
```json
{
  "timestamp": "2025-07-10T10:30:00Z",
  "level": "INFO",
  "service": "api_gateway",
  "request_id": "req-20250710143025-a1b2c3d4",
  "user_id": "user-uuid",
  "tenant_id": "tenant-uuid", 
  "method": "POST",
  "path": "/api/v1/chat/stream",
  "target_service": "eino_service",
  "status_code": 200,
  "duration_ms": 1250,
  "message": "Request forwarded successfully"
}
```

### 必须记录的事件
- 所有进入的外部请求
- JWT验证结果（成功/失败）
- 服务转发操作
- 下游服务错误
- 认证和授权失败

## 🔒 安全配置

### CORS配置
```python
CORS_CONFIG = {
    "allow_origins": ["http://localhost:3000"],
    "allow_credentials": True,
    "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allow_headers": ["*"],
    "expose_headers": ["X-Request-ID"]
}
```

### 安全头部
```python
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY", 
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
}
```

## 🚀 部署和运行

### 启动命令
```bash
cd services/gateway
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker配置
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 健康检查配置
```bash
# Docker健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

## ⚠️ 关键约束和限制

### 强制约束
1. **纯代理职责**: 禁止在此服务中实现任何业务逻辑
2. **无状态设计**: 不得存储任何会话或业务状态
3. **认证委托**: 只验证JWT，不实现认证逻辑
4. **追踪传递**: 必须为每个请求生成和传递X-Request-ID

### 性能要求
- **响应时间**: P95延迟 < 50ms（不包括下游服务时间）
- **并发处理**: 支持5000并发连接
- **超时设置**: 下游服务调用超时30秒

### 监控指标
- 请求总数和成功率
- 各路由的响应时间分布
- JWT验证成功/失败统计
- 下游服务健康状态
- 错误码分布统计

---

**🔥 重要提醒**: API Gateway作为整个平台的入口，其稳定性和安全性至关重要。任何修改都必须经过充分测试，确保不影响现有的认证和路由机制。