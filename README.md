# Lyss AI Platform - 企业级AI服务聚合与管理平台

## 🚀 快速开始

Lyss 是一个面向企业的AI服务聚合与管理平台，采用微服务架构实现多租户AI模型的统一接入、编排和治理。

### 📋 前置要求

- **Docker & Docker Compose** (用于基础设施)
- **Python 3.11+** (用于后端微服务)
- **Go 1.21+** (用于 EINO 工作流服务)  
- **Node.js 18+** (用于前端应用)

### ⚡ 一键启动

```bash
# 1. 克隆项目
git clone <repository-url>
cd lyss-ai-platform

# 2. 复制环境变量配置
cp .env.example .env

# 3. 启动基础设施服务 (数据库、缓存、向量存储)
docker-compose up -d

# 4. 等待服务启动完成
sleep 15

# 5. 验证基础设施服务
docker-compose ps
```

### 🏗️ 架构概览

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
│  Auth   │ │ Tenant  │ │  EINO   │ │ Memory  │ │  Redis  │ │PostgreSQL│
│ Service │ │ Service │ │ Service │ │ Service │ │ (Cache) │ │   (DB)    │
│  :8001  │ │  :8002  │ │  :8003  │ │  :8004  │ │  :6379  │ │   :5432   │
│(FastAPI)│ │(FastAPI)│ │   (Go)  │ │(FastAPI)│ │         │ │           │
└─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘
```

## 📊 基础设施服务说明

| 服务 | 端口 | 描述 | 健康检查 |
|-----|------|------|----------|
| PostgreSQL | 5432 | 主数据库，支持 pgcrypto 加密 | `pg_isready` |
| Redis | 6379 | 缓存和会话存储 | `redis-cli ping` |
| Qdrant | 6333 | 向量数据库 (Memory Service) | `curl /health` |
| MinIO | 9000/9001 | 对象存储 (可选) | `curl /minio/health/live` |

## 🔑 默认测试账户

开发环境已预置测试账户：

```
管理员账户:
  邮箱: admin@lyss.dev
  密码: admin123
  权限: 租户管理员

普通用户:
  邮箱: user@lyss.dev  
  密码: user123
  权限: 终端用户

租户: dev-tenant (开发测试租户)
```

## 🛠️ 开发指南

### 启动微服务 (本地开发)

每个微服务需要单独启动，推荐使用多个终端窗口：

```bash
# 终端 1 - Auth Service (认证服务)
cd auth-service
pip install -r requirements.txt
uvicorn auth_service.main:app --host 0.0.0.0 --port 8001 --reload

# 终端 2 - Tenant Service (租户管理服务)
cd tenant-service  
pip install -r requirements.txt
uvicorn tenant_service.main:app --host 0.0.0.0 --port 8002 --reload

# 终端 3 - EINO Service (AI工作流服务)
cd eino-service
go mod download
go run cmd/server/main.go

# 终端 4 - Memory Service (记忆管理服务)
cd memory-service
pip install -r requirements.txt  
uvicorn main:app --host 0.0.0.0 --port 8004 --reload

# 终端 5 - API Gateway (API网关)
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 终端 6 - Frontend (前端应用)
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

# 检查基础设施
docker-compose ps
```

## 🔒 安全配置

### 环境变量配置

**重要**: 生产环境必须更换 `.env` 文件中的所有默认密钥！

```bash
# 生成强密钥示例
# JWT 签名密钥 (32+ 字符)
SECRET_KEY="your-super-secret-jwt-key-32-characters-min"

# pgcrypto 加密密钥 (32+ 字符)  
PGCRYPTO_KEY="your-pgcrypto-encryption-key-32-chars"

# 数据库密码
DB_PASSWORD="your-strong-database-password"

# Redis 密码
REDIS_PASSWORD="your-strong-redis-password"
```

### 多租户数据隔离

- **数据库级隔离**: 敏感数据存储在租户专用数据库
- **表级隔离**: 共享表通过 `tenant_id` 字段强制过滤
- **缓存隔离**: Redis 键使用 `tenant:{id}:{key}` 模式
- **API隔离**: JWT 中包含 `tenant_id`，中间件自动注入上下文

## 📖 文档链接

| 文档类型 | 链接 | 描述 |
|---------|------|------|
| 开发规范 | [docs/STANDARDS.md](./docs/STANDARDS.md) | 代码规范、API设计、错误处理等 |
| 项目结构 | [docs/PROJECT_STRUCTURE.md](./docs/PROJECT_STRUCTURE.md) | 目录结构和文件组织规范 |
| API网关 | [docs/api_gateway.md](./docs/api_gateway.md) | API网关服务详细规范 |
| 认证服务 | [docs/auth_service.md](./docs/auth_service.md) | JWT认证和用户登录规范 |
| 租户服务 | [docs/tenant_service.md](./docs/tenant_service.md) | 租户和用户管理规范 |
| EINO服务 | [docs/eino_service.md](./docs/eino_service.md) | AI工作流编排服务规范 |
| 记忆服务 | [docs/memory_service.md](./docs/memory_service.md) | 对话记忆管理服务规范 |

## 🚨 开发注意事项

### 核心原则

1. **安全第一**: 所有操作必须验证 `tenant_id`，敏感数据必须加密
2. **服务边界**: 严格遵循微服务职责，不得跨服务直接访问数据
3. **全链路追踪**: 每个请求必须携带 `X-Request-ID`
4. **中文开发**: 所有注释、提交信息、错误消息使用中文

### 代码提交规范

```bash
# 提交信息格式
git commit -m "feat(模块): 功能描述"
git commit -m "fix(auth): 修复JWT令牌验证问题"  
git commit -m "docs(api): 更新API文档说明"
```

## 🆘 问题排查

### 常见问题

1. **服务启动失败**: 检查端口占用和环境变量配置
2. **数据库连接失败**: 确认 Docker 服务启动完成
3. **认证失败**: 验证 JWT 密钥配置
4. **数据隔离问题**: 检查 `tenant_id` 的传递和过滤

### 日志查看

```bash
# 查看特定请求的全链路日志
grep "request_id:xxx" logs/*.log

# 查看特定租户的操作日志  
grep "tenant_id:xxx" logs/*.log

# 查看 Docker 容器日志
docker-compose logs postgres
docker-compose logs redis
```

---

**⚠️ 重要提醒**: 本平台处理多租户数据和AI供应商凭证，任何代码变更都必须经过严格的安全审查。开发过程中如有疑问，请参考对应服务的规范文档。