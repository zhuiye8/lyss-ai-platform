# Lyss AI Platform 项目目录结构规范

## 📋 文档概述

本文档定义了 **Lyss AI Platform** 项目的标准目录结构，适用于所有微服务和前端应用的本地开发环境。严格遵循本规范将确保代码组织的一致性、降低新成员上手难度、提升团队协作效率。

**适用范围**: 所有Lyss AI Platform相关的代码仓库和服务  
**更新日期**: 2025-07-10

---

## 🏗️ 项目根目录结构

```
lyss-ai-platform/
├── README.md                          # 项目总览和快速开始
├── CLAUDE.md                          # Claude AI开发助手指令
├── docker-compose.yml                 # 基础设施服务编排
├── .env.example                       # 环境变量模板
├── .gitignore                         # Git忽略规则
├── .editorconfig                      # 编辑器配置
├──
├── docs/                              # 📚 项目文档
│   ├── README.md                      # 架构概述
│   ├── PROJECT_STRUCTURE.md           # 目录结构规范(本文档)
│   ├── STANDARDS.md                   # 开发规范总纲
│   ├── api_gateway.md                 # API网关服务规范
│   ├── auth_service.md                # 认证服务规范
│   ├── tenant_service.md              # 租户服务规范
│   ├── eino_service.md                # EINO工作流服务规范
│   ├── memory_service.md              # 记忆服务规范
│   └── deployment/                    # 部署相关文档
│       ├── local_setup.md
│       ├── docker_guide.md
│       └── production_checklist.md
├──
├── scripts/                           # 🔧 项目脚本
│   ├── setup.sh                      # 项目初始化脚本
│   ├── start_services.sh              # 服务启动脚本
│   ├── stop_services.sh               # 服务停止脚本
│   ├── create_tenant_db.py            # 租户数据库创建
│   ├── migrate_db.py                  # 数据库迁移
│   └── health_check.sh                # 健康检查脚本
├──
├── infrastructure/                    # 🐳 基础设施配置
│   ├── docker/                        # Docker相关配置
│   │   ├── postgres/
│   │   │   ├── Dockerfile
│   │   │   └── init.sql
│   │   ├── redis/
│   │   │   ├── Dockerfile
│   │   │   └── redis.conf
│   │   └── qdrant/
│   │       └── config.yaml
│   ├── nginx/                         # Nginx配置
│   │   ├── nginx.conf
│   │   └── ssl/
│   └── monitoring/                    # 监控配置
│       ├── prometheus.yml
│       └── grafana/
├──
├── sql/                               # 📊 数据库脚本
│   ├── init.sql                       # 初始化脚本
│   ├── migrations/                    # 数据库迁移
│   │   ├── 001_create_initial_tables.sql
│   │   ├── 002_add_user_preferences.sql
│   │   └── 003_create_supplier_credentials.sql
│   └── seeds/                         # 测试数据
│       ├── roles.sql
│       ├── tenants.sql
│       └── users.sql
├──
├── frontend/                          # 🎨 React前端应用
├── backend/                           # 🚀 FastAPI主服务 (API Gateway)
├── auth-service/                      # 🔐 FastAPI认证服务
├── tenant-service/                    # 👥 FastAPI租户管理服务
├── eino-service/                      # ⚡ Go工作流编排服务
├── memory-service/                    # 🧠 FastAPI记忆管理服务
├──
├── shared/                            # 📦 共享代码库
│   ├── python/                        # Python共享组件
│   │   ├── auth/                      # 认证相关
│   │   ├── database/                  # 数据库工具
│   │   ├── logging/                   # 日志组件
│   │   └── utils/                     # 通用工具
│   ├── go/                           # Go共享组件
│   │   ├── auth/
│   │   ├── logging/
│   │   └── utils/
│   └── typescript/                    # TypeScript共享组件
│       ├── types/                     # 类型定义
│       ├── api/                       # API客户端
│       └── utils/                     # 工具函数
├──
├── tests/                             # 🧪 集成测试
│   ├── e2e/                          # 端到端测试
│   ├── integration/                   # 集成测试
│   └── load/                         # 负载测试
└──
└── tools/                             # 🛠️ 开发工具
    ├── codegen/                       # 代码生成工具
    ├── linting/                       # 代码检查配置
    │   ├── .pylintrc
    │   ├── .golangci.yml
    │   └── .eslintrc.js
    └── ide/                          # IDE配置
        ├── vscode/
        │   ├── settings.json
        │   ├── launch.json
        │   └── extensions.json
        └── intellij/
```

---

## 🎨 Frontend 目录结构 (React + TypeScript)

```
frontend/
├── package.json                       # 项目依赖和脚本
├── package-lock.json                  # 锁定依赖版本
├── tsconfig.json                      # TypeScript配置
├── vite.config.ts                     # Vite构建配置
├── tailwind.config.js                 # Tailwind CSS配置
├── .env.local                         # 本地环境变量
├──
├── public/                            # 静态资源
│   ├── index.html
│   ├── favicon.ico
│   └── manifest.json
├──
├── src/                               # 源代码
│   ├── main.tsx                       # 应用入口
│   ├── App.tsx                        # 根组件
│   ├── App.css                        # 全局样式
│   ├──
│   ├── components/                    # 📦 可复用组件
│   │   ├── common/                    # 通用组件
│   │   │   ├── Button/
│   │   │   │   ├── index.tsx
│   │   │   │   ├── Button.module.css
│   │   │   │   └── Button.test.tsx
│   │   │   ├── Loading/
│   │   │   ├── Modal/
│   │   │   └── Form/
│   │   ├── layout/                    # 布局组件
│   │   │   ├── Header/
│   │   │   ├── Sidebar/
│   │   │   ├── Footer/
│   │   │   └── MainLayout/
│   │   └── chat/                      # 聊天相关组件
│   │       ├── ChatContainer/
│   │       ├── MessageBubble/
│   │       ├── InputBox/
│   │       └── ConversationList/
│   ├──
│   ├── pages/                         # 📄 页面组件
│   │   ├── login/
│   │   │   ├── index.tsx
│   │   │   └── Login.module.css
│   │   ├── dashboard/
│   │   │   ├── index.tsx
│   │   │   ├── Dashboard.module.css
│   │   │   └── components/           # 页面专用组件
│   │   ├── chat/
│   │   ├── settings/
│   │   └── admin/
│   ├──
│   ├── hooks/                         # 🎣 自定义Hooks
│   │   ├── useAuth.ts
│   │   ├── useChat.ts
│   │   ├── useLocalStorage.ts
│   │   └── useApi.ts
│   ├──
│   ├── services/                      # 🌐 API服务
│   │   ├── api.ts                     # API基础配置
│   │   ├── auth.ts                    # 认证相关API
│   │   ├── chat.ts                    # 聊天相关API
│   │   ├── user.ts                    # 用户相关API
│   │   └── admin.ts                   # 管理相关API
│   ├──
│   ├── store/                         # 🗄️ 状态管理
│   │   ├── index.ts                   # Store配置
│   │   ├── slices/                    # Redux切片
│   │   │   ├── authSlice.ts
│   │   │   ├── chatSlice.ts
│   │   │   └── userSlice.ts
│   │   └── middleware/                # 中间件
│   ├──
│   ├── types/                         # 📝 TypeScript类型
│   │   ├── api.ts                     # API响应类型
│   │   ├── user.ts                    # 用户相关类型
│   │   ├── chat.ts                    # 聊天相关类型
│   │   └── common.ts                  # 通用类型
│   ├──
│   ├── utils/                         # 🔧 工具函数
│   │   ├── constants.ts               # 常量定义
│   │   ├── helpers.ts                 # 辅助函数
│   │   ├── validators.ts              # 验证函数
│   │   └── formatters.ts              # 格式化函数
│   ├──
│   ├── assets/                        # 🖼️ 静态资源
│   │   ├── images/
│   │   ├── icons/
│   │   └── fonts/
│   └──
│   └── styles/                        # 🎨 样式文件
│       ├── globals.css                # 全局样式
│       ├── variables.css              # CSS变量
│       └── themes/                    # 主题文件
├──
├── tests/                             # 🧪 测试文件
│   ├── setup.ts                       # 测试环境配置
│   ├── __mocks__/                     # Mock文件
│   ├── unit/                          # 单元测试
│   └── integration/                   # 集成测试
├──
└── docs/                              # 📚 前端文档
    ├── COMPONENTS.md                  # 组件文档
    ├── DEPLOYMENT.md                  # 部署文档
    └── CONTRIBUTING.md                # 贡献指南
```

---

## 🚀 Backend (API Gateway) 目录结构 (Python + FastAPI)

```
backend/
├── requirements.txt                   # Python依赖
├── requirements-dev.txt               # 开发依赖
├── pyproject.toml                     # 项目配置
├── pytest.ini                        # 测试配置
├── .env.example                       # 环境变量模板
├──
├── api_gateway/                       # 主应用包
│   ├── __init__.py
│   ├── main.py                        # FastAPI应用入口
│   ├── config.py                      # 配置管理
│   ├──
│   ├── core/                          # 🔧 核心组件
│   │   ├── __init__.py
│   │   ├── security.py                # 安全相关
│   │   ├── dependencies.py            # 依赖注入
│   │   ├── middleware.py              # 中间件
│   │   ├── logging.py                 # 日志配置
│   │   └── database.py                # 数据库连接
│   ├──
│   ├── routers/                       # 🛣️ 路由模块
│   │   ├── __init__.py
│   │   ├── health.py                  # 健康检查
│   │   ├── auth.py                    # 认证路由代理
│   │   ├── chat.py                    # 聊天路由代理
│   │   ├── admin.py                   # 管理路由代理
│   │   └── v1/                        # API版本分组
│   │       ├── __init__.py
│   │       ├── users.py
│   │       └── conversations.py
│   ├──
│   ├── services/                      # 💼 业务服务
│   │   ├── __init__.py
│   │   ├── auth_service_client.py     # 认证服务客户端
│   │   ├── tenant_service_client.py   # 租户服务客户端
│   │   ├── eino_service_client.py     # EINO服务客户端
│   │   ├── memory_service_client.py   # 记忆服务客户端
│   │   └── base_client.py             # 基础HTTP客户端
│   ├──
│   ├── models/                        # 📊 数据模型
│   │   ├── __init__.py
│   │   ├── base.py                    # 基础模型
│   │   ├── requests.py                # 请求模型
│   │   ├── responses.py               # 响应模型
│   │   └── schemas/                   # Pydantic模式
│   │       ├── auth.py
│   │       ├── user.py
│   │       └── chat.py
│   ├──
│   ├── utils/                         # 🔧 工具模块
│   │   ├── __init__.py
│   │   ├── exceptions.py              # 异常定义
│   │   ├── validators.py              # 验证器
│   │   ├── helpers.py                 # 辅助函数
│   │   └── constants.py               # 常量定义
│   └──
│   └── middleware/                    # 🔄 中间件
│       ├── __init__.py
│       ├── cors.py                    # CORS处理
│       ├── rate_limit.py              # 速率限制
│       ├── request_id.py              # 请求ID生成
│       └── tenant_context.py          # 租户上下文
├──
├── alembic/                           # 🗃️ 数据库迁移 (如果有独立数据库)
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├──
├── tests/                             # 🧪 测试
│   ├── __init__.py
│   ├── conftest.py                    # 测试配置
│   ├── test_main.py                   # 主要测试
│   ├── unit/                          # 单元测试
│   │   ├── test_routers/
│   │   ├── test_services/
│   │   └── test_utils/
│   ├── integration/                   # 集成测试
│   │   ├── test_api_gateway.py
│   │   └── test_service_clients.py
│   └── fixtures/                      # 测试数据
├──
├── scripts/                           # 🔧 运维脚本
│   ├── start_dev.py                   # 开发环境启动
│   ├── migrate.py                     # 数据库迁移
│   └── health_check.py                # 健康检查
├──
└── docs/                              # 📚 API文档
    ├── openapi.json                   # OpenAPI规范
    └── postman/                       # Postman集合
        └── api_gateway.postman_collection.json
```

---

## 🔐 Auth Service 目录结构 (Python + FastAPI)

```
auth-service/
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── .env.example
├──
├── auth_service/                      # 主应用包
│   ├── __init__.py
│   ├── main.py                        # FastAPI应用入口
│   ├── config.py                      # 配置管理
│   ├──
│   ├── core/                          # 🔧 核心组件
│   │   ├── __init__.py
│   │   ├── security.py                # JWT处理
│   │   ├── password.py                # 密码加密
│   │   ├── tokens.py                  # 令牌管理
│   │   └── exceptions.py              # 异常定义
│   ├──
│   ├── routers/                       # 🛣️ 路由模块
│   │   ├── __init__.py
│   │   ├── health.py                  # 健康检查
│   │   ├── auth.py                    # 认证接口
│   │   ├── tokens.py                  # 令牌管理
│   │   └── internal.py                # 内部服务接口
│   ├──
│   ├── services/                      # 💼 业务服务
│   │   ├── __init__.py
│   │   ├── auth_service.py            # 认证业务逻辑
│   │   ├── token_service.py           # 令牌管理
│   │   ├── tenant_client.py           # 租户服务客户端
│   │   └── password_service.py        # 密码服务
│   ├──
│   ├── models/                        # 📊 数据模型
│   │   ├── __init__.py
│   │   ├── auth.py                    # 认证相关模型
│   │   ├── tokens.py                  # 令牌模型
│   │   └── schemas/                   # Pydantic模式
│   │       ├── login.py
│   │       ├── token.py
│   │       └── user.py
│   ├──
│   ├── utils/                         # 🔧 工具模块
│   │   ├── __init__.py
│   │   ├── redis_client.py            # Redis客户端
│   │   ├── cache.py                   # 缓存工具
│   │   └── validators.py              # 验证器
│   └──
│   └── middleware/                    # 🔄 中间件
│       ├── __init__.py
│       ├── rate_limit.py              # 速率限制
│       └── request_logging.py         # 请求日志
├──
├── tests/                             # 🧪 测试
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_tokens.py
│   └── integration/
└──
└── scripts/                           # 🔧 脚本
    ├── start_dev.py
    └── generate_keys.py               # 密钥生成
```

---

## 👥 Tenant Service 目录结构 (Python + FastAPI)

```
tenant-service/
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── .env.example
├──
├── tenant_service/                    # 主应用包
│   ├── __init__.py
│   ├── main.py                        # FastAPI应用入口
│   ├── config.py                      # 配置管理
│   ├──
│   ├── core/                          # 🔧 核心组件
│   │   ├── __init__.py
│   │   ├── database.py                # 数据库连接
│   │   ├── security.py                # 安全相关
│   │   ├── encryption.py              # pgcrypto加密
│   │   └── tenant_context.py          # 租户上下文
│   ├──
│   ├── routers/                       # 🛣️ 路由模块
│   │   ├── __init__.py
│   │   ├── health.py                  # 健康检查
│   │   ├── tenants.py                 # 租户管理
│   │   ├── users.py                   # 用户管理
│   │   ├── suppliers.py               # 供应商凭证
│   │   ├── tool_configs.py            # 工具配置
│   │   ├── preferences.py             # 用户偏好
│   │   └── internal.py                # 内部服务接口
│   ├──
│   ├── services/                      # 💼 业务服务
│   │   ├── __init__.py
│   │   ├── tenant_service.py          # 租户业务逻辑
│   │   ├── user_service.py            # 用户管理
│   │   ├── credential_service.py      # 凭证管理
│   │   ├── tool_config_service.py     # 工具配置服务
│   │   └── preference_service.py      # 偏好管理
│   ├──
│   ├── models/                        # 📊 数据模型
│   │   ├── __init__.py
│   │   ├── database/                  # SQLAlchemy模型
│   │   │   ├── tenant.py
│   │   │   ├── user.py
│   │   │   ├── role.py
│   │   │   ├── supplier_credential.py
│   │   │   ├── tool_config.py
│   │   │   └── user_preference.py
│   │   └── schemas/                   # Pydantic模式
│   │       ├── tenant.py
│   │       ├── user.py
│   │       ├── supplier.py
│   │       └── preference.py
│   ├──
│   ├── repositories/                  # 🗄️ 数据访问层
│   │   ├── __init__.py
│   │   ├── base.py                    # 基础仓库
│   │   ├── tenant_repository.py       # 租户数据访问
│   │   ├── user_repository.py         # 用户数据访问
│   │   ├── credential_repository.py   # 凭证数据访问
│   │   └── preference_repository.py   # 偏好数据访问
│   ├──
│   ├── utils/                         # 🔧 工具模块
│   │   ├── __init__.py
│   │   ├── password_utils.py          # 密码工具
│   │   ├── uuid_utils.py              # UUID工具
│   │   └── validation_utils.py        # 验证工具
│   └──
│   └── migrations/                    # 🗃️ 数据库迁移
│       ├── env.py
│       ├── script.py.mako
│       └── versions/
├──
├── tests/                             # 🧪 测试
│   ├── conftest.py
│   ├── test_tenants.py
│   ├── test_users.py
│   ├── test_credentials.py
│   └── integration/
└──
└── scripts/                           # 🔧 脚本
    ├── start_dev.py
    ├── init_db.py                     # 数据库初始化
    └── create_tenant.py               # 创建租户
```

---

## ⚡ EINO Service 目录结构 (Go)

```
eino-service/
├── go.mod                             # Go模块定义
├── go.sum                             # 依赖锁定文件
├── .env.example                       # 环境变量模板
├── Makefile                           # 构建脚本
├──
├── cmd/                               # 🚀 应用入口
│   └── server/
│       └── main.go                    # 主程序入口
├──
├── internal/                          # 🔒 内部包(不对外暴露)
│   ├── config/                        # ⚙️ 配置管理
│   │   ├── config.go
│   │   └── env.go
│   ├──
│   ├── handlers/                      # 🛣️ HTTP处理器
│   │   ├── health.go                  # 健康检查
│   │   ├── chat.go                    # 聊天接口
│   │   ├── workflow.go                # 工作流接口
│   │   └── internal.go                # 内部接口
│   ├──
│   ├── services/                      # 💼 业务服务
│   │   ├── workflow_service.go        # 工作流服务
│   │   ├── model_service.go           # 模型服务
│   │   ├── tool_service.go            # 工具服务
│   │   ├── memory_service.go          # 记忆服务集成
│   │   └── tenant_service.go          # 租户服务集成
│   ├──
│   ├── workflows/                     # 🔄 工作流定义
│   │   ├── simple_chat.go             # 简单对话工作流
│   │   ├── optimized_rag.go           # 优化RAG工作流
│   │   ├── function_calling.go        # 函数调用工作流
│   │   └── nodes/                     # 工作流节点
│   │       ├── memory_retrieval.go
│   │       ├── memory_storage.go
│   │       ├── web_search.go
│   │       └── database_query.go
│   ├──
│   ├── models/                        # 📊 数据模型
│   │   ├── request.go                 # 请求模型
│   │   ├── response.go                # 响应模型
│   │   ├── workflow.go                # 工作流模型
│   │   ├── config.go                  # 配置模型
│   │   └── execution.go               # 执行状态模型
│   ├──
│   ├── clients/                       # 🌐 外部服务客户端
│   │   ├── base_client.go             # 基础HTTP客户端
│   │   ├── tenant_client.go           # 租户服务客户端
│   │   ├── memory_client.go           # 记忆服务客户端
│   │   └── ai_providers/              # AI供应商客户端
│   │       ├── openai_client.go
│   │       ├── anthropic_client.go
│   │       └── google_client.go
│   ├──
│   ├── middleware/                    # 🔄 中间件
│   │   ├── cors.go                    # CORS处理
│   │   ├── logging.go                 # 日志中间件
│   │   ├── recovery.go                # 错误恢复
│   │   └── request_id.go              # 请求ID
│   ├──
│   ├── utils/                         # 🔧 工具包
│   │   ├── logger.go                  # 日志工具
│   │   ├── http_utils.go              # HTTP工具
│   │   ├── json_utils.go              # JSON工具
│   │   └── validation.go              # 验证工具
│   └──
│   └── repository/                    # 🗄️ 数据访问层
│       ├── execution_repo.go          # 执行状态存储
│       └── cache_repo.go              # 缓存访问
├──
├── pkg/                               # 📦 公共包(可对外暴露)
│   ├── errors/                        # 错误定义
│   │   ├── codes.go
│   │   └── errors.go
│   └── types/                         # 公共类型
│       └── common.go
├──
├── scripts/                           # 🔧 脚本文件
│   ├── build.sh                       # 构建脚本
│   ├── test.sh                        # 测试脚本
│   └── start_dev.sh                   # 开发启动
├──
├── tests/                             # 🧪 测试
│   ├── unit/                          # 单元测试
│   │   ├── services_test.go
│   │   └── workflows_test.go
│   ├── integration/                   # 集成测试
│   │   └── api_test.go
│   └── fixtures/                      # 测试数据
├──
├── docs/                              # 📚 文档
│   ├── API.md                         # API文档
│   └── WORKFLOWS.md                   # 工作流文档
└──
└── deployments/                       # 🚀 部署配置
    ├── Dockerfile
    └── docker-compose.yml
```

---

## 🧠 Memory Service 目录结构 (Python + FastAPI)

```
memory-service/
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── .env.example
├──
├── memory_service/                    # 主应用包
│   ├── __init__.py
│   ├── main.py                        # FastAPI应用入口
│   ├── config.py                      # 配置管理
│   ├──
│   ├── core/                          # 🔧 核心组件
│   │   ├── __init__.py
│   │   ├── mem0_config.py             # Mem0AI配置
│   │   ├── memory_manager.py          # 记忆管理器
│   │   ├── tenant_isolation.py        # 租户隔离
│   │   └── cache.py                   # 缓存管理
│   ├──
│   ├── routers/                       # 🛣️ 路由模块
│   │   ├── __init__.py
│   │   ├── health.py                  # 健康检查
│   │   ├── memory.py                  # 记忆操作接口
│   │   ├── search.py                  # 记忆搜索
│   │   ├── management.py              # 记忆管理
│   │   └── internal.py                # 内部服务接口
│   ├──
│   ├── services/                      # 💼 业务服务
│   │   ├── __init__.py
│   │   ├── memory_service.py          # 记忆业务逻辑
│   │   ├── search_service.py          # 搜索服务
│   │   ├── preference_checker.py      # 偏好检查器
│   │   ├── tenant_client.py           # 租户服务客户端
│   │   └── batch_processor.py         # 批量处理
│   ├──
│   ├── models/                        # 📊 数据模型
│   │   ├── __init__.py
│   │   ├── database/                  # SQLAlchemy模型
│   │   │   ├── memory_metadata.py
│   │   │   └── access_log.py
│   │   └── schemas/                   # Pydantic模式
│   │       ├── memory.py
│   │       ├── search.py
│   │       └── batch.py
│   ├──
│   ├── repositories/                  # 🗄️ 数据访问层
│   │   ├── __init__.py
│   │   ├── memory_repository.py       # 记忆数据访问
│   │   └── log_repository.py          # 日志数据访问
│   ├──
│   ├── utils/                         # 🔧 工具模块
│   │   ├── __init__.py
│   │   ├── memory_utils.py            # 记忆工具
│   │   ├── tenant_utils.py            # 租户工具
│   │   └── security_utils.py          # 安全工具
│   ├──
│   ├── middleware/                    # 🔄 中间件
│   │   ├── __init__.py
│   │   ├── memory_check.py            # 记忆开关检查
│   │   └── tenant_context.py          # 租户上下文
│   └──
│   └── migrations/                    # 🗃️ 数据库迁移
│       ├── env.py
│       ├── script.py.mako
│       └── versions/
├──
├── tests/                             # 🧪 测试
│   ├── conftest.py
│   ├── test_memory.py
│   ├── test_search.py
│   ├── test_preferences.py
│   └── integration/
└──
└── scripts/                           # 🔧 脚本
    ├── start_dev.py
    ├── init_mem0.py                   # Mem0AI初始化
    └── cleanup_memories.py            # 记忆清理
```

---

## 📦 共享代码库结构 (Shared)

```
shared/
├── python/                            # Python共享组件
│   ├── __init__.py
│   ├── setup.py                       # 包安装配置
│   ├──
│   ├── lyss_shared/                   # 主包
│   │   ├── __init__.py
│   │   ├──
│   │   ├── auth/                      # 🔐 认证相关
│   │   │   ├── __init__.py
│   │   │   ├── jwt_utils.py           # JWT工具
│   │   │   ├── decorators.py          # 认证装饰器
│   │   │   └── middleware.py          # 认证中间件
│   │   ├──
│   │   ├── database/                  # 🗄️ 数据库工具
│   │   │   ├── __init__.py
│   │   │   ├── connection.py          # 连接管理
│   │   │   ├── session.py             # 会话管理
│   │   │   └── base_model.py          # 基础模型
│   │   ├──
│   │   ├── logging/                   # 📝 日志组件
│   │   │   ├── __init__.py
│   │   │   ├── formatter.py           # 日志格式化
│   │   │   ├── handlers.py            # 日志处理器
│   │   │   └── middleware.py          # 日志中间件
│   │   ├──
│   │   ├── utils/                     # 🔧 通用工具
│   │   │   ├── __init__.py
│   │   │   ├── constants.py           # 常量定义
│   │   │   ├── exceptions.py          # 异常定义
│   │   │   ├── validators.py          # 验证器
│   │   │   └── helpers.py             # 辅助函数
│   │   └──
│   │   └── models/                    # 📊 共享模型
│   │       ├── __init__.py
│   │       ├── base.py                # 基础模型
│   │       └── responses.py           # 统一响应格式
│   └──
│   └── tests/                         # 🧪 测试
│       ├── test_auth.py
│       ├── test_logging.py
│       └── test_utils.py
├──
├── go/                                # Go共享组件
│   ├── go.mod
│   ├── go.sum
│   ├──
│   ├── auth/                          # 🔐 认证相关
│   │   ├── jwt.go                     # JWT工具
│   │   ├── middleware.go              # 认证中间件
│   │   └── types.go                   # 认证类型
│   ├──
│   ├── logging/                       # 📝 日志组件
│   │   ├── logger.go                  # 日志器
│   │   ├── formatter.go               # 格式化器
│   │   └── middleware.go              # 日志中间件
│   ├──
│   ├── utils/                         # 🔧 工具包
│   │   ├── constants.go               # 常量
│   │   ├── errors.go                  # 错误处理
│   │   ├── http.go                    # HTTP工具
│   │   └── validation.go              # 验证工具
│   └──
│   └── types/                         # 📝 公共类型
│       ├── request.go                 # 请求类型
│       ├── response.go                # 响应类型
│       └── config.go                  # 配置类型
└──
└── typescript/                        # TypeScript共享组件
    ├── package.json
    ├── tsconfig.json
    ├──
    ├── src/
    │   ├── types/                     # 📝 类型定义
    │   │   ├── api.ts                 # API类型
    │   │   ├── user.ts                # 用户类型
    │   │   ├── chat.ts                # 聊天类型
    │   │   └── common.ts              # 通用类型
    │   ├──
    │   ├── api/                       # 🌐 API客户端
    │   │   ├── base.ts                # 基础客户端
    │   │   ├── auth.ts                # 认证API
    │   │   ├── chat.ts                # 聊天API
    │   │   └── admin.ts               # 管理API
    │   ├──
    │   └── utils/                     # 🔧 工具函数
    │       ├── constants.ts           # 常量
    │       ├── validators.ts          # 验证器
    │       ├── formatters.ts          # 格式化器
    │       └── helpers.ts             # 辅助函数
    ├──
    ├── tests/                         # 🧪 测试
    └── dist/                          # 📦 构建输出
```

---

## 🔧 关键规范要求

### 📁 目录命名规范

1. **服务目录**: 使用 `kebab-case`（短横线连接）
   - ✅ `auth-service`, `tenant-service`, `memory-service`
   - ❌ `authService`, `auth_service`, `AuthService`

2. **代码包/模块**: 使用 `snake_case`（下划线连接）
   - ✅ `auth_service`, `memory_service`, `user_preferences`
   - ❌ `authService`, `auth-service`, `AuthService`

3. **文件命名**: 遵循各语言约定
   - Python: `snake_case.py`
   - Go: `snake_case.go` 或 `camelCase.go`
   - TypeScript: `camelCase.ts` 或 `kebab-case.ts`

### 📄 必需文件清单

每个服务**必须**包含以下文件：

1. **环境配置**
   - `.env.example` - 环境变量模板
   - `requirements.txt` (Python) 或 `go.mod` (Go) 或 `package.json` (Node.js)

2. **文档文件**
   - `README.md` - 服务说明和启动指南
   - `docs/API.md` - API接口文档

3. **配置文件**
   - 主配置文件：`config.py` / `config.go` / `config.ts`
   - 测试配置：`pytest.ini` / `Makefile` / `jest.config.js`

4. **健康检查**
   - 健康检查路由：`/health`
   - 对应的处理文件：`health.py` / `health.go` / `health.ts`

### 🔒 安全和隐私要求

1. **敏感文件严禁提交**
   - `.env` - 实际环境变量
   - `*.key` - 密钥文件
   - `secrets/` - 密钥目录
   - `logs/` - 日志文件

2. **权限控制**
   - 所有API都必须有对应的权限检查
   - 多租户数据严格隔离
   - 敏感操作必须记录审计日志

### 🧪 测试规范

1. **测试目录结构**
   ```
   tests/
   ├── unit/          # 单元测试
   ├── integration/   # 集成测试
   ├── e2e/          # 端到端测试
   ├── fixtures/     # 测试数据
   └── conftest.py   # 测试配置
   ```

2. **测试覆盖率要求**
   - 单元测试覆盖率 ≥ 80%
   - 关键业务逻辑覆盖率 ≥ 95%
   - 所有API接口必须有集成测试

### 🚀 部署要求

1. **Docker支持**
   - 每个服务必须有 `Dockerfile`
   - 支持多阶段构建优化镜像大小
   - 非特权用户运行

2. **健康检查**
   - 所有服务必须提供 `/health` 接口
   - Docker容器必须配置健康检查
   - 支持优雅关闭

---

## ⚠️ 严格约束条件

### 🔒 强制性规范

1. **目录结构不得随意更改** - 任何结构调整必须先更新本文档
2. **必需文件不得缺失** - 每个服务的必需文件必须完整存在
3. **命名规范严格执行** - 所有文件、目录、变量命名必须遵循规范
4. **多租户隔离** - 所有业务数据必须严格按租户隔离
5. **安全规范** - 任何涉及认证、授权、加密的代码必须遵循安全规范

### 📊 监控指标

- 代码结构合规性检查
- 必需文件完整性监控
- 测试覆盖率统计
- 安全规范遵循度评估

---

**📋 重要提醒**: 本目录结构规范是 Lyss AI Platform 项目开发的基础规范，任何偏离都可能导致团队协作效率下降和代码维护困难。请严格遵循执行！

**🔄 文档版本**: 1.0.0  
**📅 最后更新**: 2025-07-10  
**📅 下次审查**: 2025-08-10