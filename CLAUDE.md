# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚨 重要提醒 - 项目状态更新 (2025-07-09)

**当前项目状态**: 第一阶段核心功能开发已完成90%，准备进入第二阶段
**如果你是继续开发的Claude**: 请务必先阅读 `项目开发状态总结.md` 文件，获取完整的项目开发状态和上下文信息

### 第一阶段已完成功能
- ✅ **后端核心功能 (85% → 100%)**
  - 完整的认证授权系统（JWT + RBAC）
  - 对话管理系统（CRUD + 搜索 + 分页）
  - AI服务集成层（OpenAI + Anthropic + 流式响应）
  - 基础设施优化（数据库 + Redis + 中间件）

- ✅ **前端基础界面 (5% → 70%)**
  - React + TypeScript + Ant Design架构
  - 用户登录和主布局系统
  - 仪表盘和对话管理界面
  - 响应式设计和状态管理

### 下一步工作重点
1. **Memory服务完善** (优先级: HIGH)
2. **EINO工作流服务** (优先级: HIGH)
3. **管理后台功能** (优先级: MEDIUM)

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
- **backend/** - FastAPI主API网关服务，包含完整的认证、租户管理、权限控制系统 ✅
- **frontend/** - React + TypeScript + Ant Design前端应用，基础界面已完成 ✅
- **eino-service/** - 字节跳动EINO框架的Go服务，负责AI工作流编排（待开发）
- **memory-service/** - FastAPI + Mem0AI记忆服务，处理对话记忆和上下文（待开发）

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

# 启动Backend服务
cd backend
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
# 后端服务
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 前端应用
cd frontend
npm install
npm run dev

# EINO服务
cd eino-service
go mod download
go run cmd/server/main.go

# 记忆服务
cd memory-service
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

### 测试和质量检查
```bash
# 后端测试
cd backend
pytest tests/ --cov=. --cov-report=xml

# 前端测试
cd frontend
npm run test:unit
npm run test:e2e

# 安全扫描
bandit -r backend/ -f json
npm audit --audit-level=moderate

# 类型检查
cd backend && mypy .
cd frontend && npm run type-check
```

## 重要配置

### 环境变量
- `SECRET_KEY` - JWT签名密钥（至少32字符）
- `DB_HOST` / `DB_PORT` / `DB_USERNAME` / `DB_PASSWORD` / `DB_DATABASE` - 数据库连接配置
- `REDIS_HOST` / `REDIS_PORT` / `REDIS_PASSWORD` - Redis连接配置
- `ENVIRONMENT` - 运行环境（development/staging/production）
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` - AI服务商密钥（待使用）

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