# EINO Service

Lyss AI Platform 的 AI 工作流编排核心服务，基于 Go 语言实现，提供高性能的 AI 模型调用和工作流管理。

## 🚀 功能特性

### 核心功能
- **智能凭证管理**: 支持多供应商凭证负载均衡和故障转移
- **工作流编排**: 基于 EINO 框架的复杂 AI 工作流支持
- **实时健康监控**: 凭证和服务的实时健康检查
- **流式响应**: 支持 Server-Sent Events 的实时响应
- **多租户支持**: 完整的租户隔离和权限控制

### 支持的工作流类型
- **Simple Chat**: 基础对话工作流
- **Optimized RAG**: 检索增强生成工作流
- **Tool Calling**: 工具调用工作流

### 支持的 AI 供应商
- OpenAI (GPT-4, GPT-3.5-turbo)
- Anthropic (Claude-3)
- DeepSeek (DeepSeek-Chat)
- Google AI (Gemini)
- Azure OpenAI

## 🏗️ 架构设计

```
eino-service/
├── cmd/server/          # 服务入口
├── internal/
│   ├── config/         # 配置管理
│   ├── models/         # 数据模型
│   ├── client/         # 外部服务客户端
│   ├── handlers/       # HTTP 处理器
│   ├── workflows/      # 工作流定义
│   └── services/       # 业务服务
├── pkg/
│   ├── credential/     # 凭证管理
│   └── health/         # 健康检查
└── config.yaml         # 配置文件
```

## 📦 安装和运行

### 前置要求
- Go 1.21+
- Redis (缓存和状态管理)
- PostgreSQL (工作流执行记录)
- Tenant Service (凭证管理)

### 编译和运行
```bash
# 下载依赖
go mod download

# 编译
go build -o eino-service cmd/server/main.go

# 运行
./eino-service -config config.yaml
```

### 使用 Docker
```bash
# 构建镜像
docker build -t lyss-eino-service .

# 运行容器
docker run -p 8003:8003 -v $(pwd)/config.yaml:/app/config.yaml lyss-eino-service
```

## 🔧 配置说明

### 核心配置项
- `server.port`: 服务端口 (默认: 8003)
- `services.tenant_service.base_url`: 租户服务地址
- `credential.cache_ttl`: 凭证缓存时间
- `credential.health_check_interval`: 健康检查间隔

### 环境变量
支持通过环境变量覆盖配置：
```bash
export EINO_SERVER_PORT=8003
export EINO_SERVICES_TENANT_SERVICE_BASE_URL=http://localhost:8002
export EINO_CREDENTIAL_CACHE_TTL=5m
```

## 📡 API 接口

### 聊天接口
```http
POST /api/v1/chat/simple
Content-Type: application/json
X-User-ID: {user_id}
X-Tenant-ID: {tenant_id}

{
  "message": "你好，请介绍一下机器学习",
  "model": "gpt-4",
  "temperature": 0.7,
  "max_tokens": 2048
}
```

### 流式聊天
```http
POST /api/v1/chat/stream
Content-Type: application/json
X-User-ID: {user_id}
X-Tenant-ID: {tenant_id}

{
  "message": "请详细解释深度学习的原理",
  "model": "deepseek-chat",
  "stream": true
}
```

### RAG 增强对话
```http
POST /api/v1/chat/rag
Content-Type: application/json
X-User-ID: {user_id}
X-Tenant-ID: {tenant_id}

{
  "query": "最新的 AI 技术发展趋势",
  "enable_web_search": true,
  "enable_memory": true
}
```

### 健康检查
```http
GET /health
```

## 🔍 监控和日志

### 健康检查指标
- `status`: 服务整体状态
- `dependencies`: 依赖服务状态
- `metrics`: 凭证和使用统计

### 日志格式
```json
{
  "level": "info",
  "msg": "简单聊天处理完成",
  "request_id": "req-1234567890",
  "user_id": "user-uuid",
  "tenant_id": "tenant-uuid",
  "execution_time": 1500,
  "credential_id": "cred-uuid",
  "provider": "openai",
  "timestamp": "2025-07-15T10:30:00Z"
}
```

## 🚨 故障排除

### 常见问题
1. **凭证获取失败**
   - 检查 Tenant Service 连接状态
   - 验证租户 ID 和凭证配置

2. **健康检查失败**
   - 检查 Redis 连接
   - 验证依赖服务状态

3. **工作流执行超时**
   - 检查凭证健康状态
   - 调整执行超时配置

### 调试模式
```bash
# 启用调试日志
export EINO_LOGGING_LEVEL=debug
./eino-service -config config.yaml
```

## 🔐 安全说明

### 凭证安全
- API 密钥通过加密存储和传输
- 凭证缓存自动过期和刷新
- 严格的租户隔离机制

### 访问控制
- 基于 JWT 的身份验证
- 租户级别的权限控制
- 请求追踪和审计日志

## 📊 性能指标

### 基准测试
- **并发处理能力**: 100 并发工作流
- **响应时间**: P95 < 2000ms (简单对话)
- **凭证切换**: < 10ms (缓存命中)
- **健康检查**: < 100ms

### 优化建议
- 合理配置凭证缓存时间
- 启用 Redis 持久化
- 监控凭证使用频率
- 定期清理执行历史

## 🤝 开发指南

### 添加新的工作流类型
1. 在 `internal/workflows/` 中定义工作流
2. 更新 `models/models.go` 中的类型定义
3. 在 `handlers/` 中添加对应的 API 处理器

### 添加新的供应商支持
1. 更新 `getProviderFromModel` 函数
2. 在 Tenant Service 中添加供应商配置
3. 测试凭证获取和健康检查

## 📝 版本历史

### v1.0.0
- 初始版本发布
- 支持基础聊天和 RAG 工作流
- 完整的凭证管理机制
- 健康检查和监控功能

---

🎯 **重要提醒**: 这是 Lyss AI Platform 的核心组件，请确保在生产环境中进行充分的测试和监控。