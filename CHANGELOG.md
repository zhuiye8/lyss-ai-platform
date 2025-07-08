# 更新日志

本文档记录了 Lyss AI Platform 的所有重要更改。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [未发布]

### 新增
- 初始项目结构搭建
- 微服务架构设计
- 多租户支持
- AI供应商集成框架

### 变更
- 无

### 废弃
- 无

### 移除
- 无

### 修复
- 无

### 安全性
- 实现JWT认证
- 数据库敏感数据加密
- RBAC权限控制

## [1.0.0] - 2025-07-08

### 新增
- 🎉 首次发布 Lyss AI Platform
- 🏗️ 微服务架构实现
  - API网关服务 (FastAPI)
  - EINO工作流编排服务 (Go)
  - 记忆管理服务 (Mem0AI)
  - 租户管理服务
- 🎨 前端应用 (React + TypeScript + Ant Design)
- 🗄️ 数据持久化
  - PostgreSQL 主数据库
  - Redis 缓存和会话存储
- 🔐 安全功能
  - JWT 无状态认证
  - 多层级 RBAC 权限控制
  - 租户数据隔离
  - API 速率限制
- 🤖 AI 服务集成
  - OpenAI GPT 系列模型
  - Anthropic Claude 模型
  - Google Gemini 模型
  - 统一的供应商适配器接口
- 🧠 智能记忆系统
  - 用户个性化记忆存储
  - 语义搜索功能
  - 自动记忆分类
  - 记忆重要性评分
- 🔄 工作流编排
  - 简单对话工作流
  - RAG 增强对话工作流
  - 多步骤处理工作流
  - 函数调用工作流
- 📊 监控和观测
  - Prometheus 指标收集
  - Grafana 仪表板
  - Jaeger 分布式追踪
  - 结构化日志记录
- 🐳 容器化部署
  - Docker 容器支持
  - Docker Compose 开发环境
  - Kubernetes 生产部署
- 📝 完整文档
  - API 接口文档
  - 开发指南
  - 部署指南
  - 架构设计文档

### 核心特性
- **多租户架构**: 支持企业级多租户隔离和管理
- **AI 供应商聚合**: 统一接入多个 AI 服务提供商
- **智能记忆**: 基于 Mem0AI 的个性化对话记忆
- **工作流编排**: 使用 EINO 框架的复杂 AI 工作流
- **高性能**: 异步处理和微服务架构
- **安全性**: 端到端加密和严格的权限控制
- **可扩展性**: 水平扩展和负载均衡支持
- **监控**: 全面的系统监控和告警

### 技术栈
- **后端**: FastAPI (Python 3.11), EINO (Go 1.21)
- **前端**: React 18, TypeScript, Ant Design 5
- **数据库**: PostgreSQL 15, Redis 7
- **AI集成**: Mem0AI, OpenAI, Anthropic, Google
- **部署**: Docker, Kubernetes
- **监控**: Prometheus, Grafana, Jaeger

### 文件结构
```
lyss-ai-platform/
├── backend/                    # 后端微服务
├── frontend/                   # 前端应用
├── eino-service/              # EINO工作流服务
├── memory-service/            # 记忆管理服务
├── sql/                       # 数据库脚本
├── k8s/                       # Kubernetes配置
├── monitoring/                # 监控配置
├── scripts/                   # 脚本工具
├── docs/                      # 项目文档
├── read/                      # 技术文档
├── config/                    # 配置文件
├── docker-compose.yml         # Docker Compose配置
└── README.md                  # 项目说明
```

### 默认配置
- **API端口**: 8000 (API网关), 8080 (EINO), 8001 (记忆服务)
- **前端端口**: 3000
- **数据库端口**: 5432 (PostgreSQL), 6379 (Redis)
- **监控端口**: 9090 (Prometheus), 3001 (Grafana)

### 默认账户
- **管理员**: admin@lyss.ai / admin123
- **演示租户管理员**: demo@example.com / admin123
- **普通用户**: user@example.com / admin123

### 安装要求
- Node.js >= 18.0.0
- Python >= 3.11
- Go >= 1.21
- Docker >= 20.10
- Docker Compose >= 2.0

### 快速开始
```bash
# 克隆项目
git clone https://github.com/your-org/lyss-ai-platform.git
cd lyss-ai-platform

# 运行设置脚本
./scripts/setup-dev.sh

# 启动开发环境
docker-compose -f docker-compose.dev.yml up -d
```

### 已知问题
- 无

### 升级说明
- 这是首次发布，无需升级

---

## 版本说明

### 版本号规范
本项目使用语义化版本 (SemVer)：
- **主版本号**: 不兼容的 API 修改
- **次版本号**: 向下兼容的功能性新增
- **修订号**: 向下兼容的问题修正

### 发布周期
- **主版本**: 按需发布，通常包含重大架构变更
- **次版本**: 每月发布，包含新功能和改进
- **修订版本**: 每周发布，包含bug修复和小改进

### 支持政策
- **当前版本**: 完全支持，包含新功能和bug修复
- **前一个主版本**: 仅提供安全更新和严重bug修复
- **更早版本**: 不再支持

### 迁移指南
每个主版本更新都会提供详细的迁移指南，包括：
- 破坏性变更说明
- 迁移步骤
- 兼容性说明
- 回滚方案

---

**注意**: 
- 本项目目前处于积极开发阶段
- API 可能会有变化，请关注更新日志
- 生产环境使用前请充分测试
- 如有问题请提交 [Issue](https://github.com/your-org/lyss-ai-platform/issues)