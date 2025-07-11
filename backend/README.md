# Lyss AI Platform - API Gateway

## 📋 概述

API Gateway 是 Lyss AI Platform 的**统一入口**，负责：

- 🔐 **统一认证**: JWT令牌验证和用户身份管理
- 🛣️ **智能路由**: 请求转发到对应的微服务
- 📊 **分布式追踪**: 全链路请求追踪和监控
- 🔒 **安全防护**: CORS、安全头、速率限制
- 📝 **统一日志**: 结构化JSON日志记录

## 🚀 快速启动

### 环境要求

- Python 3.11+
- 依赖的微服务：Auth Service (8001), Tenant Service (8002)

### 安装依赖

```bash
# 进入项目目录
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 配置环境

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量
nano .env
```

### 启动服务

```bash
# 使用开发脚本启动（推荐）
python scripts/start_dev.py

# 或直接使用uvicorn
uvicorn api_gateway.main:app --reload --host 0.0.0.0 --port 8000
```

## 🔧 配置说明

### 核心配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `API_GATEWAY_HOST` | `0.0.0.0` | 监听地址 |
| `API_GATEWAY_PORT` | `8000` | 监听端口 |
| `API_GATEWAY_DEBUG` | `true` | 调试模式 |
| `API_GATEWAY_SECRET_KEY` | - | JWT签名密钥（必须32字符以上） |

### 服务注册

| 服务 | 环境变量 | 默认地址 |
|------|----------|----------|
| Auth Service | `AUTH_SERVICE_URL` | `http://localhost:8001` |
| Tenant Service | `TENANT_SERVICE_URL` | `http://localhost:8002` |
| EINO Service | `EINO_SERVICE_URL` | `http://localhost:8003` |
| Memory Service | `MEMORY_SERVICE_URL` | `http://localhost:8004` |

### CORS配置

```env
API_GATEWAY_CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]
API_GATEWAY_CORS_ALLOW_CREDENTIALS=true
```

## 📡 API路由

### 路由映射

| 路径前缀 | 目标服务 | 认证要求 | 说明 |
|----------|----------|----------|------|
| `/api/v1/auth/*` | Auth Service | ❌ | 用户认证、JWT管理 |
| `/api/v1/admin/*` | Tenant Service | ✅ | 租户和用户管理 |
| `/api/v1/chat/*` | EINO Service | ✅ | AI对话和工作流 |
| `/api/v1/memory/*` | Memory Service | ✅ | 对话记忆管理 |
| `/health` | API Gateway | ❌ | 健康检查 |

### 认证头部注入

经过认证的请求会自动注入以下头部到下游服务：

```http
X-User-ID: {user_id}
X-Tenant-ID: {tenant_id}
X-User-Role: {role}
X-Request-ID: {唯一追踪ID}
Authorization: Bearer {原始JWT}
```

## 🔍 监控和调试

### 健康检查

```bash
# 检查API Gateway
curl http://localhost:8000/health

# 检查所有服务
curl http://localhost:8000/health/services

# 使用脚本检查
python scripts/health_check.py
```

### 日志查看

API Gateway使用结构化JSON日志：

```json
{
  "timestamp": "2025-07-11T10:30:00.123Z",
  "level": "INFO",
  "service": "lyss-api-gateway",
  "request_id": "req-20250711103000-a1b2c3d4",
  "message": "请求完成: POST /api/v1/chat/stream -> 200",
  "method": "POST",
  "path": "/api/v1/chat/stream",
  "status_code": 200,
  "duration_ms": 1250,
  "user_id": "user-uuid",
  "tenant_id": "tenant-uuid"
}
```

## 🛡️ 安全特性

### JWT认证

- 支持HS256算法
- 自动验证令牌有效性和过期时间
- 提取用户身份信息并注入到请求头

### 速率限制

- 基于IP和用户的双重限制
- 默认每分钟100个请求
- 可配置的时间窗口和限制数量

### 安全头部

自动添加以下安全头部：

```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

## 📊 错误处理

### 统一错误格式

所有错误响应都遵循统一格式：

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
  "request_id": "req-20250711103000-a1b2c3d4",
  "timestamp": "2025-07-11T10:30:00Z"
}
```

### 错误代码

| 错误代码 | HTTP状态码 | 描述 |
|----------|-----------|------|
| `2001` | 401 | 认证失败 |
| `2002` | 401 | 令牌过期 |
| `2003` | 401 | 令牌无效 |
| `2004` | 403 | 权限不足 |
| `5004` | 503 | 服务不可用 |

## 🧪 测试

### 启动测试

```bash
# 运行所有测试
pytest tests/

# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 生成覆盖率报告
pytest --cov=api_gateway --cov-report=html
```

### 手动测试

```bash
# 测试健康检查
curl -X GET http://localhost:8000/health

# 测试认证路由（无需认证）
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password"}'

# 测试需要认证的路由
curl -X GET http://localhost:8000/api/v1/admin/users \
  -H "Authorization: Bearer your-jwt-token"
```

## 🔧 开发

### 项目结构

```
backend/
├── api_gateway/           # 主应用包
│   ├── core/             # 核心组件
│   ├── middleware/       # 中间件
│   ├── routers/          # 路由处理器
│   ├── services/         # 服务客户端
│   ├── utils/            # 工具函数
│   └── main.py           # 应用入口
├── scripts/              # 运维脚本
├── tests/                # 测试文件
└── requirements.txt      # 依赖管理
```

### 开发规范

- 使用中文注释
- 遵循PEP 8代码风格
- 使用类型提示
- 编写单元测试
- 结构化日志记录

## 📚 相关文档

- [API Gateway规范](../docs/api_gateway.md)
- [开发规范总纲](../docs/STANDARDS.md)
- [项目结构规范](../docs/PROJECT_STRUCTURE.md)

## 🚨 故障排除

### 常见问题

1. **服务启动失败**
   - 检查端口是否被占用
   - 确认环境变量配置正确
   - 查看日志输出

2. **下游服务连接失败**
   - 确认下游服务已启动
   - 检查服务地址配置
   - 验证网络连接

3. **JWT验证失败**
   - 检查SECRET_KEY配置
   - 确认令牌格式正确
   - 验证令牌是否过期

### 日志调试

```bash
# 启用调试日志
export API_GATEWAY_LOG_LEVEL=DEBUG

# 查看详细错误
python scripts/start_dev.py --host 0.0.0.0 --port 8000
```

## 🎯 性能优化

- 使用连接池复用HTTP连接
- 实现响应缓存
- 异步处理所有I/O操作
- 适当的超时设置

## 📋 待办事项

- [ ] 添加Prometheus监控指标
- [ ] 实现API限流配置
- [ ] 添加更多测试用例
- [ ] 集成分布式追踪系统

---

**版本**: 1.0.0  
**更新时间**: 2025-07-11