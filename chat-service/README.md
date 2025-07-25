# Chat Service

Chat Service是Lyss AI Platform的对话管理核心服务，基于Go语言和EINO框架开发，提供实时对话、消息管理和多供应商AI模型集成能力。

## 🚀 功能特性

### 核心功能
- **实时对话**: 基于WebSocket的实时对话功能
- **多供应商支持**: 集成OpenAI、Anthropic、DeepSeek等多个AI供应商
- **流式响应**: 支持流式消息传输，提升用户体验
- **对话管理**: 完整的对话创建、查询、删除功能
- **消息持久化**: 可靠的消息存储和历史记录

### 技术特性
- **高性能**: 基于Go和Gin框架，支持高并发处理
- **EINO集成**: 使用EINO v0.3.52框架的供应商抽象层
- **多租户**: 完整的多租户数据隔离
- **JWT认证**: 与Auth Service集成的统一认证体系
- **统一数据库**: 与其他服务共享PostgreSQL数据库

## 📋 API 接口

### REST API

#### 对话管理
```bash
# 创建对话
POST /api/v1/conversations
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
    "title": "新对话",
    "model": "gpt-3.5-turbo",
    "provider": "openai"
}

# 获取对话列表
GET /api/v1/conversations?page=1&page_size=20
Authorization: Bearer <jwt_token>

# 获取对话详情
GET /api/v1/conversations/{id}
Authorization: Bearer <jwt_token>

# 删除对话
DELETE /api/v1/conversations/{id}
Authorization: Bearer <jwt_token>
```

#### 消息发送
```bash
# 同步发送消息
POST /api/v1/chat
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
    "conversation_id": "uuid",
    "message": "你好",
    "model": "gpt-3.5-turbo",
    "provider": "openai",
    "stream": false
}
```

### WebSocket API

#### 连接建立
```javascript
// 建立WebSocket连接
const ws = new WebSocket('ws://localhost:8004/ws/chat', ['Bearer', jwt_token]);

ws.onopen = function() {
    console.log('WebSocket连接已建立');
};
```

#### 消息格式
```javascript
// 发送聊天消息
ws.send(JSON.stringify({
    type: 'chat',
    data: {
        conversation_id: 'uuid',
        message: '你好',
        model: 'gpt-3.5-turbo',
        provider: 'openai',
        stream: true
    }
}));

// 接收响应消息
ws.onmessage = function(event) {
    const response = JSON.parse(event.data);
    if (response.type === 'stream') {
        console.log('流式响应:', response.data.delta);
    }
};
```

## 🛠️ 本地开发

### 环境要求
- Go 1.21+
- PostgreSQL 13+
- Redis 6+

### 快速启动

1. **启动基础设施**
```bash
# 启动Docker基础设施
cd /root/work/lyss-ai-platform
docker-compose up -d postgres redis

# 等待服务启动
sleep 15
```

2. **初始化数据库**
```bash
# 执行数据库迁移
psql -h localhost -p 5433 -U lyss -d lyss_db -f sql/03_chat_service_schema.sql
```

3. **配置环境变量**
```bash
# 复制环境配置文件
cd chat-service
cp .env.example .env

# 编辑配置（设置API密钥等）
nano .env
```

4. **安装依赖和启动服务**
```bash
# 安装Go依赖
go mod download
go mod tidy

# 启动服务
go run cmd/server/main.go
```

5. **验证服务**
```bash
# 健康检查
curl http://localhost:8004/health

# 预期响应
{
    "status": "healthy",
    "service": "chat-service",
    "version": "1.0.0",
    "timestamp": 1706025600,
    "checks": {
        "database": "connected",
        "eino": "initialized"
    }
}
```

### 开发工具

```bash
# 代码格式化
go fmt ./...

# 代码检查
go vet ./...

# 运行测试
go test ./...

# 构建应用
go build -o bin/chat-service cmd/server/main.go
```

## 🏗️ 架构设计

### 目录结构
```
chat-service/
├── cmd/server/          # 应用入口
├── configs/             # 配置管理
├── internal/
│   ├── handlers/        # HTTP和WebSocket处理器
│   ├── services/        # 业务逻辑服务
│   ├── models/          # 数据模型
│   └── middleware/      # 中间件
├── pkg/
│   ├── types/           # 公共类型定义
│   └── utils/           # 工具函数
├── docs/                # 文档
└── README.md
```

### 数据模型
- **chat_conversations**: 对话表，存储对话会话信息
- **chat_messages**: 消息表，存储对话中的具体消息

### 依赖服务
- **Auth Service**: 用户认证和JWT验证
- **Provider Service**: AI模型供应商管理（未来集成）
- **PostgreSQL**: 数据持久化
- **Redis**: 缓存和会话管理

## 🔧 配置说明

### 环境变量
```bash
# 服务器配置
SERVER_HOST=0.0.0.0          # 监听地址
SERVER_PORT=8004             # 监听端口
GIN_MODE=debug               # Gin模式

# 数据库配置
DB_HOST=localhost            # 数据库主机
DB_PORT=5433                 # 数据库端口
DB_USER=lyss                 # 数据库用户
DB_PASSWORD=test             # 数据库密码
DB_NAME=lyss_db              # 数据库名称

# EINO配置
EINO_DEFAULT_PROVIDER=openai # 默认供应商
OPENAI_API_KEY=sk-...        # OpenAI API密钥
ANTHROPIC_API_KEY=...        # Anthropic API密钥
DEEPSEEK_API_KEY=...         # DeepSeek API密钥
```

## 🧪 测试

### 单元测试
```bash
# 运行所有测试
go test ./...

# 运行特定包的测试
go test ./internal/services

# 带覆盖率的测试
go test -cover ./...
```

### 集成测试
```bash
# 使用curl测试API
curl -X POST http://localhost:8004/api/v1/chat \
  -H "Authorization: Bearer mock-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你好",
    "model": "gpt-3.5-turbo",
    "provider": "openai"
  }'
```

### WebSocket测试
可以使用浏览器开发者工具或WebSocket客户端工具测试实时对话功能。

## 📈 监控和日志

### 健康检查
- **健康检查**: `GET /health`
- **服务指标**: `GET /metrics`

### 日志格式
服务使用结构化JSON日志格式，便于日志收集和分析。

## 🚀 部署

### Docker部署
```bash
# 构建镜像
docker build -t chat-service .

# 运行容器
docker run -d \
  --name chat-service \
  -p 8004:8004 \
  --env-file .env \
  chat-service
```

### 生产配置
- 设置 `GIN_MODE=release`
- 配置实际的API密钥
- 启用HTTPS和安全中间件
- 配置日志收集和监控

## 🤝 开发贡献

1. 遵循Go编码规范
2. 添加适当的中文注释
3. 编写单元测试
4. 更新相关文档

## 📝 版本历史

- **v1.0.0**: 初始版本，基础对话功能
- 基于EINO v0.3.52框架
- 支持WebSocket实时通信
- 多供应商AI模型集成

## 📞 技术支持

如有问题，请查看项目文档或联系开发团队。