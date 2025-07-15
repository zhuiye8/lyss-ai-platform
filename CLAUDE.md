# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚨 重要提醒 - 项目状态更新 (2025-07-15)

**当前项目状态**: 🎉 EINO服务Go架构实现完成！凭证管理对接成功，准备启动和集成测试  
**如果你是继续开发的Claude**: 
1. 请务必先阅读 `DEVELOPMENT_PRIORITY.md` 文件，快速了解当前开发状态和下一步任务
2. 参考 `docs/eino_service.md` 了解EINO服务的完整设计
3. 查看已有的代码结构，特别是 `eino-service/` 目录和 `tenant-service/routers/internal.py` 的新内部接口

### 已完成的基础工作
- ✅ **项目架构设计和文档 (100%)**
  - 完整的微服务规范文档
  - 开发规范和项目结构定义
  - API设计和数据库设计文档

- ✅ **基础设施配置 (100%)**
  - Docker Compose 基础设施服务配置
  - PostgreSQL + Redis + Qdrant + MinIO 
  - 数据库初始化脚本和测试数据
  - 环境变量配置模板

- ✅ **Auth Service - 认证服务 (100%)** (2025-07-14)
  - JWT认证机制，Redis集成，健康检查
  - 与Tenant Service集成调用
  - 完整错误处理和中文日志
  - ✅ 前后端登录功能完全正常！

- ⚠️ **Tenant Service - 租户服务 (80%)** (2025-07-11)
  - ✅ 内部用户验证接口，pgcrypto加密存储，多租户数据隔离
  - ✅ SQLAlchemy关系映射，Repository层完整
  - ⏳ 租户管理、用户管理、供应商凭证管理API待补全

- ✅ **Backend API Gateway - API网关服务 (100%)** (2025-07-14)
  - 统一入口和路由转发，JWT认证集成
  - 分布式追踪，安全防护，健康检查
  - 支持5000+并发，完整错误处理
  - 与Auth Service和Tenant Service无缝集成
  - ✅ 错误处理和数据传递优化完成！

- ✅ **Frontend - 前端应用 (基础登录100%)** (2025-07-14)
  - React + TypeScript + Ant Design架构
  - ✅ 登录功能完全正常！JWT认证集成
  - ✅ HTTP拦截器和数据格式处理修复完成
  - ⏳ 管理界面等待后端API完成

### 下一步工作重点
1. **Tenant Service 管理API补全** (优先级: 高) - 当前开发目标
2. **Frontend 管理界面实现** (优先级: 高) 
3. **EINO Service + Memory Service** (优先级: 中)

### 核心开发要求
1. **全程使用中文注释和回复**
2. **严格遵循项目开发规范**
3. **及时更新项目进度文档**
4. **确保多租户数据隔离和安全性**

## 项目概述

Lyss是一个企业级AI服务聚合与管理平台，采用微服务架构，实现多租户的AI模型集成、编排和治理。平台的核心架构基于三大支柱：

1. **双轨制供应商管理** - 统一抽象层支持多种AI服务提供商（OpenAI、Anthropic、Google等）
2. **统一对话中心** - 提供持久化、上下文感知的对话界面
3. **集中式治理与管控** - 多租户后台管理系统，支持权限控制、成本管理和安全审计

## 架构组件

### 微服务架构
- **backend/** - FastAPI主API网关服务，统一入口和路由分发 (✅ 已完成)
- **auth-service/** - FastAPI认证服务，JWT令牌管理和用户验证 (✅ 已完成)
- **tenant-service/** - FastAPI租户服务，用户管理和供应商凭证管理 (✅ 已完成)
- **frontend/** - React + TypeScript + Ant Design前端应用 (待开发)
- **eino-service/** - Go + EINO框架，AI工作流编排服务 (待开发)
- **memory-service/** - FastAPI + Mem0AI记忆服务，对话记忆和上下文管理 (待开发)

### 数据层
- **PostgreSQL** - 混合多租户模型：敏感数据独立数据库，大容量数据通过tenant_id隔离
- **Redis** - 缓存和向量存储，支持租户键前缀隔离和ACL权限控制

### 技术栈特点
- **多租户策略**: 混合模型，核心数据库级隔离 + 大容量数据表级隔离
- **安全架构**: JWT认证 + RBAC权限控制 + pgcrypto数据加密
- **工作流编排**: EINO图编排实现OptimizedRAG等复杂AI工作流
- **API设计**: RESTful + 流式响应，统一错误处理和请求追踪

## 开发命令

### 环境启动
```bash
# 启动基础设施服务（数据库、缓存等）
docker-compose up -d

# 等待服务启动完成
sleep 15

# 验证基础设施服务状态
docker-compose ps

# 启动API Gateway服务（统一入口）
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn api_gateway.main:app --reload --host 0.0.0.0 --port 8000
```

### 数据库操作
```bash
# 初始化数据库
psql -h localhost -U lyss_user -d lyss_platform -f sql/init.sql

# 创建租户数据库
python scripts/create_tenant_db.py --tenant-id <uuid>
```

### 服务开发
```bash
# Auth Service (认证服务) - 端口 8001
cd auth-service
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn auth_service.main:app --reload --host 0.0.0.0 --port 8001

# Tenant Service (租户服务) - 端口 8002  
cd tenant-service
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn tenant_service.main:app --reload --host 0.0.0.0 --port 8002

# Backend API Gateway - 端口 8000
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn api_gateway.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (前端应用) - 端口 3000
cd frontend
npm install
npm run dev

# EINO Service (AI工作流) - 端口 8003 (待开发)
cd eino-service
go mod download
go run cmd/server/main.go

# Memory Service (记忆服务) - 端口 8004 (待开发)
cd memory-service
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8004
```

### 测试和质量检查
```bash
# 健康检查 (验证所有服务正常运行)
curl http://localhost:8000/health  # API Gateway
curl http://localhost:8001/health  # Auth Service  
curl http://localhost:8002/health  # Tenant Service
curl http://localhost:3000         # Frontend

# 后端服务测试
cd auth-service
pytest tests/ --cov=. --cov-report=xml

cd tenant-service  
pytest tests/ --cov=. --cov-report=xml

cd backend
pytest tests/ --cov=. --cov-report=xml

# 前端测试和质量检查
cd frontend
npm run lint              # ESLint代码检查
npm run type-check        # TypeScript类型检查
npm run format:check      # Prettier格式检查

# 安全扫描
bandit -r auth-service/ -f json
bandit -r tenant-service/ -f json  
bandit -r backend/ -f json
cd frontend && npm audit --audit-level=moderate
```

## 重要配置

### 端口映射和服务地址
- **Frontend**: http://localhost:3000 (React + Vite开发服务器)
- **API Gateway**: http://localhost:8000 (统一入口，所有前端请求经此路由)
- **Auth Service**: http://localhost:8001 (内部服务，不直接暴露)
- **Tenant Service**: http://localhost:8002 (内部服务，不直接暴露)
- **PostgreSQL**: localhost:5433 (Docker映射端口)
- **Redis**: localhost:6380 (Docker映射端口)
- **Qdrant**: localhost:6333 (向量数据库)
- **MinIO**: localhost:9000/9001 (对象存储)

### 环境变量
- `SECRET_KEY` - JWT签名密钥（至少32字符）
- `DB_HOST` / `DB_PORT` / `DB_USERNAME` / `DB_PASSWORD` / `DB_DATABASE` - 数据库连接配置
- `REDIS_HOST` / `REDIS_PORT` / `REDIS_PASSWORD` - Redis连接配置
- `ENVIRONMENT` - 运行环境（development/staging/production）
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` - AI服务商密钥（待使用）

### 默认测试账户
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

### 租户隔离机制
- 数据库：租户专用数据库 + tenant_id字段过滤
- 缓存：`tenant:{tenant_id}:{key}` 键命名模式
- API：JWT中包含tenant_id，中间件自动注入租户上下文

### 安全要点
- API密钥使用pgcrypto列级加密存储
- 所有租户操作必须通过JWT验证tenant_id
- Redis ACL限制租户只能访问自己的键空间
- 审计日志记录所有关键操作

## 开发注意事项

### 开发优先级 (2025年7月9日更新)
当前处于**第一阶段：核心业务功能开发**，优先级如下：
1. **对话管理系统** (HIGH) - 平台核心功能
2. **AI服务集成层** (HIGH) - 核心业务价值
3. **基础前端界面** (HIGH) - 用户体验基础

### 代码规范 (必须严格遵循)
- **Python**: 使用中文注释，遵循PEP 8，类型提示完整
- **Go**: 使用中文注释，遵循Go标准格式，错误处理规范
- **TypeScript**: 使用中文注释，严格类型检查，React最佳实践
- **所有提交信息使用中文**，格式：`feat(模块): 功能描述`

### 数据库操作
- 查询共享表时必须包含 `WHERE tenant_id = ?` 条件
- 使用 `tenant_context.get_current_tenant_id()` 获取当前租户ID
- 敏感数据写入前必须使用加密函数

### API开发
- 所有API遵循 `/api/v1/` 版本前缀
- 返回统一JSON格式，包含success、data、message、request_id、timestamp、errors字段
- 流式响应使用Server-Sent Events格式
- 错误信息和响应消息使用中文

### 前端开发
- 使用Ant Design + Ant Design X双库策略
- 通过ConfigProvider实现统一主题
- 聊天组件使用@ant-design/x的Bubble和Sender组件

### EINO工作流
- 工作流定义在eino-service/internal/workflows/
- 使用compose.Graph进行图编排
- 支持OptimizedRAG、SimpleChat、ToolCalling等预定义工作流

## 常见问题排查

### 服务启动问题
```bash
# 检查端口占用
lsof -i :8000  # API Gateway
lsof -i :8001  # Auth Service
lsof -i :8002  # Tenant Service
lsof -i :3000  # Frontend

# 检查Docker服务状态
docker-compose ps
docker-compose logs postgres
docker-compose logs redis

# 重启基础设施服务
docker-compose down && docker-compose up -d
```

### 数据库连接问题
```bash
# 测试数据库连接
psql -h localhost -p 5433 -U lyss -d lyss_db

# 查看数据库日志
docker-compose logs postgres

# 重新初始化数据库
docker-compose down -v
docker-compose up -d
```

### 认证问题
```bash
# 验证JWT令牌
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@lyss.dev","password":"admin123"}'

# 测试受保护路由
curl -X GET http://localhost:8000/api/v1/admin/tenants \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 前端开发问题
```bash
# 清理node_modules和重新安装
cd frontend
rm -rf node_modules package-lock.json
npm install

# 检查TypeScript错误
npm run type-check

# 检查ESLint错误
npm run lint
```

### 日志查看
```bash
# 查看特定请求的全链路日志 (使用request_id)
grep "request_id:xxx" logs/*.log

# 查看特定租户的操作日志
grep "tenant_id:xxx" logs/*.log

# 实时查看服务日志
tail -f logs/auth-service.log
tail -f logs/tenant-service.log
tail -f logs/api-gateway.log
```

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.