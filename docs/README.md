# Lyss AI Platform - 企业级AI服务聚合与管理平台

## 🎯 项目简介

Lyss 是一个面向企业的AI服务聚合与管理平台，提供统一的AI模型接入、编排和治理能力。平台基于微服务架构，严格遵循多租户数据隔离和安全第一原则。

## 🏗️ 系统架构总览

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Frontend (React + Ant Design X)              │
│                          http://localhost:3000                      │
└─────────────────────────┬───────────────────────────────────────────┘
                          │ HTTPS/WSS
                          │
┌─────────────────────────▼───────────────────────────────────────────┐
│                     API Gateway (FastAPI)                          │
│                      http://localhost:8000                         │
│  职责: 统一入口、认证委托、请求路由、分布式追踪                        │
└─────┬─────────┬─────────┬─────────┬─────────┬─────────┬─────────────┘
      │         │         │         │         │         │
      │ /auth/* │ /admin/*│ /chat/* │ /memory/*│         │
      │         │         │         │         │         │
      ▼         ▼         ▼         ▼         ▼         ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│  Auth   │ │ Tenant  │ │  EINO   │ │ Memory  │ │  Redis  │ │ PostgreSQL│
│ Service │ │ Service │ │ Service │ │ Service │ │ (Cache) │ │   (DB)    │
│  :8001  │ │  :8002  │ │  :8003  │ │  :8004  │ │  :6379  │ │   :5432   │
│(FastAPI)│ │(FastAPI)│ │   (Go)  │ │(FastAPI)│ │         │ │           │
└─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘
                          │                       │
                          │ AI工作流编排           │ Mem0AI
                          ▼                       ▼ 后端存储
                    ┌─────────────┐         ┌─────────────┐
                    │ AI Providers│         │   Vector    │
                    │ OpenAI/     │         │   Storage   │
                    │ Anthropic/  │         │             │
                    │ Google      │         │             │
                    └─────────────┘         └─────────────┘
```

## ⚡ 开发黄金法则

### 1. 🔒 安全第一原则
- **多租户数据隔离**: 所有操作必须包含tenant_id验证
- **凭证加密存储**: API密钥使用pgcrypto列级加密
- **请求追踪**: 每个请求必须携带X-Request-ID进行全链路追踪

### 2. 📋 服务职责边界
- **API Gateway**: 唯一公开入口，负责认证委托和路由分发，**无业务逻辑**
- **Auth Service**: 专门负责JWT签发和刷新，**不处理业务数据**
- **Tenant Service**: 管理租户、用户、角色和供应商凭证，**拥有用户数据**
- **EINO Service**: AI工作流编排，**拥有执行状态数据**
- **Memory Service**: 封装Mem0AI，**拥有记忆数据**

### 3. 🔗 服务间通信规范
- **认证传递**: JWT中的tenant_id和user_id通过请求头传递
- **追踪传递**: X-Request-ID在所有服务间传递
- **错误处理**: 统一JSON错误响应格式
- **日志标准**: 所有日志必须包含request_id和tenant_id

### 4. 📊 数据所有权原则
- **每个服务拥有自己的数据库/表**
- **服务间不得直接访问其他服务的数据**
- **跨服务数据查询必须通过API调用**

## 📚 服务文档链接

| 服务名称 | 端口 | 技术栈 | 规范文档 | 职责描述 |
|---------|-----|--------|----------|----------|
| API Gateway | 8000 | FastAPI | [api_gateway.md](./api_gateway.md) | 统一入口、认证委托、请求路由 |
| Auth Service | 8001 | FastAPI | [auth_service.md](./auth_service.md) | JWT认证、用户登录、令牌管理 |
| Tenant Service | 8002 | FastAPI | [tenant_service.md](./tenant_service.md) | 租户管理、用户管理、凭证管理 |
| EINO Service | 8003 | Go | [eino_service.md](./eino_service.md) | AI工作流编排、模型调用编排 |
| Memory Service | 8004 | FastAPI | [memory_service.md](./memory_service.md) | 对话记忆、上下文管理 |

## 🚀 开发环境启动说明

### 前置要求
- Docker & Docker Compose
- Python 3.11+
- Go 1.21+
- Node.js 18+

### 快速启动

#### 1. 启动基础设施
```bash
# 启动数据库和缓存
docker-compose up -d postgres redis

# 等待服务就绪
sleep 10
```

#### 2. 初始化数据库
```bash
# 创建pgcrypto扩展
psql -h localhost -U lyss_user -d lyss_platform -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;"

# 运行初始化脚本
python scripts/init_database.py
```

#### 3. 启动微服务 (并行启动)
```bash
# 启动Auth Service
cd services/auth && uvicorn main:app --host 0.0.0.0 --port 8001 --reload &

# 启动Tenant Service  
cd services/tenant && uvicorn main:app --host 0.0.0.0 --port 8002 --reload &

# 启动EINO Service
cd services/eino && go run cmd/server/main.go &

# 启动Memory Service
cd services/memory && uvicorn main:app --host 0.0.0.0 --port 8004 --reload &

# 启动API Gateway (最后启动)
cd services/gateway && uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
```

#### 4. 启动前端
```bash
cd frontend
npm install
npm run dev
```

### 健康检查
```bash
# 检查所有服务状态
curl http://localhost:8000/health  # API Gateway
curl http://localhost:8001/health  # Auth Service  
curl http://localhost:8002/health  # Tenant Service
curl http://localhost:8003/health  # EINO Service
curl http://localhost:8004/health  # Memory Service
```

## 🛡️ 安全配置要点

### 环境变量配置
```bash
# JWT配置
SECRET_KEY="至少32字符的强密钥"
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_USERNAME=lyss_user
DB_PASSWORD=强密码
DB_DATABASE=lyss_platform

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=强密码

# pgcrypto加密密钥
PGCRYPTO_KEY="用于API密钥加密的强密钥"

# Mem0AI后台配置
MEM0_LLM_PROVIDER=openai
MEM0_EMBEDDING_MODEL=text-embedding-ada-002
MEM0_OPENAI_API_KEY="后台记忆系统专用"
```

### ⚠️ 关键安全提醒
1. **绝不在代码中硬编码密钥**
2. **生产环境使用KMS管理pgcrypto密钥**
3. **所有服务间通信使用HTTPS**
4. **定期轮换JWT签名密钥**

## 📋 开发检查清单

### 新功能开发前必读
- [ ] 阅读对应服务的规范文档
- [ ] 确认数据所有权和API边界
- [ ] 理解多租户隔离要求
- [ ] 了解日志和追踪规范

### 代码提交前检查
- [ ] 所有数据库查询包含tenant_id过滤
- [ ] API响应包含request_id
- [ ] 日志记录包含必要的上下文信息
- [ ] 错误处理符合统一格式
- [ ] 通过所有单元测试和集成测试

## 📞 问题排查

### 常见问题
1. **服务启动失败**: 检查端口占用和环境变量配置
2. **认证失败**: 验证JWT密钥配置和服务间通信
3. **数据隔离问题**: 检查tenant_id的传递和过滤
4. **性能问题**: 查看Redis缓存配置和数据库连接池

### 日志查看
```bash
# 查看特定请求的全链路日志
grep "request_id:xxx" logs/*.log

# 查看特定租户的操作日志  
grep "tenant_id:xxx" logs/*.log
```

---

**⚠️ 重要提醒**: 本平台涉及多租户数据和AI供应商凭证，任何代码变更都必须经过严格的安全审查。开发过程中如有疑问，请参考对应服务的规范文档或联系架构团队。