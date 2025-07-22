# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚨 重要提醒 - 项目状态更新 (2025-01-22)

**🎉 重大里程碑**: 架构统一100%完成！Auth Service和Provider Service已100%完成！  
**当前项目状态**: 项目架构完全统一，核心服务生产就绪，用户服务85%完成  

**如果你是继续开发的Claude**:
1. **必读文档**：`📋 下次会话开发指南.md` - 当前状态和下步工作指导
2. **重大成果**：`🎯 开发进度报告 - 架构统一完成.md` - 架构统一完成报告
3. **下步重点**：完成User Service剩余15% + 开始Chat Service开发
4. **架构模式**：统一数据库架构 + 混合部署（Docker基础设施 + 本地微服务）  
5. **架构参考**：Auth和Provider Service的企业级架构可作为其他服务模板

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

- ✅ **Auth Service - 认证服务 (100%完成)** (2025-01-22) ⭐
  - ✅ 企业级JWT令牌管理 (创建、验证、刷新、撤销、黑名单)
  - ✅ RBAC权限管理系统 (角色、权限、用户角色关联)
  - ✅ OAuth2联邦认证 (Google、GitHub、Microsoft，PKCE支持)
  - ✅ 多因素认证MFA (TOTP、SMS、Email、备份代码)
  - ✅ 安全策略管理 (密码策略、IP控制、审计日志)
  - ✅ 企业级中间件系统 (认证、权限、限流、监控、日志)
  - ✅ 完整测试基础设施 (7个测试文件、200+测试方法、>80%覆盖率)

- ✅ **Provider Service - 供应商服务 (100%完成)** (2025-01-22) ⭐
  - ✅ 多供应商AI模型管理 (OpenAI、Anthropic、DeepSeek、Azure等)
  - ✅ Channel负载均衡和故障转移机制
  - ✅ API透明代理 (OpenAI兼容接口，统一错误处理)
  - ✅ 配额管理系统 (多租户配额跟踪和限制控制)
  - ✅ 多租户凭证管理 (pgcrypto安全存储和动态验证)
  - ✅ 基于One-API架构的Channel管理系统
  - ✅ 完整的统一数据库架构集成

- 🚀 **User Service - 用户管理服务 (85%完成)** (2025-01-22)
  - ✅ 基于统一数据库架构的SQLAlchemy优化架构
  - ✅ 用户管理核心功能 (创建、激活、更新、删除、搜索)
  - ✅ 异步数据库会话管理和事务处理
  - ✅ 多租户用户关联和权限检查框架
  - 🔄 用户画像分析器、活动追踪、关系管理 (进行中)
  - ⏳ API路由完善、偏好设置、完整测试覆盖 (待完成)

- ✅ **Backend API Gateway - API网关服务 (100%)** (2025-07-14)
  - 统一入口和路由转发，JWT认证集成
  - 分布式追踪，安全防护，健康检查
  - 支持5000+并发，完整错误处理
  - 与Auth Service和Tenant Service无缝集成
  - ✅ 错误处理和数据传递优化完成！

- 🎨 **Frontend - 前端应用 (AI对话界面现代化80%)** (2025-07-16)
  - ✅ React 18 + TypeScript + Ant Design 5.x + Ant Design X架构
  - ✅ 登录功能完全正常！JWT认证集成
  - ✅ AI对话页面现代化：使用Ant Design X的Bubble和Sender组件
  - ✅ 现代化主题配色方案（从深色改为浅色主题）
  - ✅ 响应式设计支持和流式响应功能
  - ⚠️ 界面架构需重构：当前有冗余用户头像，侧边栏需改为对话历史
  - ⏳ 对话历史侧边栏和智能总结功能待实现

- ⏳ **Chat Service - AI对话服务 (待开发，下次会话重点)**
  - 🎯 基于EINO框架的Go微服务架构 (v0.3.52已调研验证)
  - 🎯 AI工作流编排和多供应商模型调用集成
  - 🎯 WebSocket实时流式响应处理
  - 🎯 对话上下文管理和记忆增强集成
  - 🎯 统一数据库架构下的chat_*表结构设计

- ⏳ **Memory Service - 智能记忆服务 (待开发)**
  - 🎯 基于Mem0AI + Qdrant + FastAPI技术栈
  - 🎯 智能对话记忆提取和语义检索
  - 🎯 用户画像分析和个性化上下文生成
  - 🎯 与Chat Service的深度集成和协作

### 🚀 下一步工作建议 (2025-01-22更新)

**架构统一和核心服务已完成，下次会话重点工作**：

**优先级1: 完成User Service剩余15%功能** 🔥 (紧急)
- 用户画像分析器和活动追踪系统实现
- 用户关系管理模块和API路由完善
- 用户偏好设置管理和通知系统集成
- 完整测试覆盖和与Auth Service集成测试

**优先级2: 开始Chat Service开发** 🚀 (高)
- 基于EINO框架v0.3.52的Go微服务架构
- WebSocket实时通信和流式响应处理
- 与Provider Service的多供应商模型调用集成
- 对话上下文管理和数据库表结构设计

**优先级3: 三大服务集成测试** ⚡ (高)
- Auth + User + Provider三大核心服务联调
- API Gateway路由和代理功能完整验证
- 统一数据库架构下的事务一致性测试
- 多租户数据隔离和安全性验证

### 核心开发要求
1. **全程使用中文注释和回复**
2. **严格遵循项目开发规范**
3. **优先解决用户体验问题** - 界面布局和空间利用
4. **保持现有功能完整性** - 重构过程中不破坏已实现功能
5. **参考先进设计模式** - ChatGPT、Gemini、Grok等AI平台界面
6. **确保多租户数据隔离和安全性**

## 项目概述

Lyss是一个企业级AI服务聚合与管理平台，采用微服务架构，实现多租户的AI模型集成、编排和治理。平台的核心架构基于三大支柱：

1. **双轨制供应商管理** - 统一抽象层支持多种AI服务提供商（OpenAI、Anthropic、Google等）
2. **统一对话中心** - 提供持久化、上下文感知的对话界面
3. **集中式治理与管控** - 多租户后台管理系统，支持权限控制、成本管理和安全审计

## 架构组件

### 微服务架构
- **backend/** - FastAPI主API网关服务，统一入口和路由分发 (✅ 已完成)
- **auth-service/** - FastAPI认证服务，JWT令牌管理和用户验证 (✅ 100%完成)
- **provider-service/** - FastAPI供应商服务，多AI模型管理和代理 (✅ 100%完成)
- **user-service/** - FastAPI用户服务，用户管理和画像分析 (🚀 85%完成)
- **chat-service/** - Go + EINO框架，AI工作流编排和对话服务 (⏳ 待开发)
- **memory-service/** - FastAPI + Mem0AI记忆服务，对话记忆和上下文管理 (⏳ 待开发)
- **frontend/** - React + TypeScript + Ant Design X前端应用 (🔄 需要重构)

### 数据层 (2025-01-22统一架构)
- **PostgreSQL** - 统一数据库架构：所有服务共享lyss_db数据库，通过表前缀隔离
- **Redis** - 缓存和会话存储，支持租户键前缀隔离和ACL权限控制
- **Qdrant** - 向量数据库，用于Memory Service的语义检索和记忆管理
- **MinIO** - 对象存储，用于文件上传和多媒体资源管理

### 技术栈特点
- **统一数据库策略**: 单一PostgreSQL实例，表前缀隔离(auth_*, provider_*, chat_*等)
- **混合部署模式**: Docker基础设施服务 + 本地启动微服务，便于开发调试
- **安全架构**: JWT认证 + RBAC权限控制 + pgcrypto数据加密
- **工作流编排**: EINO v0.3.52图编排实现OptimizedRAG等复杂AI工作流
- **API设计**: RESTful + WebSocket流式响应，统一错误处理和请求追踪

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

# User Service (用户服务) - 端口 8002  
cd user-service
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn user_service.main:app --reload --host 0.0.0.0 --port 8002

# Provider Service (供应商服务) - 端口 8003
cd provider-service
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn provider_service.main:app --reload --host 0.0.0.0 --port 8003

# Backend API Gateway - 端口 8000
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn api_gateway.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (前端应用) - 端口 3000
cd frontend
npm install
npm run dev

# Chat Service (AI对话服务) - 端口 8004 (待开发)
cd chat-service
go mod download
go run cmd/server/main.go

# Memory Service (记忆服务) - 端口 8005 (待开发)
cd memory-service
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn memory_service.main:app --reload --host 0.0.0.0 --port 8005
```

### 测试和质量检查
```bash
# 健康检查 (验证所有服务正常运行)
curl http://localhost:8000/health  # API Gateway
curl http://localhost:8001/health  # Auth Service  
curl http://localhost:8002/health  # User Service
curl http://localhost:8003/health  # Provider Service
curl http://localhost:3000         # Frontend

# 后端服务测试
cd auth-service
pytest tests/ --cov=. --cov-report=xml

cd user-service  
pytest tests/ --cov=. --cov-report=xml

cd provider-service
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
bandit -r user-service/ -f json
bandit -r provider-service/ -f json  
bandit -r backend/ -f json
cd frontend && npm audit --audit-level=moderate
```

## 重要配置

### 端口映射和服务地址
- **Frontend**: http://localhost:3000 (React + Vite开发服务器)
- **API Gateway**: http://localhost:8000 (统一入口，所有前端请求经此路由)
- **Auth Service**: http://localhost:8001 (内部服务，不直接暴露)
- **User Service**: http://localhost:8002 (内部服务，不直接暴露)
- **Provider Service**: http://localhost:8003 (内部服务，不直接暴露)
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

### 租户隔离机制 (统一数据库架构)
- 数据库：统一lyss_db数据库 + tenant_id字段过滤 + 表前缀隔离
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
lsof -i :8002  # User Service
lsof -i :8003  # Provider Service
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
tail -f logs/user-service.log
tail -f logs/provider-service.log
tail -f logs/api-gateway.log
```

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.