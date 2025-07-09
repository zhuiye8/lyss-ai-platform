# Lyss AI Platform - 企业级AI服务聚合平台

![Lyss AI Platform](https://img.shields.io/badge/Lyss%20AI-Platform-blue?style=for-the-badge)
![Version](https://img.shields.io/badge/version-1.0.0-green?style=for-the-badge)
![License](https://img.shields.io/badge/license-MIT-yellow?style=for-the-badge)
![Progress](https://img.shields.io/badge/项目进度-90%25-brightgreen?style=for-the-badge)

## 🚨 重要提醒 - 项目状态更新 (2025-07-09)

**当前项目状态**: 第一阶段核心功能开发已完成90%，准备进入第二阶段增强功能开发

**如果你是继续开发的Claude AI Assistant**: 
📖 **请务必先阅读 [`项目开发状态总结.md`](./项目开发状态总结.md) 文件**，获取完整的项目开发状态和上下文信息

### 最新完成功能 (2025-07-09)
- ✅ **后端核心功能 (100%)**：认证授权、对话管理、AI服务集成
- ✅ **前端基础界面 (70%)**：React应用、用户界面、对话管理
- ✅ **技术架构优化**：微服务架构、数据库设计、缓存系统

### 下一步工作重点
1. 🔄 **Memory服务完善** - 基于Mem0AI的记忆系统
2. 🔄 **EINO工作流服务** - Go语言工作流编排
3. 🔄 **管理后台功能** - 系统管理和监控界面

## 🌟 项目概述

Lyss AI Platform 是一个企业级的AI服务聚合与管理平台，旨在为企业提供统一的AI服务接入、管理和治理能力。平台采用微服务架构，支持多租户模式，集成了多种AI服务提供商，提供智能记忆、工作流编排等高级功能。

### 核心特性

- 🤖 **多AI供应商支持** - 统一接入OpenAI、Anthropic、Google等主流AI服务
- 🧠 **智能记忆系统** - 基于Mem0AI的个性化对话记忆
- 🔄 **工作流编排** - 使用字节跳动EINO框架的复杂AI工作流
- 🏢 **多租户架构** - 企业级多租户隔离和管理
- 🔐 **安全与权限** - 完善的RBAC权限控制和数据加密
- 📊 **监控与分析** - 全面的系统监控和使用分析
- 🚀 **高性能** - 基于FastAPI和Go的高性能微服务架构

## 🏗️ 技术架构

### 技术栈

#### 后端服务
- **API网关**: FastAPI + Python 3.11
- **工作流编排**: EINO (Go 1.21)
- **记忆服务**: Mem0AI + FastAPI
- **数据库**: PostgreSQL 15
- **缓存**: Redis 7
- **消息队列**: Redis

#### 前端应用
- **框架**: React 18 + TypeScript
- **UI组件**: Ant Design 5 + Ant Design X
- **状态管理**: Zustand
- **构建工具**: Vite

#### 基础设施
- **容器化**: Docker + Docker Compose
- **编排**: Kubernetes
- **监控**: Prometheus + Grafana + Jaeger
- **日志**: ELK Stack (可选)

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        前端层                                │
│              React + Ant Design + TypeScript               │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────┐
│                      API网关层                              │
│                FastAPI + 认证 + 限流                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
┌───────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐
│  EINO服务   │ │ 记忆服务   │ │ 租户服务   │
│ (Go+EINO)   │ │(Mem0AI)   │ │ (FastAPI) │
└─────────────┘ └───────────┘ └───────────┘
        │             │             │
        └─────────────┼─────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
┌───────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐
│ PostgreSQL  │ │   Redis   │ │ 监控系统   │
│    数据库    │ │   缓存    │ │Prometheus │
└─────────────┘ └───────────┘ └───────────┘
```

## 🚀 快速开始

### 环境要求

- **Node.js** >= 18.0.0
- **Python** >= 3.11
- **Go** >= 1.21
- **Docker** >= 20.10
- **Docker Compose** >= 2.0

### 开发环境安装

1. **克隆项目**
```bash
git clone https://github.com/your-org/lyss-ai-platform.git
cd lyss-ai-platform
```

2. **安装Python依赖**
```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装后端依赖
cd backend
pip install -r requirements.txt
cd ..

# 安装记忆服务依赖
cd memory-service
pip install -r requirements.txt
cd ..
```

3. **安装前端依赖**
```bash
cd frontend
npm install
cd ..
```

4. **安装Go依赖**
```bash
cd eino-service
go mod download
cd ..
```

5. **启动基础服务**
```bash
# 启动数据库和Redis
docker-compose up -d postgres redis

# 等待数据库启动完成
sleep 10

# 初始化数据库（可选）
# psql -h localhost -U lyss_dev_user -d lyss_platform_dev -f sql/init.sql
```

6. **启动开发服务**

在不同终端窗口中运行：

```bash
# 终端1: 启动API网关
cd backend
source venv/bin/activate
python start_server.py

# 终端2: 启动EINO服务
cd eino-service
go run cmd/server/main.go

# 终端3: 启动记忆服务
cd memory-service
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# 终端4: 启动前端
cd frontend
npm run dev
```

### 访问应用

- **前端应用**: http://localhost:5173 (Vite开发服务器)
- **API文档**: http://localhost:8000/docs
- **API健康检查**: http://localhost:8000/health
- **EINO服务**: http://localhost:8080
- **记忆服务**: http://localhost:8001

### 开发环境配置

项目使用统一的 `.env` 文件进行配置，主要配置项：

```bash
# 应用配置
SECRET_KEY=dev-secret-key-not-for-production-32chars
ENVIRONMENT=development
DEBUG=true

# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_USERNAME=lyss_dev_user
DB_PASSWORD=lyss_dev_password
DB_DATABASE=lyss_platform_dev

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=lyss_redis_dev_password

# AI服务配置
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
```

### 故障排除

**后端启动失败**：
- 检查Python虚拟环境是否激活
- 确认数据库服务正在运行
- 检查 `.env` 文件配置是否正确

**前端启动失败**：
- 确认Node.js版本 >= 18.0.0
- 删除 `node_modules` 重新安装
- 检查端口5173是否被占用

**数据库连接失败**：
- 确认Docker容器正在运行：`docker ps`
- 检查数据库配置和凭据
- 查看Docker日志：`docker logs <container_id>`

## 📁 项目结构

```
lyss-ai-platform/
├── backend/                    # 后端服务
│   ├── api_gateway/           # API网关服务
│   ├── tenant-service/        # 租户管理服务
│   ├── common/                # 共享代码
│   ├── tests/                 # 后端测试
│   ├── start_server.py        # 后端启动脚本
│   └── requirements.txt       # Python依赖
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── components/        # React组件
│   │   ├── pages/            # 页面组件
│   │   ├── services/         # API服务
│   │   ├── hooks/            # React Hooks
│   │   ├── store/            # 状态管理
│   │   └── types/            # TypeScript类型
│   └── public/               # 静态资源
├── eino-service/              # EINO工作流服务
│   ├── cmd/                  # 入口点
│   ├── internal/             # 内部包
│   ├── pkg/                  # 公共包
│   └── deployments/          # 部署配置
├── memory-service/            # 记忆服务
│   ├── app/                  # 应用代码
│   ├── tests/                # 测试代码
│   └── requirements.txt      # Python依赖
├── sql/                       # 数据库脚本
│   ├── init/                 # 初始化脚本
│   ├── migrations/           # 迁移脚本
│   └── dev/                  # 开发数据
├── k8s/                       # Kubernetes配置
│   ├── base/                 # 基础配置
│   ├── dev/                  # 开发环境
│   └── prod/                 # 生产环境
├── monitoring/                # 监控配置
│   ├── prometheus.yml        # Prometheus配置
│   ├── alert_rules.yml       # 告警规则
│   └── grafana/              # Grafana仪表板
├── scripts/                   # 脚本文件
│   ├── setup-dev.sh          # 开发环境设置
│   └── deploy/               # 部署脚本
├── docs/                      # 文档
├── read/                      # 技术文档
├── config/                    # 配置文件
├── docker-compose.yml         # Docker Compose配置
├── docker-compose.dev.yml     # 开发环境配置
└── README.md                  # 项目说明
```

## 🔧 配置说明

### 环境变量

项目使用统一的 `.env` 文件进行配置，所有服务共享同一个配置文件。

主要配置项：

- `SECRET_KEY`: 应用密钥（生产环境必须修改）
- `DB_*`: 数据库连接配置
- `REDIS_*`: Redis连接配置
- `OPENAI_API_KEY`: OpenAI API密钥
- `ANTHROPIC_API_KEY`: Anthropic API密钥
- `EINO_*`: EINO服务配置
- `MEMORY_*`: 记忆服务配置

**注意**: 所有服务都会从项目根目录的 `.env` 文件读取配置。

### AI服务配置

在管理后台中配置AI服务提供商：

1. 登录管理后台
2. 进入「AI供应商管理」
3. 添加新的AI供应商配置
4. 配置模型映射和速率限制

## 🐳 Docker部署

### 开发环境

```bash
# 启动所有服务
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f api-gateway
```

### 生产环境

```bash
# 构建并启动生产环境
docker-compose up -d

# 扩展API网关
docker-compose up -d --scale api-gateway=3
```

## ☸️ Kubernetes部署

### 部署到开发环境

```bash
# 使用部署脚本
./scripts/deploy/deploy.sh -e dev

# 手动部署
kubectl apply -f k8s/base/
kubectl apply -f k8s/dev/
```

### 部署到生产环境

```bash
# 包含监控组件的生产部署
./scripts/deploy/deploy.sh -e prod -m -r your-registry.com -t v1.0.0
```

## 📊 监控和日志

### Prometheus监控

访问 http://localhost:9090 查看Prometheus监控面板

主要监控指标：
- API响应时间和错误率
- 数据库连接和性能
- Redis使用情况
- AI模型调用统计
- 系统资源使用

### Grafana仪表板

访问 http://localhost:3001 查看Grafana仪表板（admin/admin）

### 日志查看

```bash
# 查看API网关日志
docker-compose logs -f api-gateway

# 查看所有服务日志
docker-compose logs -f

# Kubernetes环境
kubectl logs -f deployment/api-gateway-deployment -n lyss-ai-platform
```

## 🧪 测试

### 运行测试

```bash
# 后端测试
cd backend
source venv/bin/activate
pytest

# 前端测试
cd frontend
npm test

# EINO服务测试
cd eino-service
go test ./...

# 记忆服务测试
cd memory-service
pytest
```

### API测试

使用内置的API文档进行测试：http://localhost:8000/docs

## 🔐 安全性

### 数据加密

- 数据库中的敏感数据使用pgcrypto加密
- API密钥在存储时自动加密
- 传输中的数据使用TLS加密

### 访问控制

- 基于JWT的无状态认证
- 多层级RBAC权限控制
- 租户级数据隔离
- API速率限制

### 安全最佳实践

- 定期更新依赖包
- 使用强密码策略
- 启用审计日志
- 配置安全头
- 定期安全扫描

## 📈 性能优化

### 后端优化

- 数据库连接池
- Redis缓存
- 异步处理
- 数据库索引优化

### 前端优化

- 代码分割
- 懒加载
- CDN静态资源
- 浏览器缓存

### 部署优化

- 水平扩展
- 负载均衡
- 容器资源限制
- HPA自动扩缩容

## 🛠️ 开发指南

### 代码规范

- **Python**: 遵循PEP 8，使用Black格式化
- **TypeScript**: 遵循ESLint规则
- **Go**: 遵循Go官方规范，使用gofmt

### 提交规范

使用约定式提交格式：

```
feat(api): 添加用户认证功能
fix(frontend): 修复登录页面样式问题
docs(readme): 更新部署说明
```

### 分支策略

- `main`: 主分支，用于生产部署
- `develop`: 开发分支
- `feature/*`: 功能分支
- `hotfix/*`: 热修复分支

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交变更 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🆘 支持和帮助

### 文档

- [API文档](docs/api.md)
- [部署指南](docs/deployment.md)
- [开发指南](docs/development.md)
- [FAQ](docs/faq.md)

### 联系我们

- 邮箱: support@lyss.ai
- 文档: https://docs.lyss.ai
- 问题反馈: https://github.com/your-org/lyss-ai-platform/issues

## 🙏 致谢

感谢以下开源项目：

- [FastAPI](https://fastapi.tiangolo.com/) - 现代、快速的Web框架
- [EINO](https://github.com/cloudwego/eino) - 字节跳动的AI工作流框架
- [Mem0AI](https://github.com/mem0ai/mem0) - 智能记忆系统
- [Ant Design](https://ant.design/) - 企业级UI组件库
- [PostgreSQL](https://www.postgresql.org/) - 强大的开源数据库
- [Redis](https://redis.io/) - 高性能内存数据结构存储

---

<div align="center">
  <strong>🚀 Lyss AI Platform - 企业级AI服务聚合平台</strong>
  <br>
  <em>让AI服务触手可及</em>
</div>